"""Operations and integrations domain service for connector secrets and state management."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.operations.models import WorkspaceIntegration


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
