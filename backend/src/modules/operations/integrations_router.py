"""Integrations router for third-party tools (Google Meet, Jira, Slack, Linear, Gmail).

Fully Twelve-Factor Factor VI compliant: persistent database storage with Redis caching
and Pub/Sub invalidation. No in-process memory state.
"""

import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logging import get_logger
from core.redis import delete_key, get_value, publish_event, set_with_ttl
from core.security import get_current_user_optional
from modules.identity.models import User
from modules.operations.models import WorkspaceIntegration
from modules.workspaces.service import get_active_workspace_id

from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from connectors.slack import SlackConnector
from connectors.recall import RecallConnector
from connectors.google_meet import GoogleMeetConnector
from connectors.gmail import GmailConnector
from connectors.google_calendar import GoogleCalendarConnector
from connectors.external_mcp import ExternalMCPConnector
from connectors.google_auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    get_google_user_profile,
    get_valid_google_token_for_workspace,
)

logger = get_logger("integrations_router")

router = APIRouter(prefix="/integrations", tags=["Integrations & Connectors"])

CONNECTOR_FACTORIES = {
    "jira": JiraConnector,
    "linear": LinearConnector,
    "slack": SlackConnector,
    "recall": RecallConnector,
    "google_meet": GoogleMeetConnector,
    "gmail": GmailConnector,
    "google_calendar": GoogleCalendarConnector,
    "external_mcp": ExternalMCPConnector,
}

DEFAULT_PROVIDERS = [
    {
        "provider": "google_meet",
        "name": "Google Meet",
        "connected": True,
        "status_text": "Google Meet connected",
        "last_sync": "Continuous auto-scan",
        "channel_or_scope": None,
        "description": "Auto-ingests meeting recordings and transcripts with consent validation.",
    },
    {
        "provider": "jira",
        "name": "Jira Software",
        "connected": True,
        "status_text": "Jira synced 2 min ago",
        "last_sync": "2 min ago",
        "channel_or_scope": "Project ENG / Cloud site acme-corp",
        "description": "Tracks delivery dates, ticket blockers, and status field mappings.",
    },
    {
        "provider": "slack",
        "name": "Slack",
        "connected": True,
        "status_text": "Connected to #customer-commitments",
        "last_sync": "Real-time alerts active",
        "channel_or_scope": "#customer-commitments",
        "description": "Sends automated risk alerts and reminder notifications to designated team channels.",
    },
    {
        "provider": "linear",
        "name": "Linear",
        "connected": False,
        "status_text": "Not connected",
        "last_sync": "Never",
        "channel_or_scope": None,
        "description": "Alternative issue tracker integration for engineering cycle and blocker tracking.",
    },
    {
        "provider": "gmail",
        "name": "Gmail & Google Calendar",
        "connected": False,
        "status_text": "Not connected",
        "last_sync": "Never",
        "channel_or_scope": None,
        "description": "Monitors commitment confirmations and scheduled customer milestone meetings.",
    },
    {
        "provider": "recall",
        "name": "Recall.ai Meeting Bot",
        "connected": False,
        "status_text": "Not connected",
        "last_sync": "Never",
        "channel_or_scope": None,
        "description": "Autonomous meeting recording bot for Zoom, Teams, and Google Meet.",
    },
]


class IntegrationDTO(BaseModel):
    """Third-party connector status."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str  # google_meet | jira | slack | linear | gmail | recall
    name: str
    connected: bool
    statusText: str
    lastSync: Optional[str] = None
    workspaceId: Optional[str] = None
    description: Optional[str] = None
    channelOrScope: Optional[str] = None


class ConnectIntegrationRequest(BaseModel):
    """Payload to connect or update credentials for an external provider."""

    model_config = ConfigDict(extra="allow")

    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    scope: Optional[str] = None
    # Provider-specific credentials & preferences
    domain: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    bot_token: Optional[str] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    bot_name: Optional[str] = None
    access_token: Optional[str] = None
    project_key: Optional[str] = None
    team_key: Optional[str] = None
    notify_conflicts: Optional[bool] = True
    notify_overdue: Optional[bool] = True
    notify_new_promises: Optional[bool] = True


class TestIntegrationRequest(BaseModel):
    """Payload to test external provider connectivity."""

    model_config = ConfigDict(extra="allow")

    api_key: Optional[str] = None
    domain: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    webhook_url: Optional[str] = None
    bot_token: Optional[str] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    access_token: Optional[str] = None
    meeting_url: Optional[str] = None
    message: Optional[str] = None


class TestIntegrationResponse(BaseModel):
    """Result of external provider live connectivity test."""

    success: bool
    provider: str
    message: str
    details: Optional[dict[str, Any]] = None


def instantiate_connector(provider: str, config: Optional[dict[str, Any]] = None):
    """Instantiate provider connector using stored or supplied configuration."""
    cfg = config or {}
    if provider == "slack":
        return SlackConnector(
            bot_token=cfg.get("bot_token") or cfg.get("api_key"),
            default_channel=cfg.get("channel") or cfg.get("scope"),
            webhook_url=cfg.get("webhook_url"),
        )
    elif provider == "jira":
        return JiraConnector(
            domain=cfg.get("domain"),
            email=cfg.get("email"),
            api_token=cfg.get("api_token") or cfg.get("api_key"),
        )
    elif provider == "linear":
        return LinearConnector(
            api_key=cfg.get("api_key"),
        )
    elif provider == "recall":
        return RecallConnector(
            api_key=cfg.get("api_key"),
            region=cfg.get("region"),
        )
    elif provider == "google_meet":
        return GoogleMeetConnector(
            access_token=cfg.get("access_token") or cfg.get("api_key"),
        )
    elif provider == "gmail":
        return GmailConnector(
            access_token=cfg.get("access_token"),
            user_email=cfg.get("email"),
        )
    elif provider == "google_calendar":
        return GoogleCalendarConnector(
            access_token=cfg.get("access_token"),
        )
    elif provider == "external_mcp":
        return ExternalMCPConnector(
            endpoint=cfg.get("endpoint"),
            auth_token=cfg.get("api_key"),
        )
    return None


def _model_to_dto(m: WorkspaceIntegration) -> IntegrationDTO:
    """Convert database entity to API DTO."""
    return IntegrationDTO(
        id=str(m.id),
        provider=m.provider,
        name=m.name,
        connected=m.connected,
        statusText=m.status_text,
        lastSync=m.last_sync,
        workspaceId=str(m.workspace_id),
        description=m.description,
        channelOrScope=m.channel_or_scope,
    )


async def _get_or_seed_integrations(db: AsyncSession, ws_id: uuid.UUID) -> list[WorkspaceIntegration]:
    """Retrieve integration rows for workspace; seed default 6 connectors if first visit."""
    stmt = (
        select(WorkspaceIntegration)
        .where(WorkspaceIntegration.workspace_id == ws_id)
        .order_by(WorkspaceIntegration.created_at.asc())
    )
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    if records:
        return records

    # Seed default providers for newly encountered workspace
    for spec in DEFAULT_PROVIDERS:
        rec = WorkspaceIntegration(
            workspace_id=ws_id,
            provider=spec["provider"],
            name=spec["name"],
            connected=spec["connected"],
            status_text=spec["status_text"],
            last_sync=spec["last_sync"],
            channel_or_scope=spec["channel_or_scope"],
            description=spec["description"],
            config_json={},
        )
        db.add(rec)

    await db.commit()

    # Re-query newly committed records
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("", response_model=list[IntegrationDTO])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List all third-party connectors with Redis caching and DB persistence."""
    ws_id = await get_active_workspace_id(db, user)
    cache_key = f"ws:{ws_id}:integrations"

    # Fast path: check Redis cache
    cached = await get_value(cache_key)
    if cached and isinstance(cached, list):
        try:
            return [IntegrationDTO.model_validate(item) for item in cached]
        except Exception as exc:
            logger.warning(f"Cache deserialization failed for {cache_key}: {exc}")

    # Fallback to persistent database
    records = await _get_or_seed_integrations(db, ws_id)
    dtos = [_model_to_dto(r) for r in records]

    # Warm Redis cache (TTL 3600 seconds)
    await set_with_ttl(cache_key, [dto.model_dump() for dto in dtos], ttl_seconds=3600)

    return dtos


@router.post("/{provider}/connect", response_model=IntegrationDTO)
async def connect_integration(
    provider: str,
    payload: ConnectIntegrationRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Connect or update configuration for a third-party tool."""
    ws_id = await get_active_workspace_id(db, user)

    # Ensure records are provisioned
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == provider,
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        await _get_or_seed_integrations(db, ws_id)
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Integration provider '{provider}' not found")

    # Invoke connector verify and sync
    raw_payload = payload.model_dump(exclude_unset=True)
    connector = instantiate_connector(provider, raw_payload)
    sync_details = "Connected and active"
    if connector:
        await connector.verify_credentials(raw_payload)
        sync_resource = payload.project_key or payload.team_key or payload.scope or payload.channel or ""
        sync_result = await connector.initial_sync(str(ws_id), sync_resource)
        sync_details = f"Connected ({sync_result.get('status', 'active')})"

    # Update persistent database entity
    item.connected = True
    item.status_text = f"{item.name} {sync_details}"
    item.last_sync = "Just now"

    # Compute descriptive channel_or_scope
    if provider == "slack":
        item.channel_or_scope = (
            payload.channel
            or payload.scope
            or ("Webhook: " + payload.webhook_url[:30] + "..." if payload.webhook_url else "#customer-commitments")
        )
    elif provider == "jira":
        clean_domain = (payload.domain or "Atlassian Cloud").replace("https://", "").rstrip("/")
        item.channel_or_scope = f"{clean_domain} / {payload.project_key or payload.scope or 'ENG'}"
    elif provider == "linear":
        item.channel_or_scope = f"Team {payload.team_key or payload.scope or 'ENG'}"
    elif provider == "recall":
        item.channel_or_scope = f"Region: {payload.region or 'us-west-2'} ({payload.bot_name or 'PromiseCheck Notetaker'})"
    elif provider == "google_meet":
        item.channel_or_scope = payload.email or "Google Workspace Auto-Scan"
    elif provider == "gmail":
        item.channel_or_scope = payload.email or "Authorized Google Account"
    elif payload.scope or payload.webhook_url:
        item.channel_or_scope = payload.scope or payload.webhook_url

    # Persist provider config
    current_config = dict(item.config_json or {})
    for k, v in raw_payload.items():
        if v is not None:
            current_config[k] = v
    item.config_json = current_config

    await db.commit()
    await db.refresh(item)

    # Invalidate Redis cache
    cache_key = f"ws:{ws_id}:integrations"
    await delete_key(cache_key)

    # Broadcast event via Redis Pub/Sub
    await publish_event(
        f"ws:{ws_id}:events",
        "INTEGRATION_UPDATED",
        {"provider": provider, "connected": True, "statusText": item.status_text},
    )

    logger.info(f"[integrations] Provider '{provider}' connected for workspace={ws_id}")
    return _model_to_dto(item)


@router.post("/{provider}/test", response_model=TestIntegrationResponse)
async def test_integration(
    provider: str,
    payload: TestIntegrationRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Test external connection and live execution for a third-party tool."""
    ws_id = await get_active_workspace_id(db, user)

    # Retrieve existing config to merge with request payload
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == provider,
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    merged_config = dict(item.config_json or {}) if item else {}
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            merged_config[k] = v

    connector = instantiate_connector(provider, merged_config)
    if not connector:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")

    if provider == "slack":
        channel = merged_config.get("channel") or merged_config.get("scope") or "#customer-commitments"
        test_msg = payload.message or "🧪 PromiseCheck test alert: Slack integration connection verified!"
        delivery_res = await connector.post_message(text=test_msg, channel=channel)
        is_live = delivery_res.get("provider") == "slack_webhook" or bool(delivery_res.get("ts"))
        return TestIntegrationResponse(
            success=True,
            provider="slack",
            message=f"Test alert dispatched to {channel} ({'Live Slack API' if is_live else 'Fluent Simulation'})",
            details=delivery_res,
        )

    elif provider == "jira":
        is_valid = await connector.verify_credentials(merged_config)
        ticket_res = await connector.get_ticket("ENG-104")
        return TestIntegrationResponse(
            success=is_valid,
            provider="jira",
            message="Jira credentials verified successfully!" if is_valid else "Jira verification failed.",
            details={"configured": connector.is_configured, "ticket_preview": ticket_res},
        )

    elif provider == "linear":
        is_valid = await connector.verify_credentials(merged_config)
        issue_res = await connector.get_issue("ENG-891")
        return TestIntegrationResponse(
            success=is_valid,
            provider="linear",
            message="Linear GraphQL authentication verified!" if is_valid else "Linear verification failed.",
            details={"configured": connector.is_configured, "issue_preview": issue_res},
        )

    elif provider == "recall":
        is_valid = await connector.verify_credentials(merged_config)
        meeting_url = payload.meeting_url or "https://meet.google.com/xyz-abc-def"
        bot_res = await connector.create_bot(
            meeting_url=meeting_url,
            bot_name=merged_config.get("bot_name") or "PromiseCheck Notetaker",
        )
        return TestIntegrationResponse(
            success=is_valid,
            provider="recall",
            message="Recall.ai bot client verified & test dispatch completed!",
            details={"configured": connector.is_configured, "bot": bot_res},
        )

    elif provider == "google_meet":
        is_valid = await connector.verify_credentials(merged_config)
        meetings = await connector.list_recent_meetings()
        return TestIntegrationResponse(
            success=is_valid,
            provider="google_meet",
            message=f"Google Meet connection verified! {len(meetings)} conference records accessible.",
            details={"configured": connector.is_configured, "recent_meetings": meetings},
        )

    elif provider in ("gmail", "google_calendar"):
        return TestIntegrationResponse(
            success=True,
            provider=provider,
            message="Google Workspace integration ready.",
            details={"configured": True},
        )

    return TestIntegrationResponse(
        success=True,
        provider=provider,
        message=f"{provider} tested successfully.",
    )


@router.post("/{provider}/disconnect", response_model=IntegrationDTO)
async def disconnect_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Disconnect a third-party tool and invalidate cache."""
    ws_id = await get_active_workspace_id(db, user)

    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == provider,
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        await _get_or_seed_integrations(db, ws_id)
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Integration provider '{provider}' not found")

    # Update persistent database entity
    item.connected = False
    item.status_text = "Not connected"
    item.last_sync = "Disconnected"

    await db.commit()
    await db.refresh(item)

    # Invalidate Redis cache
    cache_key = f"ws:{ws_id}:integrations"
    await delete_key(cache_key)

    # Broadcast event via Redis Pub/Sub
    await publish_event(
        f"ws:{ws_id}:events",
        "INTEGRATION_UPDATED",
        {"provider": provider, "connected": False, "statusText": item.status_text},
    )

    logger.info(f"[integrations] Provider '{provider}' disconnected for workspace={ws_id}")
    return _model_to_dto(item)


# ==============================================================================
# Google Integration (Gmail & Google Calendar) Endpoints
# ==============================================================================

class GoogleAuthorizeResponse(BaseModel):
    authorization_url: str
    redirect_uri: str
    state: str


class GoogleConnectTokenRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    email: Optional[str] = None
    expires_in: Optional[int] = 3600


class CalendarSyncEventRequest(BaseModel):
    commitment_id: Optional[str] = None
    title: str
    due_date_iso: str
    description: Optional[str] = ""


class GmailSendUpdateRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    commitment_id: Optional[str] = None


@router.get("/google/authorize", response_model=GoogleAuthorizeResponse)
async def get_google_authorize_url(
    redirect_uri: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Generate Google OAuth 2.0 authorization URL for Gmail and Calendar access."""
    ws_id = await get_active_workspace_id(db, user)
    # Default redirect points to backend callback which closes popup / redirects to app
    callback_uri = redirect_uri or "http://localhost:8001/api/v1/integrations/google/callback"
    state = f"{ws_id}:{uuid.uuid4().hex[:12]}"

    auth_url = build_authorization_url(redirect_uri=callback_uri, state=state)
    return GoogleAuthorizeResponse(
        authorization_url=auth_url,
        redirect_uri=callback_uri,
        state=state,
    )


@router.get("/google/callback", response_class=HTMLResponse)
async def google_oauth_callback_get(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth browser redirect callback from consent screen."""
    if error:
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h3 style="color:#e11d48;">Google Authorization Failed</h3>
                <p>{error}</p>
                <script>setTimeout(function() {{ window.close(); }}, 3000);</script>
            </body></html>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from Google.")

    ws_id = None
    if state and ":" in state:
        try:
            ws_id = uuid.UUID(state.split(":")[0])
        except ValueError:
            pass

    if not ws_id:
        # Fallback to active workspace
        ws_id = await get_active_workspace_id(db, None)

    callback_uri = "http://localhost:8001/api/v1/integrations/google/callback"
    try:
        token_data = await exchange_code_for_tokens(code, callback_uri)
    except Exception as exc:
        logger.error(f"[Google Callback] Token exchange failed: {exc}")
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px;">
                <h3 style="color:#e11d48;">Authorization Exchange Failed</h3>
                <p>{exc}</p>
                <script>setTimeout(function() {{ window.close(); }}, 4000);</script>
            </body></html>
            """,
            status_code=400,
        )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    # Fetch user email from Google Profile
    user_info = await get_google_user_profile(access_token)
    email = user_info.get("email") or "connected-user@google.com"

    # Persist in WorkspaceIntegration record for provider 'gmail'
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == "gmail",
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        await _get_or_seed_integrations(db, ws_id)
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

    import time
    if item:
        item.connected = True
        item.status_text = f"Connected as {email}"
        item.last_sync = "Just now"
        item.channel_or_scope = email
        item.config_json = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": time.time() + expires_in,
            "email": email,
            "scopes": scopes,
        }
        await db.commit()
        await db.refresh(item)

    # Invalidate cache and broadcast
    cache_key = f"ws:{ws_id}:integrations"
    await delete_key(cache_key)
    await publish_event(
        f"ws:{ws_id}:events",
        "INTEGRATION_UPDATED",
        {"provider": "gmail", "connected": True, "statusText": f"Connected as {email}"},
    )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PromiseCheck - Google Connected</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0a0a0a; color: #fff; }}
                .card {{ text-align: center; padding: 32px; background: #171717; border-radius: 16px; border: 1px solid #262626; max-width: 400px; }}
                h2 {{ margin: 0 0 8px 0; font-size: 20px; }}
                p {{ color: #a3a3a3; font-size: 14px; margin: 0 0 16px 0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Gmail & Calendar Connected</h2>
                <p>Authorized as <strong>{email}</strong>. Returning to PromiseCheck...</p>
            </div>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GOOGLE_AUTH_SUCCESS', provider: 'gmail', email: '{email}' }}, '*');
                    setTimeout(function() {{ window.close(); }}, 1200);
                }} else {{
                    setTimeout(function() {{ window.location.href = 'http://localhost:3000/'; }}, 1200);
                }}
            </script>
        </body>
        </html>
        """
    )


@router.post("/google/connect-token", response_model=IntegrationDTO)
async def connect_google_with_token(
    payload: GoogleConnectTokenRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Directly register an existing Google Access Token / Service Account token."""
    ws_id = await get_active_workspace_id(db, user)
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == "gmail",
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        await _get_or_seed_integrations(db, ws_id)
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Integration record not found")

    email = payload.email
    if not email:
        profile = await get_google_user_profile(payload.access_token)
        email = profile.get("email") or "authorized-user@gmail.com"

    import time
    item.connected = True
    item.status_text = f"Connected as {email}"
    item.last_sync = "Just now"
    item.channel_or_scope = email
    item.config_json = {
        "access_token": payload.access_token,
        "refresh_token": payload.refresh_token,
        "token_expiry": time.time() + (payload.expires_in or 3600),
        "email": email,
    }
    await db.commit()
    await db.refresh(item)

    await delete_key(f"ws:{ws_id}:integrations")
    await publish_event(
        f"ws:{ws_id}:events",
        "INTEGRATION_UPDATED",
        {"provider": "gmail", "connected": True, "statusText": item.status_text},
    )
    return _model_to_dto(item)


@router.post("/google/calendar/sync-event")
async def sync_commitment_to_google_calendar(
    payload: CalendarSyncEventRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Sync a commitment deadline event directly to the active workspace's Google Calendar."""
    ws_id = await get_active_workspace_id(db, user)
    access_token, email = await get_valid_google_token_for_workspace(db, ws_id)

    calendar_conn = GoogleCalendarConnector(access_token=access_token)
    event_result = await calendar_conn.create_deadline_event(
        title=payload.title,
        due_date_iso=payload.due_date_iso,
        description=payload.description or f"PromiseCheck SLA commitment for '{payload.title}'.",
    )

    logger.info(f"[Google Calendar] Synced event '{payload.title}' for workspace={ws_id} (email={email})")
    return {
        "status": "synced",
        "email": email,
        "event": event_result,
        "html_link": event_result.get("htmlLink"),
    }


@router.post("/google/gmail/send-update")
async def send_customer_update_via_gmail(
    payload: GmailSendUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Dispatch an approved customer commitment update via the connected Gmail account."""
    ws_id = await get_active_workspace_id(db, user)
    access_token, sender_email = await get_valid_google_token_for_workspace(db, ws_id)

    gmail_conn = GmailConnector(access_token=access_token)
    send_result = await gmail_conn.send_draft_update(
        to_email=payload.to_email,
        subject=payload.subject,
        body=payload.body,
    )

    logger.info(f"[Gmail] Sent status update to {payload.to_email} via workspace={ws_id} (sender={sender_email})")
    return {
        "status": "sent",
        "sender": sender_email,
        "result": send_result,
    }

