"""Customers database model."""

import uuid
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class Customer(Base, TenantMixin):
    """Managed customer account entity."""

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="on-track", nullable=False)
    status_color: Mapped[str] = mapped_column(String(50), default="#10b981", nullable=False)
    active_promises: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, default=95, nullable=False)
    recent_promise: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="Account Manager", nullable=False)
    domains_json: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
