"""Delivery fulfillment verification database model."""

import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class DeliveryEvidence(Base, TenantMixin):
    """Verified evidence proof record tying engineering work to customer commitments."""

    __tablename__ = "delivery_evidence"

    commitment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    commitment_title: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), default="manual_signoff", nullable=False)  # release_notes, pr_merged, manual_signoff
    evidence_title: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="Team Lead", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
