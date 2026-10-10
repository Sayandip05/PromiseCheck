"""Google OAuth 2.0 and Token Management Utility for Gmail & Google Calendar."""

import os
import urllib.parse
from typing import Any, Optional

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger("connectors.google_auth")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


def build_authorization_url(redirect_uri: str, state: str) -> str:
    """Generate the Google OAuth 2.0 authorization URL requesting Gmail and Calendar scopes."""
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = settings.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials (client_id / client_secret) are not configured.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if res.status_code != 200:
            error_data = res.text
            try:
                error_data = res.json()
            except Exception:
                pass
            logger.error(f"[Google OAuth] Token exchange error: {error_data}")
            raise ValueError(f"Failed to exchange Google OAuth code: {error_data}")

        return res.json()


async def get_google_user_profile(access_token: str) -> dict[str, Any]:
    """Retrieve authorized user's email address and profile."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"[Google OAuth] Failed to fetch userinfo: {res.status_code} - {res.text}")
        return {}


async def refresh_google_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired Google access token using the long-lived refresh token."""
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = settings.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if res.status_code == 200:
            return res.json()
        logger.error(f"[Google OAuth] Refresh token exchange failed: {res.status_code} - {res.text}")
        raise ValueError(f"Failed to refresh Google access token: {res.text}")
