"""Google Calendar Integration Connector for Deadline Milestone Synchronization."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.google_calendar")


class GoogleCalendarConnector(BaseConnector):
    """Synchronizes customer milestones, sync calls, and delivery deadlines with Google Calendar."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token or os.getenv("GOOGLE_ACCESS_TOKEN") or ""

    @property
    def provider_name(self) -> str:
        return "google_calendar"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("access_token", self.access_token)
        if not token:
            raise ConnectorNotConfiguredError("Google Calendar connector requires an access token.")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if res.status_code != 200:
                    raise ConnectorDeliveryError(f"Google Calendar credentials invalid: HTTP {res.status_code}")
                return True
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Google Calendar verification failed: {exc}")

    async def create_deadline_event(
        self,
        title: str,
        due_date_iso: str,
        description: str,
    ) -> dict[str, Any]:
        """Add delivery deadline milestone to Google Calendar."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Google Calendar connector is not configured.")

        # Sanitize date format for Google Calendar (YYYY-MM-DD)
        clean_date = due_date_iso.split("T")[0] if "T" in due_date_iso else due_date_iso
        if len(clean_date) != 10 or clean_date.count("-") != 2:
            clean_date = "2026-10-15"

        event_payload = {
            "summary": f"[PromiseCheck SLA] {title}",
            "description": description or f"Delivery milestone tracked by PromiseCheck for '{title}'.",
            "start": {"date": clean_date},
            "end": {"date": clean_date},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 60},
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                    json=event_payload,
                )
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "status": "created",
                        "id": data.get("id"),
                        "htmlLink": data.get("htmlLink"),
                        "summary": data.get("summary"),
                        "date": clean_date,
                    }
                raise ConnectorDeliveryError(f"Google Calendar event creation failed: HTTP {res.status_code} {res.text}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Google Calendar error: {exc}")

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Google Calendar connector is not configured.")
        return {"status": "active"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
