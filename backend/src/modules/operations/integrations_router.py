"""Integrations router for third-party tools (Google Meet, Jira, Slack, Linear, Gmail)."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user_optional
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/integrations", tags=["Integrations & Connectors"])


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


# Stateful integration catalog for the workspace
WORKSPACE_INTEGRATIONS: dict[str, list[IntegrationDTO]] = {}


def _get_workspace_integrations_list(ws_id_str: str) -> list[IntegrationDTO]:
    if ws_id_str not in WORKSPACE_INTEGRATIONS:
        WORKSPACE_INTEGRATIONS[ws_id_str] = [
            IntegrationDTO(
                id="int-gmeet",
                provider="google_meet",
                name="Google Meet",
                connected=True,
                statusText="Google Meet connected",
                lastSync="Continuous auto-scan",
                workspaceId=ws_id_str,
                description="Auto-ingests meeting recordings and transcripts with consent validation.",
            ),
            IntegrationDTO(
                id="int-jira",
                provider="jira",
                name="Jira Software",
                connected=True,
                statusText="Jira synced 2 min ago",
                lastSync="2 min ago",
                channelOrScope="Project ENG / Cloud site acme-corp",
                workspaceId=ws_id_str,
                description="Tracks delivery dates, ticket blockers, and status field mappings.",
            ),
            IntegrationDTO(
                id="int-slack",
                provider="slack",
                name="Slack",
                connected=True,
                statusText="Connected to #customer-commitments",
                lastSync="Real-time alerts active",
                channelOrScope="#customer-commitments",
                workspaceId=ws_id_str,
                description="Sends automated risk alerts and reminder notifications to designated team channels.",
            ),
            IntegrationDTO(
                id="int-linear",
                provider="linear",
                name="Linear",
                connected=False,
                statusText="Not connected",
                lastSync="Never",
                workspaceId=ws_id_str,
                description="Alternative issue tracker integration for engineering cycle and blocker tracking.",
            ),
            IntegrationDTO(
                id="int-gmail",
                provider="gmail",
                name="Gmail & Google Calendar",
                connected=False,
                statusText="Not connected",
                lastSync="Never",
                workspaceId=ws_id_str,
                description="Monitors commitment confirmations and scheduled customer milestone meetings.",
            ),
            IntegrationDTO(
                id="int-recall",
                provider="recall",
                name="Recall.ai Meeting Bot",
                connected=False,
                statusText="Not connected",
                lastSync="Never",
                workspaceId=ws_id_str,
                description="Autonomous meeting recording bot for Zoom, Teams, and Google Meet.",
            ),
        ]
    return WORKSPACE_INTEGRATIONS[ws_id_str]


@router.get("", response_model=list[IntegrationDTO])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List all third-party connectors and their synchronization status."""
    ws_id = await get_active_workspace_id(db, user)
    return _get_workspace_integrations_list(str(ws_id))


from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from connectors.slack import SlackConnector
from connectors.recall import RecallConnector
from connectors.google_meet import GoogleMeetConnector
from connectors.gmail import GmailConnector
from connectors.external_mcp import ExternalMCPConnector

CONNECTOR_FACTORIES = {
    "jira": JiraConnector,
    "linear": LinearConnector,
    "slack": SlackConnector,
    "recall": RecallConnector,
    "google_meet": GoogleMeetConnector,
    "gmail": GmailConnector,
    "external_mcp": ExternalMCPConnector,
}


@router.post("/{provider}/connect", response_model=IntegrationDTO)
async def connect_integration(
    provider: str,
    payload: ConnectIntegrationRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Connect or update configuration for a third-party tool."""
    ws_id = await get_active_workspace_id(db, user)
    integrations = _get_workspace_integrations_list(str(ws_id))

    # Invoke connector verify and sync
    connector_cls = CONNECTOR_FACTORIES.get(provider)
    sync_details = "Connected and active"
    if connector_cls:
        connector = connector_cls()
        await connector.verify_credentials(payload.model_dump())
        sync_result = await connector.initial_sync(str(ws_id), payload.scope or "")
        sync_details = f"Connected ({sync_result.get('status', 'active')})"

    for item in integrations:
        if item.provider == provider:
            item.connected = True
            item.statusText = f"{item.name} {sync_details}"
            item.lastSync = "Just now"
            if payload.scope or payload.webhook_url:
                item.channelOrScope = payload.scope or payload.webhook_url
            return item

    raise HTTPException(status_code=404, detail=f"Integration provider '{provider}' not found")


@router.post("/{provider}/disconnect", response_model=IntegrationDTO)
async def disconnect_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Disconnect a third-party tool."""
    ws_id = await get_active_workspace_id(db, user)
    integrations = _get_workspace_integrations_list(str(ws_id))

    for item in integrations:
        if item.provider == provider:
            item.connected = False
            item.statusText = "Not connected"
            item.lastSync = "Disconnected"
            return item

    raise HTTPException(status_code=404, detail=f"Integration provider '{provider}' not found")
