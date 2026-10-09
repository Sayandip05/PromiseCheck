"""Legacy compatibility module for secret encryption.

FEATURE NOTICE:
This module has been renamed to `core.secret_encryption` to provide unambiguous,
feature-based naming for engineers and avoid confusion with cryptocurrency / blockchain.

Please import directly from `core.secret_encryption` in all new code.
"""

from core.secret_encryption import (
    SENSITIVE_KEYS,
    SENSITIVE_INTEGRATION_KEYS,
    decrypt_config_dict,
    decrypt_secret,
    encrypt_config_dict,
    encrypt_secret,
    get_encryption_cipher,
    get_fernet,
    mask_secret,
)

__all__ = [
    "SENSITIVE_KEYS",
    "SENSITIVE_INTEGRATION_KEYS",
    "decrypt_config_dict",
    "decrypt_secret",
    "encrypt_config_dict",
    "encrypt_secret",
    "get_encryption_cipher",
    "get_fernet",
    "mask_secret",
]
