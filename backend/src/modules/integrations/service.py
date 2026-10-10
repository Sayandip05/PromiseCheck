import os
import time
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from modules.integrations.models import WorkspaceIntegration

logger = get_logger("modules.integrations.service")


class IntegrationService:
    """Encapsulates third-party integration credential storage, encryption, and lifecycle."""

    @staticmethod
    async def get_integration(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> Optional[WorkspaceIntegration]:
        """Fetch workspace integration row ensuring tenant isolation."""
        stmt = select(WorkspaceIntegration).where(
            WorkspaceIntegration.workspace_id == workspace_id,
            WorkspaceIntegration.provider == provider,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_decrypted_config(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> dict[str, Any]:
        """Retrieve and decrypt credentials dictionary in-memory."""
        integration = await IntegrationService.get_integration(db, workspace_id, provider)
        if not integration or not integration.connected:
            return {}
        return integration.get_decrypted_config()

    @staticmethod
    async def save_integration(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
        config: dict[str, Any],
        name: Optional[str] = None,
        channel_or_scope: Optional[str] = None,
        status_text: Optional[str] = None,
    ) -> WorkspaceIntegration:
        """Create or update workspace integration with encrypted credentials at rest."""
        integration = await IntegrationService.get_integration(db, workspace_id, provider)
        display_name = name or provider.replace("_", " ").capitalize()

        if not integration:
            integration = WorkspaceIntegration(
                workspace_id=workspace_id,
                provider=provider,
                name=display_name,
                connected=True,
                status_text=status_text or f"Connected to {display_name}",
                last_sync="Active",
                channel_or_scope=channel_or_scope,
                description=f"Active integration for {display_name}",
                config_json={},
            )
            integration.set_encrypted_config(config)
            db.add(integration)
        else:
            integration.connected = True
            integration.name = display_name
            integration.status_text = status_text or f"Connected to {display_name}"
            integration.last_sync = "Active"
            if channel_or_scope is not None:
                integration.channel_or_scope = channel_or_scope
            integration.set_encrypted_config(config)

        await db.commit()
        await db.refresh(integration)
        return integration

    @staticmethod
    async def disconnect_integration(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> bool:
        """Revoke and disconnect an external integration."""
        integration = await IntegrationService.get_integration(db, workspace_id, provider)
        if not integration:
            return False

        integration.connected = False
        integration.status_text = "Disconnected"
        integration.config_json = {}
        await db.commit()
        return True

    @staticmethod
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
                from connectors.google_auth import refresh_google_access_token

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


# Module-level alias for convenient import
get_valid_google_token_for_workspace = IntegrationService.get_valid_google_token_for_workspace

