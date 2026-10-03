"""Integrations router for third-party tools (Google Meet, Jira, Slack, Linear, Gmail).

Fully Twelve-Factor Factor VI compliant: persistent database storage with Redis caching
and Pub/Sub invalidation. No in-process memory state.
"""

import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
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
from connectors.external_mcp import ExternalMCPConnector

logger = get_logger("integrations_router")

router = APIRouter(prefix="/integrations", tags=["Integrations & Connectors"])

CONNECTOR_FACTORIES = {
    "jira": JiraConnector,
    "linear": LinearConnector,
    "slack": SlackConnector,
    "recall": RecallConnector,
    "google_meet": GoogleMeetConnector,
    "gmail": GmailConnector,
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

    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    scope: Optional[str] = None


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
    connector_cls = CONNECTOR_FACTORIES.get(provider)
    sync_details = "Connected and active"
    if connector_cls:
        connector = connector_cls()
        await connector.verify_credentials(payload.model_dump())
        sync_result = await connector.initial_sync(str(ws_id), payload.scope or "")
        sync_details = f"Connected ({sync_result.get('status', 'active')})"

    # Update persistent database entity
    item.connected = True
    item.status_text = f"{item.name} {sync_details}"
    item.last_sync = "Just now"
    if payload.scope or payload.webhook_url:
        item.channel_or_scope = payload.scope or payload.webhook_url

    # Persist provider config
    current_config = dict(item.config_json or {})
    for k, v in payload.model_dump(exclude_unset=True).items():
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
