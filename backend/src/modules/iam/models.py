"""Identity module database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.security import Role


class User(Base):
    """User account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    identities: Mapped[list["Identity"]] = relationship(
        "Identity", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class Identity(Base):
    """Linked identity provider (e.g. Google OIDC).

    The (provider, provider_subject) pair is the canonical identity key per the
    architecture: issuer + subject, never email alone.  The unique constraint
    prevents a race on concurrent first-logins from creating duplicate rows for
    the same Google account, which would leave the user in an inconsistent state.
    """

    __tablename__ = "identities"

    # DB-level guard: one row per provider+subject pair globally.
    # This prevents duplicate Google identity rows on concurrent first-login.
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_identity_provider_subject"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, local
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="identities")


class Session(Base):
    """Server-side authenticated session record (legacy)."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class RefreshToken(Base):
    """Secure rotating refresh token record with family tracking and reuse detection."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class Workspace(Base):
    """Organization / Tenant root entity."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="workspace", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation", back_populates="workspace", cascade="all, delete-orphan"
    )


class Membership(Base):
    """User membership and assigned RBAC role within a workspace."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[Role] = mapped_column(
        # Persist the enum *values* ("admin", "member", ...) so they match the
        # PostgreSQL `role` enum created by migration 0001. SQLAlchemy defaults to
        # persisting member *names* ("ADMIN"), which silently fails on Postgres.
        Enum(Role, name="role", values_callable=lambda x: [e.value for e in x]),
        default=Role.MEMBER,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="memberships")


# Backwards compatibility alias
WorkspaceMember = Membership


class Invitation(Base):
    """Pending email invitation to join a workspace."""

    __tablename__ = "invitations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", values_callable=lambda x: [e.value for e in x]),
        default=Role.MEMBER,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="invitations")

