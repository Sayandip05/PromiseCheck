"""Factory-boy model factories for domain entities."""

import uuid
from datetime import date, datetime, timezone
import factory

from core.security import Role, hash_password
from modules.audit.models import AuditEvent
from modules.commitments.models import Commitment, DeliveryEvidence
from modules.customers.models import Customer
from modules.iam.models import Invitation, Membership, RefreshToken, User, Workspace
from modules.integrations.models import WorkspaceIntegration


class UserFactory(factory.Factory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user_{n}_{uuid.uuid4().hex[:6]}@example.com")
    full_name = factory.Faker("name")
    password_hash = factory.LazyFunction(lambda: hash_password("SecurePassword123!"))
    is_active = True


class WorkspaceFactory(factory.Factory):
    """Factory for creating Workspace instances."""

    class Meta:
        model = Workspace

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Workspace {n}")
    slug = factory.Sequence(lambda n: f"workspace-{n}-{uuid.uuid4().hex[:6]}")
    settings = factory.LazyFunction(dict)


class MembershipFactory(factory.Factory):
    """Factory for creating Membership instances."""

    class Meta:
        model = Membership

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    role = Role.MEMBER


class CustomerFactory(factory.Factory):
    """Factory for creating Customer instances."""

    class Meta:
        model = Customer

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Enterprise Customer {n}")
    status = "on-track"
    status_color = "#10b981"
    active_promises = 1
    health_score = 95
    recent_promise = "Deliver SOC-2 Report"
    due_date = "Oct 25, 2026"
    owner = "Account Manager"
    domains_json = factory.LazyFunction(list)


class CommitmentFactory(factory.Factory):
    """Factory for creating Commitment instances."""

    class Meta:
        model = Commitment

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    customer_id = None
    title = factory.Sequence(lambda n: f"Deliver SAML Integration {n}")
    customer_name = "Enterprise Customer"
    owner_name = "Tech Lead"
    owner_email = "lead@example.com"
    promised_by = "Nov 15, 2026"
    promised_date = factory.LazyFunction(lambda: date(2026, 11, 15))
    due_date = factory.LazyFunction(lambda: datetime(2026, 11, 15, 23, 59, 59, tzinfo=timezone.utc))
    status = "awaiting-review"
    status_label = "Awaiting review"
    category = "awaiting-review"
    is_confirmed = False


from modules.ingestion.models import IngestionJob


class DeliveryEvidenceFactory(factory.Factory):
    """Factory for creating DeliveryEvidence instances."""

    class Meta:
        model = DeliveryEvidence

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    commitment_id = factory.LazyFunction(uuid.uuid4)
    commitment_title = "Enterprise Feature Fulfillment"
    customer_name = "Enterprise Customer"
    evidence_type = "pr_merged"
    evidence_title = "Pull Request #42 Merged"
    evidence_url = "https://github.com/org/repo/pull/42"
    verified_by = "Lead Engineer"
    notes = "Verified against delivery criteria"


class IngestionJobFactory(factory.Factory):
    """Factory for creating IngestionJob instances."""

    class Meta:
        model = IngestionJob

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    job_id = factory.Sequence(lambda n: f"job_{n}_{uuid.uuid4().hex[:6]}")
    customer_name = "Enterprise Customer"
    meeting_title = "Roadmap Sync"
    source_type = "upload"
    status = "completed"
    candidates_extracted = 2
    transcript_preview = "Customer requested SAML 2.0 integration by Nov 15."
    candidates_json = factory.LazyFunction(list)


class AuditEventFactory(factory.Factory):
    """Factory for creating AuditEvent instances."""

    class Meta:
        model = AuditEvent

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    actor_id = factory.LazyFunction(uuid.uuid4)
    action = "commitment.created"
    target_type = "commitment"
    target_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    description = "Created commitment for Enterprise Customer"
    payload = factory.LazyFunction(dict)
    ip_address = "127.0.0.1"


class IntegrationFactory(factory.Factory):
    """Factory for creating WorkspaceIntegration instances."""

    class Meta:
        model = WorkspaceIntegration

    id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    provider = "slack"
    name = "Slack Integration"
    connected = True
    status_text = "Connected as #general"
    last_sync = "Just now"
    channel_or_scope = "#general"
    description = "Slack notifications channel"
    config_json = factory.LazyFunction(lambda: {"webhook_url": "https://hooks.slack.com/services/T00/B00/X00"})

