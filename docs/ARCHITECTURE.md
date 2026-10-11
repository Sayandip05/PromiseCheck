# Modular Monolith Architecture Reference

## 1. System Overview & Philosophy

PromiseCheck's backend is structured as a **Modular Monolith** with compile-time and runtime enforced architectural boundaries. Each business domain is encapsulated in an isolated module under `backend/src/modules/`. Cross-module communication is strictly mediated through clean public package interfaces (`__init__.py`), while shared infrastructure and drivers live in strictly layered horizontal layers below domain logic.

Any module can be extracted into an independent microservice in the future without untangling circular dependencies or refactoring core business logic.

---

## 2. Directory Structure

```
backend/src/
├── main.py                     # Composition root: initializes app, mounts routers, registers hooks
│
├── core/                       # Shared foundational kernel (leaf layer)
│   ├── config.py               # Environment & application settings
│   ├── database.py             # SQLAlchemy AsyncEngine & sync_engine for Celery
│   ├── redis.py                # Redis client, caching, and Pub/Sub
│   ├── security.py             # Cryptography, JWT encoding/decoding, password hashing
│   ├── secret_encryption.py    # AES-GCM symmetric secret encryption
│   ├── middleware.py           # HTTP middleware (idempotency, auth contexts)
│   ├── idempotency.py          # Distributed idempotency key checks
│   ├── rate_limiter.py         # Token bucket & sliding window rate limiting
│   ├── metrics.py              # Prometheus metrics provider & registry hooks
│   ├── logging.py              # Structured JSON logging
│   └── outbox/                 # Transactional Outbox pattern implementation
│       ├── models.py           # OutboxEvent table definition
│       ├── service.py          # create_outbox_event transactional helper
│       └── registry.py         # Event handler registry & dispatcher router
│
├── connectors/                 # External service client drivers (no DB access, stateless)
│   ├── connector_interface.py  # Base connector interfaces and exceptions
│   ├── email.py                # SMTP / SendGrid connector
│   ├── slack.py                # Slack webhook and API driver
│   ├── jira.py                 # Atlassian Jira REST client
│   ├── linear.py               # Linear GraphQL client
│   ├── google_auth.py          # Google OAuth token exchange & credentials helper
│   ├── google_calendar.py      # Google Calendar API connector
│   ├── google_drive.py         # Google Drive API connector
│   ├── google_meet.py          # Google Meet API connector
│   ├── gmail.py                # Gmail API connector
│   ├── speech_to_text.py       # Audio transcription client
│   ├── recall.py               # Recall.ai autonomous meeting bot client
│   └── external_mcp.py         # External Model Context Protocol gateway
│
├── ai/                         # AI client and extraction pipelines
│   ├── client.py               # LLM provider wrapper (OpenAI / Claude / Gemini)
│   ├── promise_extractor.py    # Extraction prompt engineering & structured parser
│   ├── prompts.py              # System prompts & few-shot templates
│   └── risk_investigator.py    # Autonomous risk analysis agent
│
├── jobs/                       # Background task runner & Celery configuration (NO imports from modules)
│   ├── celery_app.py           # Celery application initialization, queue routes & beat schedules
│   ├── celery_stats.py         # Dynamic Celery worker metrics provider
│   └── outbox_dispatcher.py    # SELECT FOR UPDATE SKIP LOCKED outbox poller daemon
│
├── api/                        # Transport gateways and system endpoints
│   ├── system/                 # System observability router (/operations/status, /operations/metrics)
│   └── transports/             # Alternative protocol transports
│       ├── realtime/           # Server-Sent Events (SSE) gateway (/events/*, /realtime/*)
│       └── mcp/                # Model Context Protocol (MCP) server & tool implementations
│
└── modules/                    # Self-contained business domain modules
    ├── iam/                    # Identity, Access Management & Workspaces
    │   ├── models.py           # User, Identity, Session, RefreshToken, Workspace, Membership, Invitation
    │   ├── dependencies.py     # FastAPI auth dependencies (get_current_user, require_role)
    │   ├── service.py          # IdentityService, AuthService, WorkspaceService
    │   ├── schemas.py          # Auth & workspace Pydantic DTOs
    │   ├── router.py           # /auth/* and /workspaces/* endpoints
    │   ├── tasks.py            # Celery task: cleanup_expired_tokens
    │   └── __init__.py         # Public exports via __all__
    │
    ├── audit/                  # Immutable audit trail
    │   ├── models.py           # AuditEvent model
    │   ├── service.py          # record_audit_event transactional logger
    │   ├── schemas.py          # AuditEventDTO
    │   ├── router.py           # /audit/* endpoints
    │   └── __init__.py         # Public exports (record_audit_event)
    │
    ├── integrations/           # Third-party workspace provider connections
    │   ├── models.py           # WorkspaceIntegration model
    │   ├── service.py          # IntegrationService (token refresh, credentials persistence)
    │   ├── schemas.py          # Provider DTOs & connection requests
    │   ├── router.py           # /operations/integrations/* and OAuth callbacks
    │   └── __init__.py         # Public exports (IntegrationService, get_valid_google_token_for_workspace)
    │
    ├── commitments/            # Core commitments domain
    │   ├── models.py           # Commitment, DeliveryEvidence models
    │   ├── service.py          # CommitmentService (lifecycle state transitions)
    │   ├── schemas.py          # Commitment DTOs and lifecycle payloads
    │   ├── router.py           # /commitments/* endpoints & sub-router aggregation
    │   ├── delivery/           # Delivery fulfillment verification sub-module (/delivery/*)
    │   ├── risk/               # Risk heuristics & deadlines (/risk/*, Celery: scan_commitment_deadlines)
    │   ├── tickets/            # Engineering tracker integration (/engineering/*)
    │   └── __init__.py         # Public exports (Commitment, CommitmentService, sub-services, schemas)
    │
    ├── customers/              # Customer accounts and SLA health tracking
    │   ├── models.py           # Customer model
    │   ├── service.py          # CustomerService (SLA metrics calculation)
    │   ├── schemas.py          # CustomerDTO, CustomerCreateRequest
    │   ├── router.py           # /customers/* endpoints
    │   └── __init__.py         # Public exports (Customer, CustomerService)
    │
    ├── ingestion/              # Transcript and audio meeting ingestion
    │   ├── models.py           # IngestionJob model
    │   ├── service.py          # IngestionService
    │   ├── schemas.py          # UploadTranscriptRequest, IngestJobResponse
    │   ├── router.py           # /ingestion/* endpoints
    │   ├── tasks.py            # Celery tasks: process_transcript_ingestion, process_audio_ingestion
    │   └── __init__.py         # Public exports (IngestionService)
    │
    └── notifications/          # Alerts and internal delivery sinks
        ├── service.py          # NotificationService
        ├── schemas.py          # NotificationAlert, SendNotificationRequest
        ├── router.py           # /notifications/* endpoints
        ├── tasks.py            # Celery task: dispatch_notification_alert
        └── __init__.py         # Public exports (NotificationService)
```

---

## 3. Dependency Rules & Architectural Enforcement

Architectural integrity is statically verified via `import-linter` configured in `backend/pyproject.toml`.

### 1. Layered Architecture Contract
Strict downward dependency flow:
$$\text{api} \longrightarrow \text{modules} \longrightarrow \text{jobs} \longrightarrow (\text{connectors} \mid \text{ai}) \longrightarrow \text{core}$$

- **`core`** is a leaf layer. It never imports any package from `connectors`, `ai`, `jobs`, `modules`, or `api`.
- **`connectors`** and **`ai`** are stateless driver libraries. They never import from `jobs`, `modules`, or `api`, and perform zero direct database operations.
- **`jobs`** manages background execution. It **never imports `modules`**. It refers to Celery tasks by registered string names and invokes them via `celery_app.send_task(...)`.
- **`modules`** contain business logic. They may import lower layers (`jobs`, `connectors`, `ai`, `core`), but never transport layers (`api`).
- **`api`** handles incoming transports (HTTP, SSE, MCP).

### 2. Module Encapsulation Contract
- Modules must only be imported through their root package:
  ```python
  # CORRECT:
  from modules.iam import User, get_current_user, get_active_workspace_id
  from modules.commitments import CommitmentService, CommitmentDTO

  # FORBIDDEN (enforced by protected import contracts):
  from modules.iam.models import User
  from modules.commitments.service import CommitmentService
  ```
- Modules are strictly acyclic: circular dependencies between modules are prohibited (`type = "acyclic_siblings"`).

### 3. Database & Entity Boundaries
- **No Cross-Module Foreign Keys:** Database foreign keys across module boundaries are forbidden. Modules reference foreign entities strictly using primitive identifiers (`UUID`).
- **No Cross-Module ORM Relationships:** SQLAlchemy `relationship()` declarations must never traverse module boundaries.
- **Transactional Outbox for Decoupled Reactions:** When an action in one module must trigger an asynchronous background reaction, the owning module writes an `OutboxEvent` in the same database transaction. The background poller dispatches it via `core.outbox.registry`.

---

## 4. Contract Freeze List

The following contracts are frozen and guarded by automated contract snapshots (`backend/tools/snapshot_contracts.py`):

1. **HTTP API Contracts:**
   - All HTTP routes, methods, and URL structures remain unchanged (including `/operations/status`, `/operations/metrics`, `/operations/integrations/*`, `/realtime/stream`, `/events/stream`, `/auth/*`, `/workspaces/*`).
   - All OpenAPI operation IDs and request/response schema JSON representations match baseline snapshots exactly.
2. **Database Schema & Migrations:**
   - 14 database tables: `users`, `identities`, `sessions`, `refresh_tokens`, `workspaces`, `memberships`, `invitations`, `commitments`, `delivery_evidences`, `customers`, `ingestion_jobs`, `outbox_events`, `workspace_integrations`, `audit_events`.
   - Production migration head is pinned at `0003_add_workspace_integrations.py`.
3. **Celery Task Contracts:**
   - Explicit task names:
     - `jobs.tasks.process_transcript_ingestion` (queue: `ingestion`)
     - `jobs.tasks.process_audio_ingestion` (queue: `ingestion`)
     - `jobs.tasks.scan_commitment_deadlines` (queue: `high_priority`)
     - `jobs.tasks.cleanup_expired_tokens` (queue: `default`)
     - `jobs.tasks.dispatch_notification_alert` (queue: `high_priority`)
   - Celery beat schedule entries and routing keys are preserved.
4. **Outbox Event Types:**
   - `ingestion.transcript.process`
   - `ingestion.audio.process`
   - `risk.scan.request`
   - `notification.deadline.overdue`
   - `notification.deadline.at_risk`
   - `commitment.created`
   - `commitment.updated`
   - `commitment.confirmed`

---

## 5. Developer Guide: How to Add a New Domain Module

Follow these steps to add a new domain module (e.g., `modules/billing`):

1. **Create Module Package:**
   ```bash
   mkdir -p backend/src/modules/billing
   touch backend/src/modules/billing/{__init__.py,models.py,schemas.py,service.py,router.py}
   ```
2. **Define Models & Schemas:**
   - Place SQLAlchemy models in `models.py`. Reference external tenants via `workspace_id: Mapped[uuid.UUID]` without ORM foreign keys.
   - Place Pydantic models in `schemas.py`.
3. **Implement Service & Router:**
   - Place business logic in `service.py`.
   - Place FastAPI routes in `router.py`. Inject dependencies using `from modules.iam import get_current_user, get_active_workspace_id`.
4. **Expose Public Interface:**
   - In `backend/src/modules/billing/__init__.py`, import and export public symbols via `__all__`:
     ```python
     from modules.billing.models import Subscription
     from modules.billing.service import BillingService

     __all__ = ["Subscription", "BillingService"]
     ```
5. **Add Encapsulation Contract in `pyproject.toml`:**
   ```toml
   [[tool.importlinter.contracts]]
   name = "Encapsulate billing module internals"
   type = "protected"
   protected_modules = [
       "modules.billing.models",
       "modules.billing.service",
       "modules.billing.schemas",
   ]
   allowed_importers = [
       "modules.billing",
   ]
   ```
6. **Mount in `main.py`:**
   Import `from modules.billing.router import router as billing_router` and attach to FastAPI: `app.include_router(billing_router)`.
7. **Verify Boundaries:**
   Run `cd backend && ../.venv/bin/lint-imports` to ensure no architectural violations were introduced.

---

## 6. Developer Guide: How to Add a Celery Task & Outbox Event

### 1. Defining a Celery Task
1. Define the task inside the owning module's `tasks.py` (e.g., `modules/billing/tasks.py`):
   ```python
   from jobs.celery_app import celery_app

   @celery_app.task(name="modules.billing.tasks.process_invoice", queue="default")
   def process_invoice(workspace_id: str, invoice_id: str) -> None:
       ...
   ```
2. Register the module in `jobs/celery_app.py` autodiscovery list:
   ```python
   celery_app.autodiscover_tasks(["modules.billing"], force=True)
   ```

### 2. Publishing & Handling via Transactional Outbox
1. In the module service, write the event in the active DB transaction:
   ```python
   from core.outbox.service import create_outbox_event

   await create_outbox_event(
       db=db,
       workspace_id=workspace_id,
       event_type="billing.invoice.created",
       payload={"workspace_id": str(workspace_id), "invoice_id": str(invoice_id)},
   )
   ```
2. Register the task route in `core/outbox/registry.py`:
   ```python
   register_task(
       event_type="billing.invoice.created",
       task_name="modules.billing.tasks.process_invoice",
       queue="default",
       kwargs_builder=lambda p: {"workspace_id": p["workspace_id"], "invoice_id": p["invoice_id"]},
       description="Triggers invoice generation and payment sync",
   )
   ```
   *(If an event has no asynchronous worker, register it as an acknowledged no-op using `register_noop("billing.invoice.created")` to prevent dead-lettering).*

---

## 7. Recommended Extraction Strategy: First Module to Extract

When traffic, scalability requirements, or deployment velocity justify extracting a service into an independent microservice, **`modules/ingestion`** should be extracted first.

### Why Extract Ingestion First?
1. **Asymmetric Resource Utilization:**
   Ingestion performs heavy CPU and memory work: speech-to-text audio processing, file handling, and large-context LLM token parsing. Isolating it prevents spikes in meeting processing from impacting user-facing HTTP latencies.
2. **Naturally Event-Driven & Decoupled:**
   Ingestion is already 100% decoupled from the rest of the monolith:
   - Dedicated `ingestion_jobs` database table.
   - Dedicated Celery queues (`queue="ingestion"`).
   - Driven entirely by transactional outbox events (`ingestion.transcript.process`, `ingestion.audio.process`).
3. **Clean Extraction Boundary:**
   Extracting `ingestion` only requires pointing the Celery workers to the ingestion worker process and exchanging commitment candidates via the `CommitmentService` API or an event topic.
