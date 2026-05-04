"""
Encrypt credentials from .credentials into confidential/env.py.

Usage:
    python applications/security.py
"""
import argparse
import ast
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / ".credentials"
DEFAULT_CONFIDENTIAL_DIR = PROJECT_ROOT / "confidential"
DEFAULT_KEY_PATH = DEFAULT_CONFIDENTIAL_DIR / ".key"
DEFAULT_ENV_PATH = DEFAULT_CONFIDENTIAL_DIR / "env.py"

KEY_VALUE_PATTERN = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_credentials(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Credentials file not found: {path}")

    credentials = {}
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = KEY_VALUE_PATTERN.match(stripped)
        if not match:
            raise ValueError(f"Invalid credentials line {line_number}: expected KEY=value")

        key, raw_value = match.groups()
        credentials[key] = parse_value(raw_value.strip())

    if not credentials:
        raise ValueError(f"No credentials found in {path}")

    return credentials


def parse_value(raw_value: str) -> str:
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {"'", '"'}:
        try:
            value = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError):
            value = raw_value[1:-1]
        return str(value)
    return raw_value


def load_or_create_key(path: Path, rotate: bool = False, dry_run: bool = False) -> tuple[bytes, bool]:
    if path.exists() and not rotate:
        key = path.read_bytes().strip()
        Fernet(key)
        return key, False

    key = Fernet.generate_key()
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key + b"\n")
        os.chmod(path, 0o600)

    return key, True


def encrypt_credentials(credentials: dict[str, str], key: bytes) -> dict[str, str]:
    cipher = Fernet(key)
    return {
        name: cipher.encrypt(value.encode("utf-8")).decode("utf-8")
        for name, value in credentials.items()
    }


def render_env_py(encrypted_credentials: dict[str, str]) -> str:
    constant_lines = [
        f"{name} = {encrypted_value!r}"
        for name, encrypted_value in encrypted_credentials.items()
    ]
    exported_names = ", ".join(repr(name) for name in encrypted_credentials)

    return f'''"""
Auto-generated encrypted credential tokens.

Run `python applications/security.py` after editing `.credentials`.
Keep `confidential/.key` private. These constants are encrypted strings.
"""


{chr(10).join(constant_lines)}

__all__ = [{exported_names}]
'''


def write_env_file(path: Path, encrypted_credentials: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_env_py(encrypted_credentials))
    os.chmod(path, 0o600)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Encrypt .credentials values into confidential/env.py.",
    )
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS_PATH)
    parser.add_argument("--key-path", type=Path, default=DEFAULT_KEY_PATH)
    parser.add_argument("--env-path", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--rotate-key", action="store_true", help="Generate a new key before encrypting.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and encrypt in memory without writing files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    credentials = parse_credentials(args.credentials)
    key, created_key = load_or_create_key(args.key_path, rotate=args.rotate_key, dry_run=args.dry_run)
    encrypted_credentials = encrypt_credentials(credentials, key)

    if not args.dry_run:
        write_env_file(args.env_path, encrypted_credentials)

    action = "Would encrypt" if args.dry_run else "Encrypted"
    key_action = "generated" if created_key else "reused"
    print(f"{action} {len(credentials)} field(s): {', '.join(credentials)}")
    print(f"Key {key_action}: {args.key_path}")
    if args.dry_run:
        print(f"Dry run only; no files written. Target env file: {args.env_path}")
    else:
        print(f"Wrote encrypted credentials to: {args.env_path}")


if __name__ == "__main__":
    main()
