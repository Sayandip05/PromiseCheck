"""add_evidence_lineage_tickets_approvals_mcp_and_retention_tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-18 00:00:00.000000

Closes the data-model gap called out in the architecture review:

* Evidence lineage (FR-07 / NFR-08): source_documents, source_versions,
  source_segments, evidence_links.
* Ticket sync (FR-11): tickets, commitment_tickets, dependencies.
* Approvals & exact-approval sending (FR-13 / FR-14): notification_drafts,
  approvals, notification_attempts.
* MCP surface (FR-17 / FR-18): external_mcp_servers, mcp_grants.
* Retention & deletion (FR-20 / NFR-13): deletion_jobs.

The migration is idempotent: each table is created only when absent so it can
safely run against databases that were partially migrated by hand.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_COLUMNS = (
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
)

_JSONB = postgresql.JSONB(astext_type=sa.Text())


def _table_exists(inspector: sa.Inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── Evidence lineage (FR-07 / NFR-08) ─────────────────────────────────────
    if not _table_exists(inspector, "source_documents"):
        op.create_table(
            "source_documents",
            *AUDIT_COLUMNS,
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("provider_document_id", sa.String(255), nullable=False),
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(500), nullable=False, server_default=""),
            sa.Column("mime_type", sa.String(255), nullable=True),
            sa.Column("uri", sa.String(1000), nullable=True),
            sa.Column("author", sa.String(255), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id",
                "provider",
                "provider_document_id",
                name="uq_source_documents_ws_provider_doc",
            ),
        )
        op.create_index("ix_source_documents_id", "source_documents", ["id"])
        op.create_index("ix_source_documents_workspace_id", "source_documents", ["workspace_id"])
        op.create_index("ix_source_documents_provider", "source_documents", ["provider"])
        op.create_index(
            "ix_source_documents_provider_document_id", "source_documents", ["provider_document_id"]
        )
        op.create_index(
            "ix_source_documents_integration_id", "source_documents", ["integration_id"]
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "source_versions"):
        op.create_table(
            "source_versions",
            *AUDIT_COLUMNS,
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "document_id", "version_number", name="uq_source_versions_doc_version"
            ),
        )
        op.create_index("ix_source_versions_id", "source_versions", ["id"])
        op.create_index("ix_source_versions_workspace_id", "source_versions", ["workspace_id"])
        op.create_index("ix_source_versions_document_id", "source_versions", ["document_id"])
        op.create_index("ix_source_versions_content_hash", "source_versions", ["content_hash"])
        op.create_index("ix_source_versions_is_current", "source_versions", ["is_current"])
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "source_segments"):
        op.create_table(
            "source_segments",
            *AUDIT_COLUMNS,
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("segment_index", sa.Integer(), nullable=False),
            sa.Column("start_offset", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("end_offset", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("text", sa.Text(), nullable=False, server_default=""),
            sa.Column("speaker", sa.String(255), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["version_id"], ["source_versions.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "version_id", "segment_index", name="uq_source_segments_version_index"
            ),
        )
        op.create_index("ix_source_segments_id", "source_segments", ["id"])
        op.create_index("ix_source_segments_workspace_id", "source_segments", ["workspace_id"])
        op.create_index("ix_source_segments_document_id", "source_segments", ["document_id"])
        op.create_index("ix_source_segments_version_id", "source_segments", ["version_id"])
        op.create_index(
            "ix_source_segments_doc_index", "source_segments", ["document_id", "segment_index"]
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "evidence_links"):
        op.create_table(
            "evidence_links",
            *AUDIT_COLUMNS,
            sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("relation", sa.String(50), nullable=False, server_default="supports"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
            sa.Column("quote_start", sa.Integer(), nullable=True),
            sa.Column("quote_end", sa.Integer(), nullable=True),
            sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["source_segment_id"], ["source_segments.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "commitment_id", "source_segment_id", name="uq_evidence_links_commitment_segment"
            ),
        )
        op.create_index("ix_evidence_links_id", "evidence_links", ["id"])
        op.create_index("ix_evidence_links_workspace_id", "evidence_links", ["workspace_id"])
        op.create_index("ix_evidence_links_commitment_id", "evidence_links", ["commitment_id"])
        op.create_index(
            "ix_evidence_links_source_segment_id", "evidence_links", ["source_segment_id"]
        )
        op.create_index(
            "ix_evidence_links_ws_commitment", "evidence_links", ["workspace_id", "commitment_id"]
        )
        inspector = sa.inspect(bind)

    # ── Ticket sync (FR-11) ───────────────────────────────────────────────────
    if not _table_exists(inspector, "tickets"):
        op.create_table(
            "tickets",
            *AUDIT_COLUMNS,
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("provider_ticket_id", sa.String(255), nullable=False),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("title", sa.String(500), nullable=False, server_default=""),
            sa.Column("status", sa.String(50), nullable=False, server_default="unknown"),
            sa.Column("status_category", sa.String(50), nullable=True),
            sa.Column("assignee", sa.String(255), nullable=True),
            sa.Column("target_date", sa.Date(), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id",
                "provider",
                "provider_ticket_id",
                name="uq_tickets_ws_provider_ticket",
            ),
        )
        op.create_index("ix_tickets_id", "tickets", ["id"])
        op.create_index("ix_tickets_workspace_id", "tickets", ["workspace_id"])
        op.create_index("ix_tickets_integration_id", "tickets", ["integration_id"])
        op.create_index("ix_tickets_provider", "tickets", ["provider"])
        op.create_index("ix_tickets_provider_ticket_id", "tickets", ["provider_ticket_id"])
        op.create_index("ix_tickets_key", "tickets", ["key"])
        op.create_index("ix_tickets_status", "tickets", ["status"])
        op.create_index("ix_tickets_ws_status", "tickets", ["workspace_id", "status"])
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "commitment_tickets"):
        op.create_table(
            "commitment_tickets",
            *AUDIT_COLUMNS,
            sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "required_for_delivery", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
            sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("commitment_id", "ticket_id", name="uq_commitment_tickets_pair"),
        )
        op.create_index("ix_commitment_tickets_id", "commitment_tickets", ["id"])
        op.create_index(
            "ix_commitment_tickets_workspace_id", "commitment_tickets", ["workspace_id"]
        )
        op.create_index(
            "ix_commitment_tickets_commitment_id", "commitment_tickets", ["commitment_id"]
        )
        op.create_index("ix_commitment_tickets_ticket_id", "commitment_tickets", ["ticket_id"])
        op.create_index(
            "ix_commitment_tickets_ws_ticket", "commitment_tickets", ["workspace_id", "ticket_id"]
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "dependencies"):
        op.create_table(
            "dependencies",
            *AUDIT_COLUMNS,
            sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("depends_on_ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dependency_type", sa.String(50), nullable=False, server_default="blocks"),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["depends_on_ticket_id"], ["tickets.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("ticket_id", "depends_on_ticket_id", name="uq_dependencies_pair"),
        )
        op.create_index("ix_dependencies_id", "dependencies", ["id"])
        op.create_index("ix_dependencies_workspace_id", "dependencies", ["workspace_id"])
        op.create_index("ix_dependencies_ticket_id", "dependencies", ["ticket_id"])
        op.create_index(
            "ix_dependencies_depends_on_ticket_id", "dependencies", ["depends_on_ticket_id"]
        )
        inspector = sa.inspect(bind)

    # ── Approvals & notification delivery (FR-13 / FR-14) ─────────────────────
    if not _table_exists(inspector, "notification_drafts"):
        op.create_table(
            "notification_drafts",
            *AUDIT_COLUMNS,
            sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("channel", sa.String(50), nullable=False),
            sa.Column("recipient", sa.String(255), nullable=False, server_default=""),
            sa.Column("subject", sa.String(500), nullable=False, server_default=""),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_notification_drafts_id", "notification_drafts", ["id"])
        op.create_index(
            "ix_notification_drafts_workspace_id", "notification_drafts", ["workspace_id"]
        )
        op.create_index(
            "ix_notification_drafts_commitment_id", "notification_drafts", ["commitment_id"]
        )
        op.create_index("ix_notification_drafts_channel", "notification_drafts", ["channel"])
        op.create_index(
            "ix_notification_drafts_content_hash", "notification_drafts", ["content_hash"]
        )
        op.create_index("ix_notification_drafts_status", "notification_drafts", ["status"])
        op.create_index(
            "ix_notification_drafts_ws_hash",
            "notification_drafts",
            ["workspace_id", "content_hash"],
        )
        op.create_index(
            "ix_notification_drafts_ws_status", "notification_drafts", ["workspace_id", "status"]
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "approvals"):
        op.create_table(
            "approvals",
            *AUDIT_COLUMNS,
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("approver_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("decision", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("expected_content_hash", sa.String(64), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["draft_id"], ["notification_drafts.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_approvals_id", "approvals", ["id"])
        op.create_index("ix_approvals_workspace_id", "approvals", ["workspace_id"])
        op.create_index("ix_approvals_draft_id", "approvals", ["draft_id"])
        op.create_index("ix_approvals_approver_id", "approvals", ["approver_id"])
        op.create_index("ix_approvals_ws_draft", "approvals", ["workspace_id", "draft_id"])
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "notification_attempts"):
        op.create_table(
            "notification_attempts",
            *AUDIT_COLUMNS,
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("channel", sa.String(50), nullable=False),
            sa.Column("provider_message_id", sa.String(255), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("request_fingerprint", sa.String(64), nullable=True),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["draft_id"], ["notification_drafts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"], ondelete="SET NULL"),
            sa.UniqueConstraint(
                "workspace_id", "request_fingerprint", name="uq_notification_attempts_fingerprint"
            ),
        )
        op.create_index("ix_notification_attempts_id", "notification_attempts", ["id"])
        op.create_index(
            "ix_notification_attempts_workspace_id", "notification_attempts", ["workspace_id"]
        )
        op.create_index("ix_notification_attempts_draft_id", "notification_attempts", ["draft_id"])
        op.create_index(
            "ix_notification_attempts_approval_id", "notification_attempts", ["approval_id"]
        )
        op.create_index("ix_notification_attempts_status", "notification_attempts", ["status"])
        op.create_index(
            "ix_notification_attempts_request_fingerprint",
            "notification_attempts",
            ["request_fingerprint"],
        )
        op.create_index(
            "ix_notification_attempts_ws_draft",
            "notification_attempts",
            ["workspace_id", "draft_id"],
        )
        inspector = sa.inspect(bind)

    # ── MCP surface (FR-17 / FR-18) ───────────────────────────────────────────
    if not _table_exists(inspector, "external_mcp_servers"):
        op.create_table(
            "external_mcp_servers",
            *AUDIT_COLUMNS,
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("endpoint_url", sa.String(1000), nullable=False),
            sa.Column("transport", sa.String(20), nullable=False, server_default="http"),
            sa.Column("auth_type", sa.String(50), nullable=False, server_default="none"),
            sa.Column("config_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column(
                "allowed_tools", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
            ),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id", "endpoint_url", name="uq_external_mcp_servers_ws_endpoint"
            ),
        )
        op.create_index("ix_external_mcp_servers_id", "external_mcp_servers", ["id"])
        op.create_index(
            "ix_external_mcp_servers_workspace_id", "external_mcp_servers", ["workspace_id"]
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "mcp_grants"):
        op.create_table(
            "mcp_grants",
            *AUDIT_COLUMNS,
            sa.Column("server_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("tool_name", sa.String(100), nullable=False, server_default="*"),
            sa.Column("scope", sa.String(100), nullable=False),
            sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["server_id"], ["external_mcp_servers.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_mcp_grants_id", "mcp_grants", ["id"])
        op.create_index("ix_mcp_grants_workspace_id", "mcp_grants", ["workspace_id"])
        op.create_index("ix_mcp_grants_server_id", "mcp_grants", ["server_id"])
        op.create_index("ix_mcp_grants_user_id", "mcp_grants", ["user_id"])
        op.create_index("ix_mcp_grants_ws_server", "mcp_grants", ["workspace_id", "server_id"])
        inspector = sa.inspect(bind)

    # ── Retention & deletion (FR-20 / NFR-13) ─────────────────────────────────
    if not _table_exists(inspector, "deletion_jobs"):
        op.create_table(
            "deletion_jobs",
            *AUDIT_COLUMNS,
            sa.Column("resource_type", sa.String(100), nullable=False),
            sa.Column("resource_id", sa.String(255), nullable=False),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("tombstone_hash", sa.String(64), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "metadata_json", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_deletion_jobs_id", "deletion_jobs", ["id"])
        op.create_index("ix_deletion_jobs_workspace_id", "deletion_jobs", ["workspace_id"])
        op.create_index("ix_deletion_jobs_resource_type", "deletion_jobs", ["resource_type"])
        op.create_index("ix_deletion_jobs_resource_id", "deletion_jobs", ["resource_id"])
        op.create_index("ix_deletion_jobs_requested_by", "deletion_jobs", ["requested_by"])
        op.create_index("ix_deletion_jobs_status", "deletion_jobs", ["status"])
        op.create_index("ix_deletion_jobs_ws_status", "deletion_jobs", ["workspace_id", "status"])


def downgrade() -> None:
    # Reverse dependency order.
    op.drop_table("deletion_jobs")
    op.drop_table("mcp_grants")
    op.drop_table("external_mcp_servers")
    op.drop_table("notification_attempts")
    op.drop_table("approvals")
    op.drop_table("notification_drafts")
    op.drop_table("dependencies")
    op.drop_table("commitment_tickets")
    op.drop_table("tickets")
    op.drop_table("evidence_links")
    op.drop_table("source_segments")
    op.drop_table("source_versions")
    op.drop_table("source_documents")
