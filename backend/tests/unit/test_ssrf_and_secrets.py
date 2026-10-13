"""Unit tests for SSRF protection guard and secret encryption at rest.

CRITICAL Item #7:
- SSRF guard blocks private IPv4, metadata endpoints, IPv6 loopback/link-local/ULA,
  IPv4-mapped IPv6, DNS rebinding, and malformed schemes.

CRITICAL Item #8:
- Secret envelope encryption roundtrip, tampered ciphertext safety, wrong key rejection.
- Secret masking and integration config sanitization.
- Verification that integration secrets never appear in logs or plaintext.
"""

import logging
import socket
from unittest.mock import patch
import pytest
from fastapi import HTTPException

from connectors.ssrf_guard import _is_blocked_ip, validate_no_ssrf
from core.secret_encryption import (
    SENSITIVE_INTEGRATION_KEYS,
    decrypt_config_dict,
    decrypt_secret,
    encrypt_config_dict,
    encrypt_secret,
    mask_secret,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRITICAL Item #7: Comprehensive SSRF Guard Checks
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "blocked_ip",
    [
        # Loopback IPv4
        "127.0.0.1",
        "127.0.0.2",
        "127.255.255.254",
        # Loopback IPv6
        "::1",
        # RFC-1918 Private class A, B, C
        "10.0.0.1",
        "10.254.254.254",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.1.1",
        "192.168.254.254",
        # Cloud metadata / link-local
        "169.254.169.254",
        "169.254.1.1",
        # IPv6 link-local and unique local
        "fe80::1",
        "fc00::1",
        "fd12:3456:789a::1",
        # Unspecified & Carrier-grade NAT
        "0.0.0.0",
        "100.64.0.1",
        "100.127.255.255",
    ],
)
def test_ssrf_is_blocked_ip_detects_all_internal_ranges(blocked_ip: str):
    """CRITICAL Item #7: _is_blocked_ip returns True for every internal, loopback, or metadata address."""
    assert _is_blocked_ip(blocked_ip) is True, f"IP {blocked_ip} should be blocked"


@pytest.mark.xfail(
    strict=True,
    reason="BUG-6: ssrf_guard fails to unmap IPv4-mapped IPv6 addresses (::ffff:x.x.x.x), allowing SSRF bypass to loopback and cloud metadata",
)
@pytest.mark.parametrize(
    "ipv4_mapped_ip",
    [
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "::ffff:10.0.0.1",
        "::ffff:192.168.1.1",
    ],
)
def test_ssrf_is_blocked_ip_detects_ipv4_mapped_ipv6_addresses(ipv4_mapped_ip: str):
    """CRITICAL Item #7: _is_blocked_ip unmaps IPv4-mapped IPv6 addresses to prevent SSRF bypass."""
    assert _is_blocked_ip(ipv4_mapped_ip) is True, f"IPv4-mapped IP {ipv4_mapped_ip} should be blocked"


@pytest.mark.parametrize(
    "public_ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",
        "2607:f8b0:4005:805::200e",  # Google IPv6
    ],
)
def test_ssrf_is_blocked_ip_allows_legitimate_public_ips(public_ip: str):
    """CRITICAL Item #7: _is_blocked_ip returns False for legitimate public Internet IP addresses."""
    assert _is_blocked_ip(public_ip) is False, f"Public IP {public_ip} should NOT be blocked"


@pytest.mark.parametrize(
    "metadata_hostname",
    [
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.com/test",
        "http://instance-data.ec2.internal/latest/",
    ],
)
def test_ssrf_guard_blocks_cloud_metadata_endpoints(metadata_hostname: str):
    """CRITICAL Item #7: validate_no_ssrf blocks well-known AWS/GCP/Azure instance metadata URLs."""
    with pytest.raises(HTTPException) as exc_info:
        validate_no_ssrf(metadata_hostname)
    assert exc_info.value.status_code == 400


def test_ssrf_guard_blocks_dns_rebinding_to_private_ip():
    """CRITICAL Item #7: A public-looking hostname that resolves via DNS to a private IP is blocked."""
    # Simulate a domain that resolves to 192.168.1.100 (e.g., DNS rebinding attack)
    fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.100", 80))]

    with patch("socket.getaddrinfo", return_value=fake_addrinfo):
        with pytest.raises(HTTPException) as exc_info:
            validate_no_ssrf("https://attacker-rebound-domain.com/webhook")
        assert exc_info.value.status_code == 400
        assert "internal IP range" in exc_info.value.detail


@pytest.mark.parametrize(
    "malformed_or_dangerous_url",
    [
        "",
        "   ",
        "not-a-valid-url",
        "http://",
        "https://",
    ],
)
def test_ssrf_guard_rejects_empty_or_malformed_urls(malformed_or_dangerous_url: str):
    """validate_no_ssrf raises 400 on empty, whitespace, or malformed URLs."""
    with pytest.raises(HTTPException) as exc_info:
        validate_no_ssrf(malformed_or_dangerous_url)
    assert exc_info.value.status_code == 400


def test_ssrf_guard_allows_valid_public_domain():
    """validate_no_ssrf succeeds cleanly for legitimate public SaaS endpoints."""
    # Mock DNS resolution to public IP 142.250.190.46
    fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.190.46", 443))]

    with patch("socket.getaddrinfo", return_value=fake_addrinfo):
        # Should execute without raising HTTPException
        validate_no_ssrf("https://hooks.slack.com/services/T00/B00/XXXX")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CRITICAL Item #8: Secrets & Credential Sanitization
# ─────────────────────────────────────────────────────────────────────────────


def test_secret_encryption_roundtrip():
    """CRITICAL Item #8: Plaintext secret encrypts to Fernet ciphertext and decrypts identically."""
    secret = "sk-proj-super-sensitive-api-token-123456789"
    cipher_text = encrypt_secret(secret)

    # Ciphertext must begin with Fernet header and not match plaintext
    assert cipher_text.startswith("gAAAAA")
    assert cipher_text != secret

    # Decrypt restores identical plaintext
    decrypted = decrypt_secret(cipher_text)
    assert decrypted == secret


def test_encrypt_secret_idempotent_on_already_encrypted_ciphertext():
    """Encrypting an already-encrypted Fernet string does not double-encrypt."""
    secret = "ghp_github_personal_access_token_999"
    token = encrypt_secret(secret)
    token_second = encrypt_secret(token)
    assert token_second == token


def test_decrypt_secret_tampered_ciphertext_safety():
    """Tampered ciphertext is safely handled without raising unhandled exception."""
    tampered = "gAAAAABfakeCorruptedCiphertextThatCannotBeDecrypted12345="
    result = decrypt_secret(tampered)
    # Falls back to returning input without crashing
    assert result == tampered


def test_decrypt_secret_legacy_plaintext_passthrough():
    """Plaintext secrets created prior to encryption migration pass through intact."""
    legacy_secret = "legacy_unencrypted_token_value"
    assert decrypt_secret(legacy_secret) == legacy_secret


def test_mask_secret_redacts_credentials_for_ui_and_telemetry():
    """mask_secret masks the middle of secrets while preserving short prefix/suffix."""
    long_secret = "tokn-1234567890-abcdefghijklmnop"
    masked = mask_secret(long_secret)
    assert masked == "tokn***mnop"
    assert "1234567890" not in masked

    short_secret = "secret"
    assert mask_secret(short_secret) == "***"
    assert mask_secret("") == ""
    assert mask_secret(None) == ""


def test_config_dict_encryption_sanitizes_only_sensitive_keys():
    """CRITICAL Item #8: encrypt_config_dict encrypts sensitive keys while keeping non-sensitive keys readable."""
    raw_config = {
        "api_key": "raw_sensitive_api_key_123",
        "bot_token": "xoxb-raw-bot-token-456",
        "client_secret": "raw_client_secret_789",
        "channel": "#general",
        "enabled": True,
        "max_retries": 3,
    }

    encrypted_config = encrypt_config_dict(raw_config)

    # Sensitive keys are encrypted
    assert encrypted_config["api_key"].startswith("gAAAAA")
    assert encrypted_config["bot_token"].startswith("gAAAAA")
    assert encrypted_config["client_secret"].startswith("gAAAAA")
    assert "raw_sensitive_api_key_123" not in encrypted_config["api_key"]

    # Non-sensitive keys remain intact
    assert encrypted_config["channel"] == "#general"
    assert encrypted_config["enabled"] is True
    assert encrypted_config["max_retries"] == 3

    # Decrypt restores original configuration
    restored = decrypt_config_dict(encrypted_config)
    assert restored == raw_config


def test_sensitive_integration_keys_constant():
    """All expected sensitive credentials keys are included in SENSITIVE_INTEGRATION_KEYS."""
    required_keys = {"api_key", "bot_token", "access_token", "refresh_token", "client_secret", "webhook_url"}
    assert required_keys.issubset(SENSITIVE_INTEGRATION_KEYS)


def test_integration_secrets_never_appear_in_sanitized_logs(caplog: pytest.LogCaptureFixture):
    """CRITICAL Item #8: Sanitized configuration dictionaries do not leak raw secret tokens in logs."""
    raw_secret = "super_confidential_slack_bot_token_abc123"
    config = {
        "bot_token": raw_secret,
        "channel": "#alerts",
    }

    # Encrypt config before any logging or persistence
    safe_config = encrypt_config_dict(config)

    test_logger = logging.getLogger("test_logger")
    with caplog.at_level(logging.INFO):
        test_logger.info(f"Connecting integration with configuration: {safe_config}")

    # Raw secret must NEVER appear in the captured log text
    assert raw_secret not in caplog.text
    assert "gAAAAA" in caplog.text  # Encrypted representation is logged instead
