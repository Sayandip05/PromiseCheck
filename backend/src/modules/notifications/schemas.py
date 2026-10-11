"""Notifications domain Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel


class NotificationAlert(BaseModel):
    """Internal Slack/Email delivery alert."""

    id: str
    commitment_id: str
    commitment_title: str
    channel: str  # slack, email
    recipient: str
    status: str  # pending_approval, sent, scheduled
    alert_message: str


class SendNotificationRequest(BaseModel):
    """Request payload to dispatch an alert."""

    commitment_id: Optional[str] = None
    channel: str = "slack"  # slack | email
    recipient: Optional[str] = None
    message: str = ""
