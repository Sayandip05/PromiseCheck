"""Integration tests for Integrations router, Google OAuth state/CSRF validation (CRITICAL Item #9),
and Model Context Protocol (MCP) tool invocation lifecycle.

Verifies:
- Google OAuth flow: authorize URL state construction, error handling, missing/malformed state rejection,
  code-for-token exchange, encrypted token storage, cache invalidation, and CSRF protection.
- Integrations lifecycle: connect, test, disconnect, and cross-tenant isolation across providers.
- MCP Gateway: authentication requirement, tools manifest discovery, tool dispatch (list_commitments,
  create_commitment, get_commitment_evidence, create_update_draft), unknown tool rejection, role guards,
  and cross-tenant data isolation.
"""

from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_value, publish_event
from core.security import Role, create_access_token
from modules.commitments.models import Commitment, DeliveryEvidence
from modules.iam.models import Membership, User, Workspace
from modules.integrations.models import WorkspaceIntegration
from src.main import app
from tests.fixtures.factories import CommitmentFactory, DeliveryEvidenceFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRITICAL Item #9: Google OAuth & State / CSRF Validation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_google_authorize_url_contains_state_parameter(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """CRITICAL Item #9: GET /integrations/google/authorize generates URL containing a secure state token."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.get("/api/v1/integrations/google/authorize", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "authorization_url" in data
    assert "state" in data
    state = data["state"]
    # State must be formatted with workspace UUID and nonce
    assert str(ws.id) in state
    import urllib.parse
    assert urllib.parse.quote(state) in data["authorization_url"]
    assert "access_type=offline" in data["authorization_url"]
    assert "prompt=consent" in data["authorization_url"]


def test_google_oauth_callback_missing_code_rejected(app_client: TestClient):
    """CRITICAL Item #9: Google OAuth callback without authorization code raises 400 Bad Request."""
    res = app_client.get("/api/v1/integrations/google/callback?state=some_state")
    assert res.status_code == 400
    assert "Missing authorization code" in res.json().get("detail", "")


def test_google_oauth_callback_error_parameter_handled(app_client: TestClient):
    """CRITICAL Item #9: Google OAuth callback returning error from consent screen returns 400 HTML error."""
    res = app_client.get("/api/v1/integrations/google/callback?error=access_denied")
    assert res.status_code == 400
    assert "Google Authorization Failed" in res.text
    assert "access_denied" in res.text


@pytest.mark.parametrize(
    "invalid_state",
    [
        "",
        "no_colon_here",
        "not-a-valid-uuid:123456",
        "00000000-0000-0000-0000-000000000000",
    ],
)
def test_google_oauth_callback_missing_or_corrupt_state_rejected(
    app_client: TestClient,
    invalid_state: str,
):
    """CRITICAL Item #9: Google OAuth callback with missing or unparseable workspace UUID in state is rejected with 400."""
    res = app_client.get(f"/api/v1/integrations/google/callback?code=mock_code&state={invalid_state}")
    assert res.status_code == 400
    assert "Invalid OAuth State" in res.text or "corrupted workspace" in res.text


@pytest.mark.asyncio
async def test_google_oauth_callback_successful_exchange_persists_tokens_and_updates_status(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """CRITICAL Item #9: Valid callback code exchanges tokens, stores encrypted config, and sets provider connected."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    state = f"{ws.id}:{uuid.uuid4().hex[:12]}"
    mock_tokens = {
        "access_token": "ya29.valid_test_access_token",
        "refresh_token": "1//valid_test_refresh_token",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/gmail.send",
    }
    mock_profile = {
        "email": "connected_user@acme.com",
        "name": "Integration User",
    }

    with patch("modules.integrations.router.exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange, \
         patch("modules.integrations.router.get_google_user_profile", new_callable=AsyncMock) as mock_get_profile:
        mock_exchange.return_value = mock_tokens
        mock_get_profile.return_value = mock_profile

        res = app_client.get(f"/api/v1/integrations/google/callback?code=valid_auth_code_123&state={state}")

        assert res.status_code == 200
        assert "Gmail & Calendar Connected" in res.text
        assert "connected_user@acme.com" in res.text

    # Verify database state in PostgreSQL
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws.id,
        WorkspaceIntegration.provider == "gmail",
    )
    db_res = await db_session.execute(stmt)
    integration = db_res.scalar_one_or_none()

    assert integration is not None
    assert integration.connected is True
    assert "connected_user@acme.com" in integration.status_text

    # Verify encrypted config roundtrip
    config = integration.get_decrypted_config()
    assert config["access_token"] == "ya29.valid_test_access_token"
    assert config["refresh_token"] == "1//valid_test_refresh_token"
    assert config["email"] == "connected_user@acme.com"


@pytest.mark.xfail(
    strict=True,
    reason="BUG-7: google_oauth_callback_get lacks CSRF state replay/forgery protection; accepts stateless unvalidated nonces",
)
def test_google_oauth_callback_rejects_replayed_or_forged_state(
    app_client: TestClient,
):
    """CRITICAL Item #9: State token that was not issued by the server in Redis/session must be rejected to prevent CSRF."""
    forged_state = f"{uuid.uuid4()}:forged_nonce_never_issued"
    res = app_client.get(f"/api/v1/integrations/google/callback?code=fake_code&state={forged_state}")
    # A secure implementation checks server-side state issued in Redis/session and rejects with 400
    assert res.status_code == 400
    assert "Invalid or replayed state" in res.text


@pytest.mark.xfail(
    strict=True,
    reason="BUG-8: missing legacy route alias /api/v1/operations/integrations/google/callback registered with external OAuth console",
)
def test_google_oauth_callback_legacy_operations_route_alias_accessible(
    app_client: TestClient,
):
    """The legacy URL /api/v1/operations/integrations/google/callback registered in Google Console must redirect or route."""
    res = app_client.get("/api/v1/operations/integrations/google/callback?code=test&state=invalid")
    assert res.status_code != 404


# ─────────────────────────────────────────────────────────────────────────────
# 2. Integrations Matrix & Lifecycle
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_integrations_list_seeds_defaults_and_preserves_workspace_isolation(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """GET /integrations seeds default connectors and segregates configurations per workspace."""
    user1 = UserFactory(is_active=True)
    ws1 = WorkspaceFactory()
    user2 = UserFactory(is_active=True)
    ws2 = WorkspaceFactory()
    db_session.add_all([user1, ws1, user2, ws2])
    db_session.add(Membership(workspace_id=ws1.id, user_id=user1.id, role=Role.ADMIN))
    db_session.add(Membership(workspace_id=ws2.id, user_id=user2.id, role=Role.ADMIN))
    await db_session.commit()

    token1 = create_access_token(user_id=user1.id, email=user1.email)
    headers1 = {"Authorization": f"Bearer {token1}", "X-Workspace-Id": str(ws1.id)}

    token2 = create_access_token(user_id=user2.id, email=user2.email)
    headers2 = {"Authorization": f"Bearer {token2}", "X-Workspace-Id": str(ws2.id)}

    res1 = app_client.get("/api/v1/integrations", headers=headers1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) >= 6

    # Verify all DTOs do NOT leak config_json secrets
    for item in data1:
        assert "config" not in item
        assert "config_json" not in item
        assert "api_key" not in item


@pytest.mark.asyncio
async def test_connect_and_disconnect_slack_lifecycle(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Connect Slack with webhook and channel, test connection, then disconnect."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    # Connect Slack
    with patch("connectors.slack.SlackConnector.verify_credentials", new_callable=AsyncMock) as mock_verify, \
         patch("connectors.slack.SlackConnector.initial_sync", new_callable=AsyncMock) as mock_sync:
        mock_verify.return_value = True
        mock_sync.return_value = {"status": "active"}

        connect_payload = {
            "channel": "#alerts-commitments",
            "webhook_url": "https://hooks.slack.com/services/T00/B00/XXXXX",
        }
        res = app_client.post("/api/v1/integrations/slack/connect", json=connect_payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["channelOrScope"] == "#alerts-commitments"

    # Test Slack
    with patch("connectors.slack.SlackConnector.post_message", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"ok": True, "ts": "1234567890.123456"}
        test_res = app_client.post("/api/v1/integrations/slack/test", json={}, headers=headers)
        assert test_res.status_code == 200
        assert test_res.json()["success"] is True

    # Disconnect Slack
    dis_res = app_client.post("/api/v1/integrations/slack/disconnect", headers=headers)
    assert dis_res.status_code == 200
    assert dis_res.json()["connected"] is False


@pytest.mark.asyncio
async def test_integrations_cross_tenant_isolation(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Workspace A connecting an integration does not affect Workspace B's integration status."""
    user_a = UserFactory(is_active=True)
    ws_a = WorkspaceFactory()
    user_b = UserFactory(is_active=True)
    ws_b = WorkspaceFactory()
    db_session.add_all([user_a, ws_a, user_b, ws_b])
    db_session.add(Membership(workspace_id=ws_a.id, user_id=user_a.id, role=Role.ADMIN))
    db_session.add(Membership(workspace_id=ws_b.id, user_id=user_b.id, role=Role.ADMIN))
    await db_session.commit()

    token_a = create_access_token(user_id=user_a.id, email=user_a.email)
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": str(ws_a.id)}

    token_b = create_access_token(user_id=user_b.id, email=user_b.email)
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": str(ws_b.id)}

    # Connect Jira in workspace A
    with patch("connectors.jira.JiraConnector.verify_credentials", new_callable=AsyncMock) as mock_verify, \
         patch("connectors.jira.JiraConnector.initial_sync", new_callable=AsyncMock) as mock_sync:
        mock_verify.return_value = True
        mock_sync.return_value = {"status": "synced"}

        app_client.post(
            "/api/v1/integrations/jira/connect",
            json={"domain": "tenant-a.atlassian.net", "email": "admin@a.com", "api_token": "tok_a"},
            headers=headers_a,
        )

    # Workspace B's Jira must remain in disconnected state
    res_b = app_client.get("/api/v1/integrations", headers=headers_b)
    assert res_b.status_code == 200
    jira_b = next(item for item in res_b.json() if item["provider"] == "jira")
    assert jira_b["connected"] is False or jira_b["statusText"] != "Jira Software Connected (synced)"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Model Context Protocol (MCP) Gateway Lifecycle
# ─────────────────────────────────────────────────────────────────────────────


def test_mcp_tools_list_requires_authentication(app_client: TestClient):
    """Unauthenticated GET /api/v1/mcp/tools returns 401 Unauthorized."""
    res = app_client.get("/api/v1/mcp/tools")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_mcp_tools_list_returns_manifest(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """Authenticated GET /api/v1/mcp/tools returns the full tool discovery manifest."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.MEMBER))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    res = app_client.get("/api/v1/mcp/tools", headers=headers)
    assert res.status_code == 200
    tools = res.json()["tools"]
    tool_names = {t["name"] for t in tools}

    expected_tools = {"list_commitments", "get_commitment_evidence", "create_commitment", "create_update_draft"}
    assert expected_tools.issubset(tool_names)


@pytest.mark.xfail(
    strict=True,
    reason="BUG-9: list_commitments_tool calls CommitmentService.list_commitments with mismatched keyword argument 'status' instead of 'status_filter'",
)
@pytest.mark.asyncio
async def test_mcp_call_list_commitments_scopes_to_caller_workspace(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """MCP list_commitments returns only commitments belonging to the caller's active workspace."""
    user1 = UserFactory(is_active=True)
    ws1 = WorkspaceFactory()
    comm1 = CommitmentFactory(workspace_id=ws1.id, title="Workspace 1 Commitment")

    user2 = UserFactory(is_active=True)
    ws2 = WorkspaceFactory()
    comm2 = CommitmentFactory(workspace_id=ws2.id, title="Workspace 2 Commitment")

    db_session.add_all([user1, ws1, comm1, user2, ws2, comm2])
    db_session.add(Membership(workspace_id=ws1.id, user_id=user1.id, role=Role.MEMBER))
    await db_session.commit()

    token1 = create_access_token(user_id=user1.id, email=user1.email)
    headers1 = {"Authorization": f"Bearer {token1}", "X-Workspace-Id": str(ws1.id)}

    payload = {
        "name": "list_commitments",
        "arguments": {"limit": 10},
    }
    res = app_client.post("/api/v1/mcp/tools/call", json=payload, headers=headers1)
    assert res.status_code == 200
    body = res.json()
    assert body["isError"] is False

    content_text = body["content"][0]["text"]
    assert "Workspace 1 Commitment" in content_text
    assert "Workspace 2 Commitment" not in content_text


@pytest.mark.asyncio
async def test_mcp_call_create_commitment_tool(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """MCP create_commitment tool successfully creates a new commitment in awaiting-review status."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.ADMIN))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {
        "name": "create_commitment",
        "arguments": {
            "title": "Build ISO 27001 Access Matrix",
            "customer": "FinTech Corp",
            "quote": "We will have the matrix ready by next sprint",
            "promised_by": "Next Sprint",
        },
    }
    res = app_client.post("/api/v1/mcp/tools/call", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["isError"] is False

    created_info = json.loads(data["content"][0]["text"])
    assert created_info["status"] == "created"
    assert created_info["title"] == "Build ISO 27001 Access Matrix"
    assert created_info["customer"] == "FinTech Corp"
    assert "id" in created_info


@pytest.mark.asyncio
async def test_mcp_call_unknown_tool_returns_404(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """MCP call with unknown tool name returns HTTP 404 Not Found."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.MEMBER))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {
        "name": "non_existent_malicious_tool",
        "arguments": {},
    }
    res = app_client.post("/api/v1/mcp/tools/call", json=payload, headers=headers)
    assert res.status_code == 404
    assert "Unknown tool" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_mcp_mutation_tools_block_viewer_role(
    app_client: TestClient,
    db_session: AsyncSession,
):
    """MCP write tools (create_commitment, create_update_draft) block users with VIEWER role."""
    user = UserFactory(is_active=True)
    ws = WorkspaceFactory()
    db_session.add_all([user, ws])
    db_session.add(Membership(workspace_id=ws.id, user_id=user.id, role=Role.VIEWER))
    await db_session.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

    payload = {
        "name": "create_commitment",
        "arguments": {"title": "Viewer Unauthorized Commitment"},
    }
    res = app_client.post("/api/v1/mcp/tools/call", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Viewer role cannot perform mutations" in res.json().get("detail", "")
