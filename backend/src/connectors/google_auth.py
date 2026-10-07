"""Google OAuth 2.0 and Token Management Utility for Gmail & Google Calendar."""

import os
import time
import urllib.parse
import uuid
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from modules.operations.models import WorkspaceIntegration

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


async def get_valid_google_token_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> tuple[Optional[str], Optional[str]]:
    """Retrieve a valid Google access token for a workspace, refreshing automatically if expired.

    Returns:
        (access_token, authorized_email) or (None, None)
    """
    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == workspace_id,
        WorkspaceIntegration.provider.in_(["gmail", "google_calendar"]),
        WorkspaceIntegration.connected == True,  # noqa: E712
    )
    res = await db.execute(stmt)
    integration = res.scalars().first()

    if not integration or not integration.config_json:
        # Fallback to server env var if present
        env_token = os.getenv("GOOGLE_ACCESS_TOKEN") or os.getenv("GMAIL_ACCESS_TOKEN")
        if env_token:
            return env_token, os.getenv("GOOGLE_AUTHORIZED_EMAIL", "system@promisecheck.com")
        return None, None

    config = integration.get_decrypted_config()
    access_token = config.get("access_token")
    refresh_token = config.get("refresh_token")
    expires_at = config.get("token_expiry", 0)
    email = config.get("email") or integration.channel_or_scope or "connected-account@google.com"

    now = time.time()
    # If token still valid with at least 60 seconds buffer
    if access_token and expires_at > (now + 60):
        return access_token, email

    # Attempt automatic refresh if refresh_token available
    if refresh_token:
        try:
            logger.info(f"[Google OAuth] Refreshing expired access token for workspace={workspace_id}")
            token_data = await refresh_google_access_token(refresh_token)
            new_access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)

            if new_access_token:
                config["access_token"] = new_access_token
                config["token_expiry"] = now + expires_in
                integration.set_encrypted_config(config)
                await db.commit()
                await db.refresh(integration)
                return new_access_token, email
        except Exception as exc:
            logger.error(f"[Google OAuth] Automatic token refresh failed for workspace={workspace_id}: {exc}")

    return access_token, email
