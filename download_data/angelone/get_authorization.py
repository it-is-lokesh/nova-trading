import http.client
import json
import sys
import re
from pathlib import Path

import pyotp

# Add project root to sys.path to import confidential.env
sys.path.append(str(Path(__file__).parent.parent.parent))

import confidential.env as env

SMARTAPI_HOST = "apiconnect.angelone.in"
LOGIN_PATH = "/rest/auth/angelbroking/user/v1/loginByPassword"
ENV_FILE_PATH = Path(__file__).parent.parent.parent / "confidential" / "env.py"


def generate_totp():
    """
    Generates a fresh 6-digit TOTP code using TOTP_SECRET from env.
    """
    secret = getattr(env, "TOTP_SECRET", "")
    if not secret:
        raise RuntimeError(
            "TOTP_SECRET is empty in confidential/env.py.\n"
            "To automate login, add the TOTP secret key you received when "
            "enabling TOTP on the AngelOne SmartAPI portal.\n"
            "  → Go to https://smartapi.angelbroking.com/enable-totp\n"
            "  → Copy the secret key and paste it in env.py as:\n"
            '    TOTP_SECRET = "YOUR_SECRET_KEY_HERE"'
        )
    totp = pyotp.TOTP(secret)
    code = totp.now()
    print(f"Generated TOTP: {code}")
    return code


def ensure_credentials():
    """
    Validates that all required credentials are present in env.py.
    """
    missing = [
        name
        for name, value in {
            "API_KEY": env.API_KEY,
            "CLIENT_CODE": env.CLIENT_CODE,
            "CLIENT_PIN": env.CLIENT_PIN,
        }.items()
        if not value
    ]

    if not getattr(env, "TOTP_SECRET", ""):
        missing.append("TOTP_SECRET")

    if missing:
        raise RuntimeError(f"Fill these values in confidential/env.py first: {', '.join(missing)}")


def login_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": env.CLIENT_LOCAL_IP,
        "X-ClientPublicIP": env.CLIENT_PUBLIC_IP,
        "X-MACAddress": env.MAC_ADDRESS,
        "X-PrivateKey": env.API_KEY,
    }


def login_payload():
    totp_code = generate_totp()
    return {
        "clientcode": env.CLIENT_CODE,
        "password": env.CLIENT_PIN,
        "totp": totp_code,
        "state": env.STATE_VARIABLE,
    }


def post_json(path, payload, headers):
    conn = http.client.HTTPSConnection(SMARTAPI_HOST, timeout=30)
    try:
        conn.request("POST", path, json.dumps(payload), headers)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
    finally:
        conn.close()

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"SmartAPI returned non-JSON response: {body}") from exc

    if response.status >= 400:
        raise SystemExit(f"SmartAPI HTTP {response.status}: {json.dumps(data, indent=2)}")

    return data


def get_fresh_token():
    """
    Performs login with auto-generated TOTP and returns a fresh JWT token.
    """
    ensure_credentials()
    print("Logging in to AngelOne SmartAPI...")
    response = post_json(LOGIN_PATH, login_payload(), login_headers())

    if not response.get("status"):
        raise RuntimeError(f"Login failed: {json.dumps(response, indent=2)}")

    jwt_token = response.get("data", {}).get("jwtToken")
    if not jwt_token:
        raise RuntimeError(f"Login response did not include jwtToken: {json.dumps(response, indent=2)}")

    print("Login successful!")
    return jwt_token


def update_env_file(new_jwt_token):
    """
    Updates the JWT_TOKEN value in confidential/env.py file.
    Also updates the in-memory env.JWT_TOKEN so the current process
    uses the new token immediately.
    """
    # Update in-memory
    env.JWT_TOKEN = new_jwt_token

    if not ENV_FILE_PATH.exists():
        print(f"Warning: {ENV_FILE_PATH} not found. Cannot update token on disk.")
        return

    content = ENV_FILE_PATH.read_text()
    # Match JWT_TOKEN = "..." or JWT_TOKEN = '...'
    pattern = r'(JWT_TOKEN\s*=\s*["\'])(.*?)(["\'])'
    new_content = re.sub(pattern, rf'\1{new_jwt_token}\3', content)

    ENV_FILE_PATH.write_text(new_content)
    print(f"Updated JWT_TOKEN in {ENV_FILE_PATH}")


def main():
    try:
        jwt_token = get_fresh_token()
        update_env_file(jwt_token)
        print(f"\nYou can now use this token to make API calls.")
    except RuntimeError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
