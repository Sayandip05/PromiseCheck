"""Integrations domain Pydantic schemas."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


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
