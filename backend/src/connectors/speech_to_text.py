"""Speech-to-text audio transcription connector."""

from typing import Any

from connectors.base import BaseConnector


class SpeechToTextConnector(BaseConnector):
    """Submits uploaded audio files to hosted STT providers (e.g. Deepgram)."""

    @property
    def provider_name(self) -> str:
        return "speech_to_text"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
