"""Operations module database models for persistent workspace integrations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class WorkspaceIntegration(Base, TenantMixin):
    """Persistent storage for third-party connector credentials and sync state (Factor VI)."""

    __tablename__ = "workspace_integrations"
    __table_args__ = (
        Index("ix_workspace_integrations_ws_provider", "workspace_id", "provider", unique=True),
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_text: Mapped[str] = mapped_column(String(255), default="Not connected", nullable=False)
    last_sync: Mapped[str] = mapped_column(String(100), default="Never", nullable=False)
    channel_or_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    def get_decrypted_config(self) -> dict:
        """Return decrypted credentials and configuration dict in-memory."""
        from core.secret_encryption import decrypt_config_dict

        return decrypt_config_dict(self.config_json or {})

    def set_encrypted_config(self, cfg: dict) -> None:
        """Encrypt sensitive fields in credentials dict before persisting to config_json."""
        from core.secret_encryption import encrypt_config_dict

        self.config_json = encrypt_config_dict(cfg or {})


class ExternalMCPServer(Base, TenantMixin):
    """Workspace-authorized outbound Model Context Protocol server allowlist entry."""

    __tablename__ = "external_mcp_servers"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "endpoint_url",
            name="uq_external_mcp_servers_ws_endpoint",
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    transport: Mapped[str] = mapped_column(String(20), default="http", nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    allowed_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def get_decrypted_config(self) -> dict:
        """Return decrypted credentials and configuration dict in-memory."""
        from core.secret_encryption import decrypt_config_dict

        return decrypt_config_dict(self.config_json or {})

    def set_encrypted_config(self, cfg: dict) -> None:
        """Encrypt sensitive fields in credentials dict before persisting to config_json."""
        from core.secret_encryption import encrypt_config_dict

        self.config_json = encrypt_config_dict(cfg or {})


class MCPGrant(Base, TenantMixin):
    """Explicit scope grant allowing a user to invoke a tool on an external MCP server."""

    __tablename__ = "mcp_grants"
    __table_args__ = (Index("ix_mcp_grants_ws_server", "workspace_id", "server_id"),)

    server_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_mcp_servers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100), default="*", nullable=False)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
