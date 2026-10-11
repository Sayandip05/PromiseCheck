"""Unit tests for JWT generation, cryptographic decoding, token type isolation, and Bcrypt hashing."""

from datetime import datetime, timedelta, timezone
import secrets
import uuid
import jwt
import pytest
from fastapi import HTTPException

from core.config import settings
from core.security import (
    _get_jwt_secret,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_jwt_expired_token_rejected():
    """Verify decode_token raises 401 ExpiredSignatureError when token timestamp is in past."""
    secret = _get_jwt_secret()
    past_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "expired@example.com",
        "type": "access",
        "iat": past_timestamp - 3600,
        "exp": past_timestamp,
        "jti": secrets.token_hex(16),
    }
    expired_token = jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc:
        decode_token(expired_token, expected_type="access")
    assert exc.value.status_code == 401
    assert "Token has expired" in exc.value.detail


def test_jwt_malformed_token_rejected():
    """Verify decode_token raises 401 when given malformed or garbage strings."""
    garbage = "not.a.valid.jwt.string.at.all"
    with pytest.raises(HTTPException) as exc:
        decode_token(garbage, expected_type="access")
    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail


def test_jwt_wrong_signature_rejected():
    """Verify token signed with a different key is rejected with 401."""
    different_secret = "completely-different-signing-key-0000000000000000"
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "attacker@example.com",
        "type": "access",
        "iat": now,
        "exp": now + 900,
        "jti": secrets.token_hex(16),
    }
    forged_token = jwt.encode(payload, different_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        decode_token(forged_token, expected_type="access")
    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail


def test_jwt_wrong_type_refresh_used_as_access_rejected():
    """Verify refresh token passed to decode_token(expected_type='access') is rejected."""
    raw_refresh, _, _, _ = create_refresh_token(user_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc:
        decode_token(raw_refresh, expected_type="access")
    assert exc.value.status_code == 401
    assert "Invalid token type: expected 'access'" in exc.value.detail


def test_jwt_wrong_type_access_used_as_refresh_rejected():
    """Verify access token passed to decode_token(expected_type='refresh') is rejected."""
    access_token = create_access_token(user_id=uuid.uuid4(), email="user@example.com")

    with pytest.raises(HTTPException) as exc:
        decode_token(access_token, expected_type="refresh")
    assert exc.value.status_code == 401
    assert "Invalid token type: expected 'refresh'" in exc.value.detail


def test_jwt_tampered_payload_claims_rejected():
    """Verify tampering with base64 payload claims invalidates signature verification."""
    access_token = create_access_token(user_id=uuid.uuid4(), email="victim@example.com")
    header_b64, payload_b64, sig_b64 = access_token.split(".")

    # Tamper payload by replacing characters in the base64 segment
    tampered_payload_b64 = payload_b64[:-2] + ("AA" if payload_b64[-2:] != "AA" else "BB")
    tampered_token = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"

    with pytest.raises(HTTPException) as exc:
        decode_token(tampered_token, expected_type="access")
    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail


def test_password_hash_and_verify():
    """Verify Bcrypt hashing generates salted hashes and verifies accurately."""
    pwd = "UltraSecretPassword#2026"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)

    # Hashes must differ due to distinct random salts
    assert h1 != h2
    assert h1.startswith("$2")

    # Correct password succeeds
    assert verify_password(pwd, h1) is True
    assert verify_password(pwd, h2) is True

    # Wrong password fails
    assert verify_password("WrongPassword123", h1) is False
    assert verify_password("", h1) is False
    assert verify_password(pwd, "") is False
