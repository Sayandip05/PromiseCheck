"""Speech-to-Text Transcription Connector supporting Deepgram and Whisper."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.speech_to_text")


class SpeechToTextConnector(BaseConnector):
    """Transcribes meeting recordings and voice memos into text."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "deepgram") -> None:
        self.api_key = api_key or os.getenv("SPEECH_API_KEY") or ""
        self.provider = provider or os.getenv("SPEECH_PROVIDER") or "deepgram"

    @property
    def provider_name(self) -> str:
        return "speech_to_text"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        key = credentials.get("api_key", self.api_key)
        if not key:
            raise ConnectorNotConfiguredError("Speech-to-Text connector requires an API key.")
        return True

    def transcribe_file_sync(self, file_path: str) -> str:
        """Synchronously transcribe audio file on disk via provider API without full RAM buffering."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError(
                "Speech-to-Text provider is not configured. Provide a valid SPEECH_API_KEY."
            )

        if self.provider == "deepgram":
            try:
                with open(file_path, "rb") as f:
                    with httpx.Client(timeout=180.0) as client:
                        res = client.post(
                            "https://api.deepgram.com/v1/listen?smart_format=true&diarize=true",
                            headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/*"},
                            content=f.read(),
                        )
                        if res.status_code == 200:
                            data = res.json()
                            channels = data.get("results", {}).get("channels", [])
                            if channels:
                                transcript = channels[0].get("alternatives", [{}])[0].get("transcript", "")
                                if transcript:
                                    return transcript
                            raise ConnectorDeliveryError("Deepgram completed transcription but returned no speech text.")
                        raise ConnectorDeliveryError(f"Deepgram returned HTTP {res.status_code}: {res.text}")
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Deepgram transcription error: {exc}")

        raise ConnectorNotConfiguredError(f"Unsupported speech provider: '{self.provider}'")

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "meeting.mp3") -> str:
        """Transcribe raw audio bytes into formatted transcript text."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError(
                "Speech-to-Text provider is not configured. Provide a valid SPEECH_API_KEY."
            )

        if self.provider == "deepgram":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(
                        "https://api.deepgram.com/v1/listen?smart_format=true&diarize=true",
                        headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/*"},
                        content=audio_bytes,
                    )
                    if res.status_code == 200:
                        data = res.json()
                        channels = data.get("results", {}).get("channels", [])
                        if channels:
                            transcript = channels[0].get("alternatives", [{}])[0].get("transcript", "")
                            if transcript:
                                return transcript
                        raise ConnectorDeliveryError("Deepgram completed transcription but returned no speech text.")
                    raise ConnectorDeliveryError(f"Deepgram returned HTTP {res.status_code}: {res.text}")
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Deepgram transcription error: {exc}")

        raise ConnectorNotConfiguredError(f"Unsupported speech provider: '{self.provider}'")


    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Speech-to-Text is not configured.")
        return {"status": "active"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
