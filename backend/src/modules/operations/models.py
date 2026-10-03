"""Operations module database models for persistent workspace integrations."""

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
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
