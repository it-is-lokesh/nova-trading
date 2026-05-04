from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KEY_PATH = PROJECT_ROOT / "confidential" / ".key"


@lru_cache(maxsize=1)
def _cipher() -> Fernet:
    if not KEY_PATH.exists():
        raise RuntimeError(
            f"Missing credential key: {KEY_PATH}. "
            "Run `python applications/security.py` after filling `.credentials`."
        )
    return Fernet(KEY_PATH.read_bytes().strip())


def decrypt_credential(encrypted_value: str, name: str = "credential") -> str:
    if encrypted_value is None:
        return ""

    token = str(encrypted_value)
    if not token:
        return ""

    try:
        return _cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            f"Could not decrypt {name}. Regenerate confidential/env.py with "
            "`python applications/security.py` and keep confidential/.key unchanged."
        ) from exc


def encrypt_credential(value: str) -> str:
    return _cipher().encrypt(str(value).encode("utf-8")).decode("utf-8")


def decrypt_env_credential(env_module, name: str) -> str:
    return decrypt_credential(getattr(env_module, name, ""), name=name)
