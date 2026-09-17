"""Security tests for JWT token rotation, lifecycle, and replay attack prevention."""

import uuid
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_jwt_token_rotation_and_replay_protection(client: TestClient):
    """Test full JWT token lifecycle, refresh token rotation, and replay attack invalidation."""
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    # 1. Register a new user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Test Security User",
        },
    )
    assert reg_res.status_code == 201
    tokens = reg_res.json()
    access_token_1 = tokens["access_token"]
    refresh_token_1 = tokens["refresh_token"]
    assert access_token_1
    assert refresh_token_1

    # 2. Access /auth/me with valid access token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token_1}"},
    )
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == unique_email

    # 3. Rotate refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    access_token_2 = new_tokens["access_token"]
    refresh_token_2 = new_tokens["refresh_token"]
    assert access_token_2
    assert refresh_token_2
    assert refresh_token_2 != refresh_token_1

    # 4. Verify new access token works
    me_res_2 = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token_2}"},
    )
    assert me_res_2.status_code == 200

    # 5. Replay attack: attempting to reuse old refresh token MUST fail
    replay_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert replay_res.status_code == 401
    assert "revoked" in replay_res.json().get("detail", "").lower() or "invalid" in replay_res.json().get("detail", "").lower()

    # 6. Rejection with invalid or missing token
    bad_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert bad_res.status_code == 401
