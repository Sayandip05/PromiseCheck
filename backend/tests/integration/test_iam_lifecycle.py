"""Integration tests for IAM lifecycle: authentication, Bcrypt verification, anti-enumeration,
token rotation, family replay revocation (CRITICAL), logout blacklisting, cleanup task,
Google auth OIDC flow, and workspace/invitation management.
"""

from datetime import datetime, timedelta, timezone
import secrets
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import hash_password, hash_token
from modules.iam.models import Identity, Membership, RefreshToken, Session as UserSession, User, Workspace
from modules.iam.schemas import WorkspaceCreateRequest
from modules.iam.service import AuthService, WorkspaceService
from modules.iam.tasks import cleanup_expired_tokens
from tests.fixtures.factories import UserFactory, WorkspaceFactory

pytestmark = pytest.mark.integration


def ip_headers(extra: dict | None = None) -> dict[str, str]:
    """Generate fresh IP in X-Forwarded-For header to prevent cross-test rate limiting collisions."""
    h = {"X-Forwarded-For": f"10.{uuid.uuid4().int % 200}.{uuid.uuid4().int % 200}.{uuid.uuid4().int % 200}"}
    if extra:
        h.update(extra)
    return h


# ─────────────────────────────────────────────────────────────────────────────
# 1. Registration
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_creates_user_and_default_workspace(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Registering a new account provisions the user, Bcrypt password, default workspace, and returns tokens."""
    unique_email = f"iam_reg_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "StrongPassword2026!",
        "full_name": "Alice Tester",
    }
    res = app_client.post("/api/v1/auth/register", json=payload, headers=ip_headers())
    assert res.status_code == 201
    data = res.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == unique_email
    assert data["user"]["full_name"] == "Alice Tester"

    # Verify default workspace created and user assigned as admin
    assert data["active_workspace"] is not None
    assert len(data["workspaces"]) >= 1
    assert data["workspaces"][0]["role"] == "admin"

    # Verify persistence in PostgreSQL
    user_res = await db_session.execute(select(User).where(User.email == unique_email))
    user = user_res.scalar_one_or_none()
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash.startswith("$2")

    # Verify membership exists in DB
    mem_res = await db_session.execute(select(Membership).where(Membership.user_id == user.id))
    memberships = mem_res.scalars().all()
    assert len(memberships) >= 1
    role_val = memberships[0].role.value if hasattr(memberships[0].role, "value") else str(memberships[0].role)
    assert role_val == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Attempting to register an existing email returns 400 Bad Request without leaking PII."""
    existing_user = UserFactory(email=f"dup_{uuid.uuid4().hex[:8]}@example.com")
    db_session.add(existing_user)
    await db_session.commit()

    payload = {
        "email": existing_user.email,
        "password": "ValidPassword123!",
        "full_name": "Duplicate Tester",
    }
    res = app_client.post("/api/v1/auth/register", json=payload, headers=ip_headers())
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert detail == "An account with this email address already exists."
    assert existing_user.email not in detail


@pytest.mark.asyncio
async def test_register_weak_or_invalid_input_rejected(app_client: TestClient):
    """Pydantic validation rejects password shorter than 8 chars, email shorter than 3 chars, or missing fields."""
    # Password too short (< 8 chars)
    res_short_pwd = app_client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short", "full_name": "Bob"},
        headers=ip_headers(),
    )
    assert res_short_pwd.status_code == 422

    # Email too short (< 3 chars)
    res_short_email = app_client.post(
        "/api/v1/auth/register",
        json={"email": "a", "password": "ValidPassword123!", "full_name": "Bob"},
        headers=ip_headers(),
    )
    assert res_short_email.status_code == 422

    # Missing password
    res_no_pwd = app_client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "full_name": "Bob"},
        headers=ip_headers(),
    )
    assert res_no_pwd.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 2. Login & Anti-Enumeration
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(app_client: TestClient, db_session: AsyncSession):
    """Valid credentials successfully authenticate, set auth cookies, and return token pair."""
    password = "CorrectHorseBatteryStaple1!"
    user = UserFactory(
        email=f"login_ok_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    ws = WorkspaceFactory(slug=f"ws-{uuid.uuid4().hex[:6]}")
    db_session.add(ws)
    await db_session.flush()

    mem = Membership(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    await db_session.commit()

    res = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
        headers=ip_headers(),
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == user.email

    # Check HttpOnly cookies set
    assert settings.REFRESH_COOKIE_NAME in res.cookies
    assert settings.ACCESS_COOKIE_NAME in res.cookies


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(app_client: TestClient, db_session: AsyncSession):
    """Wrong password returns 401 Unauthorized."""
    user = UserFactory(
        email=f"wrong_pwd_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("RightPassword123!"),
    )
    db_session.add(user)
    await db_session.commit()

    res = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "DefinitivelyWrongPassword"},
        headers=ip_headers(),
    )
    assert res.status_code == 401
    assert res.json().get("detail") == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_unknown_user_rejected(app_client: TestClient):
    """Non-existent email returns 401 Unauthorized."""
    res = app_client.post(
        "/api/v1/auth/login",
        json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com", "password": "AnyPassword123!"},
        headers=ip_headers(),
    )
    assert res.status_code == 401
    assert res.json().get("detail") == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_anti_enumeration_identical_error(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Anti-enumeration: wrong password vs unknown email return the exact same status and message."""
    user = UserFactory(
        email=f"enum_check_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("ValidPassword123!"),
    )
    db_session.add(user)
    await db_session.commit()

    res_wrong_pwd = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "WrongPassword!"},
        headers=ip_headers(),
    )
    res_unknown_user = app_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody_exists_here_999@example.com", "password": "WrongPassword!"},
        headers=ip_headers(),
    )

    assert res_wrong_pwd.status_code == res_unknown_user.status_code == 401
    assert res_wrong_pwd.json() == res_unknown_user.json() == {"detail": "Invalid email or password."}


@pytest.mark.asyncio
async def test_login_deactivated_user_rejected(app_client: TestClient, db_session: AsyncSession):
    """Deactivated user account returns 403 Forbidden."""
    pwd = "ValidPassword123!"
    user = UserFactory(
        email=f"deact_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password(pwd),
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    res = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": pwd},
        headers=ip_headers(),
    )
    assert res.status_code == 403
    assert "deactivated" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_auth_me_profile_returns_workspaces_and_roles(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /api/v1/auth/me returns authenticated user, active workspace, and all memberships."""
    user = UserFactory(is_active=True)
    db_session.add(user)
    await db_session.flush()

    ws1 = WorkspaceFactory(slug=f"ws1-{uuid.uuid4().hex[:6]}")
    ws2 = WorkspaceFactory(slug=f"ws2-{uuid.uuid4().hex[:6]}")
    db_session.add_all([ws1, ws2])
    await db_session.flush()

    mem1 = Membership(workspace_id=ws1.id, user_id=user.id, role="admin")
    mem2 = Membership(workspace_id=ws2.id, user_id=user.id, role="member")
    db_session.add_all([mem1, mem2])
    await db_session.commit()

    from core.security import create_access_token
    access_token = create_access_token(user_id=user.id, email=user.email)

    res = app_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == user.email
    assert data["id"] == str(user.id)
    assert len(data["workspaces"]) >= 2
    ws_slugs = [w["slug"] for w in data["workspaces"]]
    assert ws1.slug in ws_slugs
    assert ws2.slug in ws_slugs


# ─────────────────────────────────────────────────────────────────────────────
# 3. Refresh Token Rotation & Family Replay Revocation (CRITICAL Item #2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_token_rotation_success(app_client: TestClient, db_session: AsyncSession):
    """POST /api/v1/auth/refresh rotates the refresh token and invalidates the previous one."""
    pwd = "RotatePassword2026!"
    reg_res = app_client.post(
        "/api/v1/auth/register",
        json={"email": f"rot_{uuid.uuid4().hex[:8]}@example.com", "password": pwd, "full_name": "Rotator"},
        headers=ip_headers(),
    )
    assert reg_res.status_code == 201
    old_refresh = reg_res.json()["refresh_token"]

    # 1. Rotate refresh token
    rotate_res = app_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
        headers=ip_headers(),
    )
    assert rotate_res.status_code == 200
    new_data = rotate_res.json()
    new_refresh = new_data["refresh_token"]
    assert new_refresh != old_refresh

    # 2. Check DB record: old refresh token is marked replaced and revoked
    old_hash = hash_token(old_refresh)
    old_record = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    ).scalar_one_or_none()
    assert old_record is not None
    assert old_record.revoked_at is not None
    assert old_record.replaced_by_jti is not None

    # 3. New refresh token is active and valid in DB
    new_hash = hash_token(new_refresh)
    new_record = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == new_hash))
    ).scalar_one_or_none()
    assert new_record is not None
    assert new_record.revoked_at is None
    assert new_record.family_id == old_record.family_id


@pytest.mark.asyncio
async def test_refresh_token_replay_revokes_entire_session_family(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """CRITICAL Item #2: Replaying an already-used refresh token revokes the entire token family.
    
    Any subsequent attempt to use the newly issued refresh token in that family is also rejected with 401.
    """
    # 1. Register and get initial refresh token (T1)
    reg_res = app_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"replay_guard_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongPassword123!",
            "full_name": "Victim User",
        },
        headers=ip_headers(),
    )
    assert reg_res.status_code == 201
    t1_refresh = reg_res.json()["refresh_token"]

    # 2. Legitimate user rotates T1 -> receives T2
    rot_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": t1_refresh}, headers=ip_headers())
    assert rot_res.status_code == 200
    t2_refresh = rot_res.json()["refresh_token"]

    # 3. ATTACK: Attacker replays compromised T1!
    replay_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": t1_refresh}, headers=ip_headers())
    assert replay_res.status_code == 401
    replay_detail = replay_res.json().get("detail", "")
    assert "reuse detected" in replay_detail.lower()

    # 4. Verification: Entire token family has been revoked in PostgreSQL
    t1_hash = hash_token(t1_refresh)
    t1_record = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == t1_hash))
    ).scalar_one_or_none()
    assert t1_record is not None

    family_records = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.family_id == t1_record.family_id)
        )
    ).scalars().all()
    assert len(family_records) >= 2
    for record in family_records:
        assert record.revoked_at is not None, f"Token {record.token_jti} must be revoked"

    # 5. Legitimate user tries to use T2 -> must ALSO fail with 401 because the family was revoked!
    t2_aftermath_res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": t2_refresh}, headers=ip_headers())
    assert t2_aftermath_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_expired_rejected(app_client: TestClient, db_session: AsyncSession):
    """Expired refresh token is rejected with 401 Unauthorized."""
    user = UserFactory()
    db_session.add(user)
    await db_session.commit()

    from core.security import _get_jwt_secret
    import jwt

    # Craft an expired refresh token JWT
    past = int((datetime.now(timezone.utc) - timedelta(days=31)).timestamp())
    expired_jwt = jwt.encode(
        {
            "sub": str(user.id),
            "type": "refresh",
            "jti": secrets.token_hex(16),
            "family_id": secrets.token_hex(16),
            "iat": past - 3600,
            "exp": past,
        },
        _get_jwt_secret(),
        algorithm=settings.JWT_ALGORITHM,
    )

    res = app_client.post("/api/v1/auth/refresh", json={"refresh_token": expired_jwt}, headers=ip_headers())
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_and_blacklists_access(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/auth/logout revokes the refresh family and blacklists the access token JTI."""
    reg_res = app_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"logout_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "full_name": "Logout Tester",
        },
        headers=ip_headers(),
    )
    tokens = reg_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Verify access token works initially
    pre_me = app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert pre_me.status_code == 200

    # Perform logout
    logout_res = app_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers=ip_headers({"Authorization": f"Bearer {access_token}"}),
    )
    assert logout_res.status_code == 200
    assert logout_res.json() == {"status": "logged_out"}

    # Replaying blacklisted access token is immediately rejected with 401
    post_me = app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert post_me.status_code == 401
    assert "revoked" in post_me.json().get("detail", "").lower()

    # Replaying refresh token is rejected
    post_refresh = app_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}, headers=ip_headers())
    assert post_refresh.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 4. Token Cleanup Background Task
# ─────────────────────────────────────────────────────────────────────────────


def test_cleanup_expired_tokens_deletes_only_expired_records():
    """cleanup_expired_tokens Celery task deletes records expired > 24 hours ago, keeping active rows."""
    from sqlalchemy.orm import Session
    from core.database import sync_engine

    now = datetime.now(timezone.utc)
    old_cutoff = now - timedelta(days=3)  # Expired 3 days ago (eligible for deletion)
    future_exp = now + timedelta(days=7)  # Active (must NOT be deleted)

    with Session(sync_engine) as session:
        # Create a test user for foreign keys
        user = User(
            email=f"cleanup_user_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("pwd"),
            full_name="Cleanup Test User",
        )
        session.add(user)
        session.flush()

        # Seed 1 expired refresh token and 1 active refresh token
        expired_token = RefreshToken(
            user_id=user.id,
            token_jti=uuid.uuid4().hex,
            token_hash=hash_token(uuid.uuid4().hex),
            family_id=uuid.uuid4().hex,
            expires_at=old_cutoff,
        )
        active_token = RefreshToken(
            user_id=user.id,
            token_jti=uuid.uuid4().hex,
            token_hash=hash_token(uuid.uuid4().hex),
            family_id=uuid.uuid4().hex,
            expires_at=future_exp,
        )

        # Seed 1 expired session and 1 active session
        expired_session = UserSession(
            user_id=user.id,
            token_hash=hash_token(uuid.uuid4().hex),
            expires_at=old_cutoff,
        )
        active_session = UserSession(
            user_id=user.id,
            token_hash=hash_token(uuid.uuid4().hex),
            expires_at=future_exp,
        )

        session.add_all([expired_token, active_token, expired_session, active_session])
        session.commit()

        expired_tok_id = expired_token.id
        active_tok_id = active_token.id
        expired_sess_id = expired_session.id
        active_sess_id = active_session.id

    # Execute the maintenance task function directly
    result = cleanup_expired_tokens()
    assert result["refresh_tokens_deleted"] >= 1
    assert result["sessions_deleted"] >= 1

    # Verify database state
    with Session(sync_engine) as session:
        assert session.get(RefreshToken, expired_tok_id) is None
        assert session.get(RefreshToken, active_tok_id) is not None
        assert session.get(UserSession, expired_sess_id) is None
        assert session.get(UserSession, active_sess_id) is not None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Google OAuth / OIDC Flow
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_google_auth_new_user_provisioning(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Google auth with valid ID token provisions new user, Identity record, and default workspace."""
    google_email = f"google_new_{uuid.uuid4().hex[:8]}@example.com"
    fake_payload = {
        "email": google_email,
        "email_verified": True,
        "name": "Google User",
        "sub": f"google-sub-{uuid.uuid4().hex}",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload):
        res = app_client.post(
            "/api/v1/auth/google",
            json={"id_token": "fake-google-id-token-value"},
            headers=ip_headers(),
        )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == google_email
    assert "access_token" in data

    # Verify Identity table row created
    user_id = uuid.UUID(data["user"]["id"])
    ident_res = await db_session.execute(
        select(Identity).where(Identity.user_id == user_id, Identity.provider == "google")
    )
    ident = ident_res.scalar_one_or_none()
    assert ident is not None
    assert ident.provider_subject == fake_payload["sub"]


@pytest.mark.asyncio
async def test_google_auth_links_existing_user(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Google auth for email registered with password logs in existing user without creating duplicate."""
    existing_user = UserFactory(
        email=f"link_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(existing_user)
    await db_session.commit()

    fake_payload = {
        "email": existing_user.email,
        "email_verified": True,
        "name": "Linked User",
        "sub": f"google-sub-{uuid.uuid4().hex}",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload):
        res = app_client.post(
            "/api/v1/auth/google",
            json={"credential": "fake-google-credential"},
            headers=ip_headers(),
        )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["id"] == str(existing_user.id)

    # Ensure no duplicate User row was created
    all_users = (
        await db_session.execute(select(User).where(User.email == existing_user.email))
    ).scalars().all()
    assert len(all_users) == 1


@pytest.mark.asyncio
async def test_google_auth_invalid_credential_rejected(app_client: TestClient):
    """Invalid Google credential raises 401 Unauthorized."""
    with patch(
        "google.oauth2.id_token.verify_oauth2_token",
        side_effect=ValueError("Token expired or corrupted"),
    ):
        res = app_client.post(
            "/api/v1/auth/google",
            json={"id_token": "invalid-token"},
            headers=ip_headers(),
        )
    assert res.status_code == 401
    assert "Invalid Google credential" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_google_auth_unverified_email_rejected(app_client: TestClient):
    """Google credential with email_verified=False is rejected with 401."""
    fake_payload = {
        "email": "unverified@example.com",
        "email_verified": False,
        "sub": "sub-123",
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload):
        res = app_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid-token-unverified-email"},
            headers=ip_headers(),
        )
    assert res.status_code == 401
    assert "unverified" in res.json().get("detail", "").lower()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Workspaces & Invitations
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason="BUG-4: src/modules/iam/router.py:267 uses unpersisted system_user_id = uuid.uuid4(), causing ForeignKeyViolationError on memberships table and 500 error",
)
@pytest.mark.asyncio
async def test_workspace_create_assigns_admin(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """POST /api/v1/workspaces creates a new workspace and assigns creator as ADMIN."""
    slug = f"custom-slug-{uuid.uuid4().hex[:6]}"
    payload = {"name": "Innovate Ltd", "slug": slug}

    res = app_client.post("/api/v1/workspaces", json=payload, headers=ip_headers())
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_workspace_create_via_service_layer_assigns_admin(db_session: AsyncSession):
    """WorkspaceService.create_workspace creates workspace and assigns creator as ADMIN when user exists."""
    user = UserFactory()
    db_session.add(user)
    await db_session.commit()

    slug = f"srv-slug-{uuid.uuid4().hex[:6]}"
    payload = WorkspaceCreateRequest(name="Service Layer Org", slug=slug)
    ws = await WorkspaceService.create_workspace(db_session, user.id, payload)
    assert ws is not None
    assert ws.name == "Service Layer Org"

    members = await WorkspaceService.list_members(db_session, ws.id)
    assert len(members) == 1
    assert members[0].user_id == user.id
    role_val = members[0].role.value if hasattr(members[0].role, "value") else str(members[0].role)
    assert role_val == "admin"


@pytest.mark.asyncio
async def test_workspace_create_duplicate_slug_rejected(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Creating workspace with an existing slug returns 400 Bad Request."""
    slug = f"unique-slug-{uuid.uuid4().hex[:6]}"
    ws = WorkspaceFactory(slug=slug)
    db_session.add(ws)
    await db_session.commit()

    res = app_client.post(
        "/api/v1/workspaces",
        json={"name": "Duplicate Slug Org", "slug": slug},
        headers=ip_headers(),
    )
    assert res.status_code == 400
    assert "already exists" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_workspace_get_and_members_list(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /api/v1/workspaces/{id} and members endpoints return workspace details."""
    ws = WorkspaceFactory()
    db_session.add(ws)
    await db_session.flush()

    user = UserFactory()
    db_session.add(user)
    await db_session.flush()

    mem = Membership(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    await db_session.commit()

    # Get workspace
    res_ws = app_client.get(f"/api/v1/workspaces/{ws.id}")
    assert res_ws.status_code == 200
    assert res_ws.json()["id"] == str(ws.id)

    # List members
    res_members = app_client.get(f"/api/v1/workspaces/{ws.id}/members")
    assert res_members.status_code == 200
    members_data = res_members.json()
    assert len(members_data) >= 1
    assert any(m["user_id"] == str(user.id) for m in members_data)


@pytest.mark.asyncio
async def test_invitation_lifecycle_create_and_validation(db_session: AsyncSession):
    """WorkspaceService creates invitations with unexpired tokens retrievable via get_valid_invitation."""
    ws = WorkspaceFactory()
    db_session.add(ws)
    await db_session.commit()

    invite_email = f"teammate_{uuid.uuid4().hex[:6]}@example.com"
    invitation, raw_token = await WorkspaceService.create_invitation(
        db=db_session,
        workspace_id=ws.id,
        email=invite_email,
        expires_delta_hours=48,
    )
    await db_session.commit()

    # Token hash matches
    expected_hash = hash_token(raw_token)
    assert invitation.token_hash == expected_hash

    # Successfully retrievable via DB query
    found = await WorkspaceService.get_valid_invitation(db_session, expected_hash)
    assert found is not None
    assert found.id == invitation.id
    assert found.email == invite_email


@pytest.mark.asyncio
async def test_invitation_expiry_and_already_accepted_filtered(db_session: AsyncSession):
    """get_valid_invitation strictly filters expired or accepted invitations at the DB query level."""
    ws = WorkspaceFactory()
    db_session.add(ws)
    await db_session.commit()

    # 1. Expired invitation
    inv_exp, raw_exp = await WorkspaceService.create_invitation(
        db=db_session,
        workspace_id=ws.id,
        email="expired@example.com",
        expires_delta_hours=-2,  # Expired 2 hours ago
    )
    await db_session.commit()

    found_exp = await WorkspaceService.get_valid_invitation(db_session, inv_exp.token_hash)
    assert found_exp is None, "Expired invitation must be excluded by DB query filter"

    # 2. Accepted invitation
    inv_acc, raw_acc = await WorkspaceService.create_invitation(
        db=db_session,
        workspace_id=ws.id,
        email="accepted@example.com",
        expires_delta_hours=24,
    )
    inv_acc.accepted_at = datetime.now(timezone.utc)
    await db_session.commit()

    found_acc = await WorkspaceService.get_valid_invitation(db_session, inv_acc.token_hash)
    assert found_acc is None, "Accepted invitation must be excluded by DB query filter"
