"""Secret Encryption at Rest (Twelve-Factor Factor IV & VI).

FEATURE PURPOSE:
Provides symmetric envelope encryption for third-party OAuth access tokens,
refresh tokens, API keys, and incoming webhooks stored in the database.
This protects sensitive customer integrations against database leaks, backups exposure,
and SQL injection inspection.

NOTE ON NAMING:
This module was explicitly named `secret_encryption.py` (rather than `crypto.py`)
to make the feature immediately obvious to developers and avoid ambiguity
with cryptocurrency / blockchain concepts.
"""

import base64
import hashlib
from typing import Any, Optional
from cryptography.fernet import Fernet, InvalidToken

from core.config import settings
from core.logging import get_logger

logger = get_logger("secret_encryption")

# Specific dictionary keys in third-party integration configs that MUST be encrypted before DB persistence
SENSITIVE_INTEGRATION_KEYS: frozenset[str] = frozenset({
    "api_key",
    "api_token",
    "bot_token",
    "access_token",
    "refresh_token",
    "webhook_url",
    "client_secret",
    "auth_token",
    "secret",
})
# Backwards-compatible alias
SENSITIVE_KEYS = SENSITIVE_INTEGRATION_KEYS


def _get_encryption_key() -> bytes:
    """Derive a URL-safe base64-encoded 32-byte Fernet key from application secrets."""
    raw_key = (
        getattr(settings, "ENCRYPTION_KEY", None)
        or getattr(settings, "SECRET_KEY", None)
        or getattr(settings, "JWT_SECRET_KEY", None)
        or "promisecheck-default-fallback-encryption-key-32b"
    )
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_encryption_cipher() -> Fernet:
    """Instantiate the Fernet symmetric encryption cipher."""
    return Fernet(_get_encryption_key())


# Backwards-compatible alias
get_fernet = get_encryption_cipher


def encrypt_secret(plain_text: Optional[str]) -> str:
    """Encrypt a secret string using AES-128-CBC envelope encryption with HMAC authentication."""
    if not plain_text or not isinstance(plain_text, str):
        return ""
    # Avoid re-encrypting if already an encrypted Fernet token
    if plain_text.startswith("gAAAAA"):
        return plain_text
    cipher = get_encryption_cipher()
    return cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: Optional[str]) -> str:
    """Decrypt an encrypted secret string into memory. Falls back to plain text for legacy records."""
    if not cipher_text or not isinstance(cipher_text, str):
        return ""
    if not cipher_text.startswith("gAAAAA"):
        # Legacy or plaintext value prior to encryption migration
        return cipher_text
    try:
        cipher = get_encryption_cipher()
        return cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Decryption failed: invalid encryption token or application key mismatch")
        return cipher_text
    except Exception as exc:
        logger.warning(f"Unexpected error during secret decryption: {exc}")
        return cipher_text


def encrypt_config_dict(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Return a sanitized copy of the integration config dictionary with all sensitive keys encrypted."""
    if not config:
        return {}
    encrypted = {}
    for k, v in config.items():
        if k in SENSITIVE_INTEGRATION_KEYS and isinstance(v, str) and v:
            encrypted[k] = encrypt_secret(v)
        else:
            encrypted[k] = v
    return encrypted


def decrypt_config_dict(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Return an in-memory copy of the integration config dictionary with all sensitive keys decrypted."""
    if not config:
        return {}
    decrypted = {}
    for k, v in config.items():
        if k in SENSITIVE_INTEGRATION_KEYS and isinstance(v, str) and v:
            decrypted[k] = decrypt_secret(v)
        else:
            decrypted[k] = v
    return decrypted


def mask_secret(value: Optional[str]) -> str:
    """Mask a secret for user-facing API responses or telemetry logs (e.g., 'sec_***abcd')."""
    if not value or not isinstance(value, str):
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"
