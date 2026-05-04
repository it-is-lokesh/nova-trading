"""
Example shape of the generated encrypted env file.

Do not edit `confidential/env.py` by hand. Copy `.credentials.example` to
`.credentials`, fill plaintext values there, then run:

    python applications/security.py

The generated `confidential/env.py` stores encrypted Fernet tokens like the
constants below. Runtime code decrypts them using `confidential/.key`.
"""

API_KEY = "gAAAA..."
CLIENT_CODE = "gAAAA..."
CLIENT_PIN = "gAAAA..."
TOTP_CODE = "gAAAA..."
TOTP_SECRET = "gAAAA..."
STATE_VARIABLE = "gAAAA..."
JWT_TOKEN = "gAAAA..."
CLIENT_LOCAL_IP = "gAAAA..."
CLIENT_PUBLIC_IP = "gAAAA..."
MAC_ADDRESS = "gAAAA..."

__all__ = [
    "API_KEY",
    "CLIENT_CODE",
    "CLIENT_PIN",
    "TOTP_CODE",
    "TOTP_SECRET",
    "STATE_VARIABLE",
    "JWT_TOKEN",
    "CLIENT_LOCAL_IP",
    "CLIENT_PUBLIC_IP",
    "MAC_ADDRESS",
]
