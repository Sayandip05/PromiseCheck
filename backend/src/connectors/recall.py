"""Recall.ai Autonomous Meeting Recording Bot Connector."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.recall")


class RecallConnector(BaseConnector):
    """Dispatches autonomous recording and transcription bots to Google Meet, Zoom, and Teams."""

    def __init__(self, api_key: Optional[str] = None, region: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("RECALL_API_KEY") or ""
        self.region = region or os.getenv("RECALL_REGION") or "us-west-2"
        self.base_url = f"https://{self.region}.recall.ai/api/v1"

    @property
    def provider_name(self) -> str:
        return "recall"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        key = credentials.get("api_key", self.api_key)
        if not key:
            raise ConnectorNotConfiguredError("Recall.ai connector requires an API key.")

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{self.base_url}/bot/",
                    headers={"Authorization": f"Token {key}"},
                )
                if res.status_code == 200:
                    return True
                raise ConnectorDeliveryError(f"Recall.ai credentials rejected: HTTP {res.status_code}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Recall.ai verification error: {exc}")

    async def create_bot(self, meeting_url: str, bot_name: str = "PromiseCheck NoteTaker") -> dict[str, Any]:
        """Dispatch a virtual participant bot to record and transcribe a meeting."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Recall.ai is not configured. Provide an API key.")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{self.base_url}/bot/",
                    headers={"Authorization": f"Token {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "meeting_url": meeting_url,
                        "bot_name": bot_name,
                        "transcription_options": {"provider": "meeting_captions"},
                    },
                )
                if res.status_code in (200, 201):
                    return res.json()
                raise ConnectorDeliveryError(f"Recall.ai bot creation failed: HTTP {res.status_code} {res.text}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Recall.ai dispatch error: {exc}")

    async def get_transcript(self, bot_id: str) -> dict[str, Any]:
        """Fetch finished meeting transcript from Recall.ai."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Recall.ai is not configured.")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(
                    f"{self.base_url}/bot/{bot_id}/transcript/",
                    headers={"Authorization": f"Token {self.api_key}"},
                )
                if res.status_code == 200:
                    return res.json()
                raise ConnectorDeliveryError(f"Recall.ai transcript fetch failed: HTTP {res.status_code} {res.text}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Recall.ai transcript error: {exc}")

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Recall.ai is not configured.")
        return {"status": "active", "bots_active": 0}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
