# PromiseCheck

**Customer commitments, connected from conversation to verified delivery.**

PromiseCheck helps SaaS teams capture promises made to customers, assign accountable owners, connect promises to engineering work, detect delivery conflicts, and communicate changes before trust is damaged.

> **Project status:** Architectural specification and implementation blueprint. The core frontend application has been established in `frontend/`; the backend services, integrations catalog, and operational pipelines are being implemented according to the contracts defined below.
>
> **Scope commitment:** MCP, real integrations, permissions, operational reliability, and end-to-end delivery verification are required release capabilities. Phases describe build order, not features that may be silently dropped. Each customer enables only the integrations they authorize; product support for the integration is still required.

## Contents

- [Product and example](#product-and-example)
- [Product mind map](#product-mind-map)
- [Full release scope](#full-release-scope)
- [Screens and user journeys](#screens-and-user-journeys)
- [System overview](#system-overview)
- [Core modules](#core-modules)
- [Integration catalog](#integration-catalog)
- [AI and MCP](#ai-and-mcp)
- [Scalable repository layout](#scalable-repository-layout)
- [Development and configuration](#development-and-configuration)
- [Build sequence and release gates](#build-sequence-and-release-gates)
- [Documentation and references](#documentation-and-references)

## Product and example

Sales promises Acme that SSO will be enabled by September 30. An engineering ticket targets October 5. PromiseCheck retains the original quote, links the ticket, identifies the five-day conflict, and alerts the owner. The owner can investigate, approve a customer update, revise the commitment with history, and eventually attach evidence that SSO is available to Acme.

A ticket marked Done does not by itself prove that a customer can use a feature. A suggested date is not automatically a confirmed promise. Missing engineering data means delivery confidence is unknown.

Primary users: sales, customer success, engineering leads, account owners, and workspace administrators. Customers are records in the initial product; they are not automatically workspace users or recipients.

## Product mind map

```mermaid
mindmap
  root((PromiseCheck))
    Access
      Login and sessions
      Workspaces and roles
      Record permissions
      Audit history
    Capture
      Native Meet transcripts
      Meeting bots
      Audio and transcript uploads
      Email conversations
      Calendar discovery
    Commitments
      Source evidence
      Customer and owner
      Human confirmation
      Versioned promises
      Delivery verification
    Intelligence
      Structured extraction
      Ticket suggestions
      Bounded investigation
      Grounded drafts
      Quality evaluation
    Connections
      Jira and Linear
      Slack and email
      Google Workspace (Meet, Drive, Gmail)
      MCP client and server
    Operations
      Durable jobs
      Retries and reconciliation
      Monitoring and budgets
      Retention and recovery
```

## Full release scope

| Area | Required result |
| --- | --- |
| Identity | OIDC login, server sessions, secure logout, invitations, membership lifecycle, administrative MFA through the identity provider. |
| Access | Workspace isolation, roles, record grants, source visibility, server-enforced permissions on HTTP, jobs, search, and MCP. |
| Capture | Native Google Meet ingestion, transcript upload, audio upload with speech-to-text, selected Gmail conversations, Calendar meeting discovery, and Google Drive document search. |
| Review | Candidate promises, uncertain speaker/customer/date review, confirmed ticket links, rejected candidates, immutable revision history. |
| Engineering | Jira and Linear initial sync, change processing, date-field mapping, blockers, multiple tickets per promise, fresh-state reconciliation. |
| Risk | Date conflicts, approaching deadlines, overdue promises, blockers, missing delivery information, stale evidence, configurable escalation. |
| Communication | Slack and email internal alerts, grouped notifications, delivery status, approval-gated customer updates. |
| Delivery | Release/enablement evidence attachment, owner verification, delivered and reopened states. |
| AI | Structured extraction, semantic matching, bounded tool-using investigation, evidence-grounded drafting, regression evaluation. |
| MCP | Authenticated remote PromiseCheck server and a controlled client gateway for explicitly configured external MCP servers. |
| Operations | Durable jobs, retry limits, connection repair, quotas, observability, exports, deletion, backups, restore tests, deployment and rollback. |

“All integrations” means the explicit catalog below and the common connector framework. It does not imply every vendor on the internet, automatic authorization, or capabilities a provider does not expose. New vendors enter the same documented onboarding and acceptance process.

## Screens and user journeys

| Screen | Required functionality |
| --- | --- |
| Landing page | Product explanation, supported integrations, sign-in and onboarding entry. |
| Onboarding | Create or join workspace, assign initial admin, choose timezone and retention, connect providers, map fields and customers. |
| Overview | Active commitments, risk totals, review backlog, upcoming deadlines, clearly stated count definitions. |
| Commitments | Search, filters, customer/owner/date/status columns, paginated results and detail drawer. |
| Commitment details | Exact quotes, evidence links, ticket status and freshness, revision history, risks, owner actions and approved drafts. |
| Customers | Account identity, reviewed domain mappings, owners, customer timeline and access grants. |
| Review queue | Confirm/edit/reject candidates, resolve ambiguous dates and links, group possible duplicates. |
| Meetings and imports | Capture schedules, capture consent status, upload progress, waiting/failed/ready transcript states. |
| Integrations | Connection owner, selected resources, granted scopes, last sync, reconnection and disconnect controls. |
| Notifications | Alert history, failed delivery, preferences, approved recipients and approval queue. |
| Workspace settings | Roles, invitations, retention, quotas, audit, MCP client grants and external server allowlist. |

### End-to-end user journey

1. Sign in and create or join a workspace.
2. An authorized admin connects approved accounts; a resource owner separately authorizes private source access when required.
3. Choose meeting capture rules, source-sharing policy, ticket projects, delivery-field mapping, and notification destinations.
4. Ingest a real transcript or email. AI extracts candidates with source evidence.
5. A reviewer confirms customer, owner, deadline, conditions, and engineering links.
6. Risk evaluation uses confirmed information and current ticket snapshots.
7. Relevant changes create an internal alert. An investigation agent can gather authorized evidence and draft an update.
8. A permitted reviewer approves the exact customer message and recipient before sending.
9. The owner records verified delivery, or revises the promise without erasing history.
10. Users and authorized MCP clients can retrieve the same permission-filtered records.

## System overview

### Backend Services & Feature Modules Flow

```mermaid
flowchart TD
    %% Clients & Transports
    subgraph CLIENTS["1. Clients & Ingress Channels"]
        WEB["React Web App<br/>(HTTPS / JWT / SSE)"]
        MCP_CLI["External AI Clients<br/>(Claude / Cursor / MCP)"]
        WEBHOOKS["External Webhooks<br/>(Slack / Jira / Google)"]
    end

    %% API Gateway & Core Layer
    subgraph GATEWAY["2. FastAPI Gateway & Core Kernel"]
        API["FastAPI HTTP Router<br/>(/api/v1)"]
        MCP_SRV["FastMCP Server<br/>(Tools & Resources)"]
        SSE_RT["Real-time SSE Gateway<br/>(/realtime/stream)"]
        
        subgraph MIDDLEWARE["Core Middleware & Guards"]
            MW_AUTH["IAM & RBAC Guard<br/>(JWT / Tenant Isolation)"]
            MW_RATE["Dual Rate Limiter<br/>(Sliding Window & Token Bucket)"]
            MW_IDEMP["Idempotency Engine<br/>(Redis Cache / Replay Guard)"]
            MW_SSRF["SSRF Guard<br/>(IP / CIDR / Rebinding Blocks)"]
        end
    end

    %% Modular Feature Modules
    subgraph MODULES["3. Domain Feature Modules (backend/src/modules)"]
        MOD_IAM["IAM Module<br/>- Users & Workspaces<br/>- Memberships & RBAC Roles<br/>- JWT Rotation & Family Replay Guard"]
        MOD_INGEST["Ingestion Module<br/>- Transcript Chunks<br/>- Audio File Streams<br/>- Ingestion Job Ledger"]
        MOD_COMM["Commitments Module<br/>- Candidate Promises<br/>- Lifecycle & Revisions<br/>- Delivery Evidence Verification<br/>- SLA & Deadline Tracking"]
        MOD_INTEG["Integrations Module<br/>- Slack, Jira, Linear<br/>- Google OAuth & Workspace<br/>- Envelope Encryption (AES-128)"]
        MOD_NOTIF["Notifications Module<br/>- At-Risk & Overdue Alerts<br/>- Approval-Gated Messages<br/>- Multi-Channel Dispatch"]
        MOD_CUST["Customers Module<br/>- Accounts & Domain Mapping<br/>- Accountable Owners"]
        MOD_AUDIT["Audit Module<br/>- Append-Only Audit Trail"]
    end

    %% Persistence Layer
    subgraph STORAGE["4. Persistence & Intent Durability"]
        PG[("PostgreSQL 16 Database<br/>- Multi-tenant Schemas (workspace_id)<br/>- Transactional Outbox (outbox_events)<br/>- Row-Level Locking (SKIP LOCKED)")]
        REDIS[("Redis 7 In-Memory Store<br/>- Task Broker & Result Backend<br/>- Sliding Window Rate Limits<br/>- SSE Pub/Sub & 24h Ring Buffer<br/>- Distributed Scheduler Locks")]
    end

    %% Asynchronous Processing Engine
    subgraph ASYNC["5. Asynchronous Processing Engine (backend/src/jobs)"]
        DISPATCHER["Outbox Dispatcher Daemon<br/>(Polls outbox_events with concurrency safety)"]
        BEAT["Celery Beat Scheduler<br/>(Periodic SLA Scans & Token Cleanup)"]
        
        subgraph QUEUES["Multi-Priority Celery Queues"]
            Q_HIGH["high_priority queue<br/>(Deadline risk scans & alerts)"]
            Q_INGEST["ingestion queue<br/>(Audio STT & LLM extraction)"]
            Q_DEFAULT["default queue<br/>(Periodic maintenance & cleanup)"]
        end
        
        WORKERS["Celery Distributed Workers<br/>(Concurrent Task Executors)"]
    end

    %% Connectors & AI Engines
    subgraph CONNECTORS_AI["6. External Connectors & AI Intelligence"]
        AI_ENGINE["AI Processing Engine<br/>- Promise Extractor (LLM)<br/>- Risk Investigator (ReAct Agent)<br/>- Update Draft Generator"]
        LLM_EXT["External LLM APIs<br/>(Anthropic Claude / OpenAI GPT-4)"]
        STT_EXT["Speech-to-Text Service<br/>(Whisper Audio Transcriber)"]
        SAAS_EXT["SaaS Providers<br/>(Slack Webhooks / Jira / Linear API)"]
    end

    %% Flows & Edges
    WEB -->|"REST API Calls"| API
    WEB -->|"SSE Subscriptions"| SSE_RT
    MCP_CLI -->|"MCP Tool Invocations"| MCP_SRV
    WEBHOOKS -->|"OAuth & Incoming Webhooks"| API

    API --> MIDDLEWARE
    MCP_SRV --> MIDDLEWARE
    MIDDLEWARE --> MODULES

    MOD_IAM --> PG
    MOD_CUST --> PG
    MOD_AUDIT --> PG
    MOD_INGEST -->|"Atomically Write Job & Outbox Event"| PG
    MOD_COMM -->|"Atomically Write Promise & Outbox Event"| PG
    MOD_INTEG -->|"Persist Encrypted Secrets"| PG
    MOD_NOTIF --> PG

    MW_RATE -.->|"Rate limit state"| REDIS
    MW_IDEMP -.->|"Cached responses"| REDIS
    SSE_RT <-->|"Live Pub/Sub & 24h Ring Buffer"| REDIS

    PG -->|"Poll pending events (FOR UPDATE SKIP LOCKED)"| DISPATCHER
    DISPATCHER -->|"Enqueue Celery tasks"| QUEUES
    BEAT -->|"Periodic deadline scan triggers"| Q_HIGH
    
    Q_HIGH --> WORKERS
    Q_INGEST --> WORKERS
    Q_DEFAULT --> WORKERS

    WORKERS -->|"Transcribe audio"| STT_EXT
    WORKERS -->|"Extract candidate promises"| AI_ENGINE
    AI_ENGINE --> LLM_EXT
    WORKERS -->|"Deliver notifications"| SAAS_EXT
    WORKERS -->|"Publish realtime events"| REDIS
    WORKERS -->|"Save results & audit records"| PG
```

### End-to-End Service Flow Lifecycle

1. **Ingress & Security Kernel**:
   - Every inbound HTTP, SSE, or MCP call passes through `core/middleware.py`.
   - **Dual Rate Limiter**: Auth endpoints are protected by an in-memory sliding window limiter (5 req/min); file ingestion uses token buckets (refill rate smoothing bursts).
   - **Idempotency Guard**: Mutation endpoints check `Idempotency-Key` headers in Redis, returning cached responses for replayed requests and rejecting altered duplicate payloads with HTTP 422.
   - **Tenant & SSRF Isolation**: Every query filters by `workspace_id` derived from verified JWT session claims. Outbound webhooks and MCP connector URLs are validated through `connectors/ssrf_guard.py` against private CIDRs, cloud metadata endpoints, and DNS rebinding attacks.

2. **Domain Service Execution & Transactional Outbox**:
   - Feature modules (`commitments`, `ingestion`, `integrations`, `iam`, `notifications`) encapsulate business logic behind service classes.
   - When a transcript is uploaded or a promise is confirmed, domain records and a corresponding `OutboxEvent` are written inside the **exact same database transaction**.
   - Zero background tasks are dispatched directly inside HTTP requests, guaranteeing that database rollbacks never emit phantom tasks and broker restarts never lose work.

3. **Asynchronous Dispatch & Multi-Queue Workers**:
   - `jobs/outbox_dispatcher.py` runs a background polling loop using `SELECT ... FOR UPDATE SKIP LOCKED` to prevent double-dispatch across concurrent replicas.
   - Events are routed to dedicated Celery queues:
     - `high_priority`: Time-critical deadline scans and SLA warning alerts.
     - `ingestion`: Heavy audio transcription and LLM promise extraction.
     - `default`: Background token rotation cleanup and database maintenance.
   - Celery workers process jobs, invoke external AI/LLMs or SaaS connectors, persist results, and publish events to Redis Pub/Sub.

4. **Real-time Synchronization & SSE Gateway**:
   - Browser clients subscribe to `/api/v1/events/stream` via Server-Sent Events.
   - Redis Pub/Sub broadcasts live updates across all API instances.
   - A 24-hour Redis Stream ring buffer (`stream:ws:{id}:events`, capped at 1000 items) enables reconnecting clients to replay missed events using `Last-Event-ID`.

## Core modules

| Module | Owns |
| --- | --- |
| `identity` | Identity links, sessions and login callbacks. |
| `workspaces` | Memberships, invitations, roles, teams, record grants. |
| `integrations` | Credentials references, selected resources, sync cursors, subscriptions and connector lifecycle. |
| `ingestion` | Event receipts, uploaded source records, normalized segments and import jobs. |
| `customers` | Accounts, identities, reviewed domain mapping and assigned owners. |
| `commitments` | Candidates, confirmed promises, evidence links, immutable revisions and transitions. |
| `engineering` | Ticket snapshots, project configuration, delivery-field mapping and dependencies. |
| `risk` | Current risk assessments and deterministic evaluation policy. |
| `delivery` | Release/customer enablement evidence and verified fulfillment. |
| `notifications` | Internal alerts, exact message approvals, recipients and delivery attempts. |
| `ai` | Extraction, retrieval, matching, investigation, drafts, prompt/model versions and evaluations. |
| `mcp` | Server tools, client gateway, authorization context, external server configuration and contracts. |
| `audit` | Append-only application audit events and privileged access records. |
| `operations` | Jobs, outbox, quotas, scheduling, retention and operational status. |

## Integration catalog

Every connector below is a required product deliverable. A customer may use only its chosen capture route; the system must not start multiple recorders for a meeting by default.

| Integration | Purpose | Connection and data flow | Completion evidence |
| --- | --- | --- | --- |
| Google identity / configured OIDC provider | Login | Authorization-code flow, PKCE, validated callback, server session. | Login, logout, invitation and invalid-token tests. |
| Google Calendar | Discover selected meetings and scheduled capture | User-authorized API access; maintain event identity and time changes. | Selected meeting is scheduled, rescheduled and canceled correctly. |
| Google Meet | Retrieve native generated transcripts | User OAuth; Workspace Events through Pub/Sub; fetch entries and reconcile. | Real authorized meeting transcript imports with speaker/time evidence. |
| Google Drive | Import authorized Meet artifacts and user-selected files | Scope-minimized access; retain original source ID and permissions. | Eligible file imports; denied/revoked access remains denied. |
| Transcript upload | Import exported conversations | Authenticated upload, file validation, normalization. | Supported formats and malformed files are tested. |
| Audio upload / speech-to-text | Convert authorized recordings | Private upload; worker invokes configured hosted speech provider. | Supported audio produces evidence segments; unsupported files fail clearly. |
| Gmail | Extract commitments from selected email conversations | Separate consent and selection; cursor/history synchronization with reconciliation. | Thread revision and duplicate message handled without duplicate commitment. |
| Jira | Engineering truth | OAuth, selected projects, paginated import, events and periodic reconciliation. | Real ticket update changes linked risk; removed permissions revoke visibility. |
| Linear | Alternative engineering tracker | OAuth, selected teams/projects, paginated import, events and reconciliation. | Same normalized ticket contract and risk tests as Jira. |
| Slack | Internal alerts | Workspace app authorization and approved destinations. | Message delivery, destination denial and retry behavior verified. |
| Email delivery | Internal alerts and approved customer updates | Backend mail adapter with delivery receipts where supported. | Exact approval, bounce handling and ambiguous-send recovery tested. |
| MCP server | Expose PromiseCheck to external AI clients | Authenticated remote transport; tool-level scopes and record checks. | Authorized client completes read and approved mutation scenarios. |
| MCP client gateway | Agent access to configured external tools | Admin allowlist, server authentication, capability contract and scoped tool execution. | At least one real configured server passes contract, denial and timeout tests. |

Provider registration, credentials, OAuth verification, account eligibility, webhook capabilities and recording access are external launch dependencies. The product must show these prerequisites honestly. It must never fabricate a transcript or label synthetic data as a successful live integration.

## AI and MCP

The routine pipeline is explicit: normalize source, extract candidates, validate evidence, suggest matches, request review, evaluate confirmed records, create alerts. The investigation agent is invoked for ambiguous matching or an explicit investigation/draft request; it has a bounded number of read-tool calls and a controlled draft-writing capability.

The initial agent budget is six tool calls, 60 seconds, and a configured token/cost cap per run. These are initial limits to tune from measurements. Exhaustion produces an incomplete investigation state, not an invented answer.

Required internal tools include `get_commitment`, `search_allowed_tickets`, `get_ticket_details`, `get_source_excerpt`, `get_delivery_evidence`, and `save_update_draft`. The backend injects actor and workspace context; the model cannot choose a different tenant.

Required external MCP tools include `list_commitments`, `get_commitment_evidence`, `list_at_risk_commitments`, `investigate_commitment`, `create_update_draft`, and permission-scoped review/delivery actions. External send and review mutations require the same approval workflow as the dashboard. Tool descriptions are not permission grants.

MCP is a required interface in this product, but provider event ingestion and scheduled synchronization continue to run through durable connectors. MCP cannot create provider access that was never granted.

## Scalable repository layout

PromiseCheck is structured as a **feature-based modular monolith**. The backend API, background workers, beat scheduler, outbox dispatcher, and MCP server all share a unified, decoupled codebase without artificial subpackaging or `sys.path` workarounds.

```text
PromiseCheck/
  README.md
  architecture.md
  Dockerfile                   Multi-stage container (frontend & backend targets)
  docker-compose.yml           Full local stack (Postgres, Redis, API, Worker, Beat, Dispatcher, Web)
  requirements.txt             Python root dependencies
  .env.example                 Environment configuration template
  .gitignore
  frontend/                    React + TypeScript + Vite SPA
    package.json
    vite.config.ts
    index.html
    public/
      images/                  Static frontend images and assets
    src/
      components/              UI and layout components
      pages/                   Feature pages (Auth, Commitments, Meetings, Settings)
      services/                API client and HTTP transport
      types/                   Frontend TypeScript schemas
  backend/                     FastAPI modular monolith
    pyproject.toml             Dependency, packaging, ruff, and pytest configurations
    alembic.ini                Database migration configuration
    main.py                    Root convenience entrypoint (python main.py)
    migrations/                Alembic environment and version scripts
    src/
      main.py                  FastAPI application factory, lifespan, CORS, and router registration
      core/                    Shared platform infrastructure
        config.py              Pydantic v2 settings, Twelve-Factor external configuration
        database.py            SQLAlchemy async engine and session factory
        security.py            JWT authentication and password hashing utilities
        logging.py             Standard-stream structured logging setup
      modules/                 Vertical business capability slices
        identity/              Users, authentication, session lifecycle
        workspaces/            Tenant isolation, memberships, and roles
        commitments/           Commitment lifecycle, revisions, evidence matching
        customers/             Customer accounts, domain mappings
        engineering/           Jira & Linear ticket synchronization, field mappings
        risk/                  Deadline analysis and conflict detection
        delivery/              Fulfillment verification and owner attestation
        notifications/         Notification drafting, approval flows, delivery state
        ingestion/             Meeting uploads, webhook processing, transcript parsing
        audit/                 Audit trails and immutable access logs
        operations/            Tenant health, usage budgets, and operations
      connectors/              External integration adapters
        base.py                Abstract connector interface
        google_calendar.py     Google Calendar API adapter
        google_meet.py         Google Meet API adapter
        google_drive.py        Google Drive API adapter
        gmail.py               Gmail API adapter
        recall.py              Recall.ai capture adapter
        speech_to_text.py      Audio transcription adapter
        jira.py                Atlassian Jira REST adapter
        linear.py              Linear GraphQL adapter
        slack.py               Slack notifications adapter
        email.py               Transactional email adapter
        external_mcp.py        External Model Context Protocol client adapter
      ai/                      Model integration layer
        service.py             Prompt composition and LLM extraction service
        prompts.py             Versioned extraction and matching prompts
        router.py              AI evaluation and ad-hoc extraction endpoints
      mcp/                     Model Context Protocol support
        server.py              PromiseCheck MCP tool and resource provider
        client.py              Controlled external MCP client connection
        router.py              MCP HTTP endpoint (/mcp)
      jobs/                    Asynchronous workflow execution
        celery_app.py          Centralized Celery application and task registration
        dispatcher.py          Transactional outbox event dispatcher
        tasks.py               Background task definitions
      entrypoints/             Process entrypoint scripts
        worker.py              Celery worker process
        scheduler.py           Celery Beat periodic scheduler process
        dispatcher.py          Outbox polling dispatcher process
        mcp_server.py          Standalone MCP server runner
    tests/
      conftest.py              Pytest fixtures and test client setup
      unit/                    Unit tests for config, health, security, and packages

```

### Inside a business module

Modules are organized as lightweight, feature-based packages. Instead of rigid, empty four-layer boilerplate (`domain/application/infrastructure/presentation`), each module contains only the files needed for its domain:

```text
modules/commitments/
  router.py        FastAPI route handlers and dependency injection
  schemas.py       Pydantic input/output validation models
  models.py        SQLAlchemy ORM models
  service.py       Core business logic and domain policies
  repository.py    Database access and persistence operations
```

Dependency rule: Routers handle transport and validation, invoking services. Services coordinate business policies and call repositories. Cross-module collaboration occurs via clean service/repository interfaces or transactional outbox events, never by mutating another module's database internals directly.

Frontend features own their views, queries and state. Shared UI components contain no customer or commitment business rules. Generated API clients must not be edited manually.

## Development and configuration

### Chosen implementation baseline

| Layer | Baseline |
| --- | --- |
| Frontend | React, TypeScript, Vite, query cache, accessible component system. |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic. |
| Durable data | PostgreSQL; permission-filtered full-text search, with pgvector for semantic retrieval when implemented as part of matching. |
| Background work | Celery with Redis broker, PostgreSQL job ledger and transactional outbox. |
| Files | Private S3-compatible object storage and short-lived authorized download URLs. |
| AI | Hosted LLM and hosted speech-to-text adapters; pinned model identifiers and versioned prompts. |
| Interfaces | Versioned REST/OpenAPI, provider event endpoints, authenticated MCP over supported remote HTTP transport. |
| Deployment | Containerized backend processes, static frontend delivery, managed database and broker, infrastructure as code. |
| Operations | OpenTelemetry instrumentation, metrics, structured redacted logs, alerts and backup restoration. |

Pin supported dependency versions in lockfiles during implementation. No package versions or cloud account resources are claimed to exist in this document.

### Configuration contract

| Group | Proposed keys | Handling |
| --- | --- | --- |
| App | `APP_ENV`, `PUBLIC_APP_URL`, `API_BASE_URL`, `DEFAULT_TIMEZONE` | Non-secret configuration. |
| Identity | `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `SESSION_SIGNING_KEY` | Secret values remain server-side. |
| Data | `DATABASE_URL`, `REDIS_URL`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ENDPOINT` | Credentials from secret manager or workload identity. |
| Encryption | `KMS_KEY_ID` | Envelope encryption for provider tokens. |
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_PUBSUB_TOPIC`, `GOOGLE_PUBSUB_AUDIENCE` | Scopes configured per selected capability. |
| Capture | `RECALL_API_KEY`, `RECALL_REGION`, `SPEECH_PROVIDER`, `SPEECH_API_KEY` | Capture access and tenant usage budgets required. |
| Trackers | `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `LINEAR_CLIENT_ID`, `LINEAR_CLIENT_SECRET` | Per-connection OAuth grants stored encrypted. |
| Alerts | `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`, `EMAIL_PROVIDER_API_KEY` | Per-destination access and sending policy. |
| AI | `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `EMBEDDING_MODEL`, `AI_RUN_COST_LIMIT` | Server-only values; no production transcript logging. |
| MCP | `MCP_PUBLIC_URL`, `MCP_AUTH_ISSUER`, `MCP_AUDIENCE` | Tenant-specific external server configurations in database. |
| Monitoring | `OTEL_EXPORTER_OTLP_ENDPOINT`, `ERROR_REPORTING_DSN` | Redaction before export. |

Never commit real `.env` files. `.env.example` must contain placeholder values and descriptions only. React build variables are public and must not contain secrets.

### Startup and development experience

PromiseCheck supports both local development and containerized execution using Docker Compose.

#### 1. Full Stack via Docker Compose (Recommended)
All services (PostgreSQL, Redis, Backend API, Celery Worker, Celery Beat Scheduler, Outbox Dispatcher, and Vite Frontend) can be launched simultaneously using the root multi-stage `Dockerfile`:

```bash
# Copy and configure environment variables
cp .env.example .env

# Build and start all services
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API & OpenAPI Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health/ready`

#### 2. Local backend development

Ensure PostgreSQL and Redis are running locally (or via `docker compose up -d postgres redis`):

```bash
# Set up Python virtual environment (from repo root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Option A: Start backend via root convenience entrypoint
python main.py

# Option B: Start backend via uvicorn with live reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Running background processes & workers
Background workers and periodic dispatchers can be run from the `backend/` directory:

```bash
cd backend

# Celery Worker (executes async jobs and ingestion tasks)
python src/entrypoints/worker.py

# Celery Beat (schedules recurring health checks and reconciliation)
python src/entrypoints/scheduler.py

# Outbox Dispatcher (polls outbox events and pushes to message broker)
python src/entrypoints/dispatcher.py

# Standalone MCP Server
python src/entrypoints/mcp_server.py
```

#### 4. Running tests and linter
```bash
cd backend

# Run the pytest test suite
pytest tests/ -v

# Run code style and lint checks with Ruff
ruff check .
ruff format --check .
```

#### 5. Local frontend development
```bash
cd frontend
npm install
npm run dev
```

### API contract outline

| Route family | Responsibility |
| --- | --- |
| `/api/v1/auth/*` | Login callback, session status and logout. |
| `/api/v1/workspaces/*` | Membership and configuration. |
| `/api/v1/integrations/*` | Authorize, select resources, status, reconnect, disconnect. |
| `/api/v1/uploads/*` | Upload creation, completion and validation. |
| `/api/v1/meetings/*` | Capture, transcript and import status. |
| `/api/v1/customers/*` | Accounts, owners and reviewed mappings. |
| `/api/v1/commitments/*` | Search, review, revision, evidence and delivery. |
| `/api/v1/notifications/*` | Draft, approval, delivery state and preferences. |
| `/api/v1/jobs/*` | Permission-filtered progress and retry status. |
| `/events/{provider}` | Provider-specific authenticated delivery, independent of browser sessions. |
| `/mcp` | MCP entrypoint using dedicated resource-server authorization. |

Long tasks return `202 Accepted` with an authorized job resource. Mutations use idempotency keys where repetition could create duplicate business actions and expected record versions where stale updates matter.

## Build sequence and release gates

Every phase is mandatory for the full release.

| Phase | Deliverables | Exit gate |
| --- | --- | --- |
| 1. Foundation | Repository, CI, auth, membership, data model, policy, audit. | Cross-workspace and role tests pass. |
| 2. Source pipeline | Uploads, event ledger, outbox, workers, normalized evidence. | Retries and duplicate deliveries preserve one logical result. |
| 3. Promise workflow | Extraction, customer mapping, review, revisions, search. | Evaluation targets and review workflow pass. |
| 4. Real sources | Meet, Calendar, Drive, Gmail, audio speech service; Recall bot capture (future scope milestone). | Authorized real-source acceptance per catalog. |
| 5. Delivery monitoring | Jira and Linear, field mapping, risks, deadlines, delivery evidence. | Real ticket changes and verified fulfillment work end-to-end. |
| 6. Communication | Slack, email, exact draft approval, failure recovery. | No external send without valid approval; ambiguous sends handled. |
| 7. Agent and MCP | Bounded investigation, MCP server, controlled MCP client. | Tool authorization and external-client end-to-end tests pass. |
| 8. Production readiness | Performance, accessibility, observability, retention, recovery, deployment. | SLO evidence, restored backup, security review and rollback drill. |

### Definition of done

- [ ] Every functional requirement in `architecture.md` has implementation and acceptance evidence.
- [ ] Every catalog integration passes live authorized acceptance and failure scenarios.
- [ ] Native Meet access and meeting bot access are represented honestly in onboarding.
- [ ] MCP works with a real authorized client and the controlled external-server gateway.
- [ ] Dashboard, REST and MCP produce equivalent permission-filtered business results.
- [ ] Original evidence and human changes remain traceable without unrestricted transcript exposure.
- [ ] Duplicate, delayed and revoked-access scenarios are tested.
- [ ] Customer delivery is verified separately from ticket completion.
- [ ] No production completion is asserted from synthetic-only tests or screenshots.
- [ ] Backup restoration, retention deletion, deployment and rollback are demonstrated.

## Documentation and references

Read [architecture.md](architecture.md) for functional and non-functional requirements, access policy, data design, service contracts, sequence diagrams, failure handling, MCP security and architectural decisions.

Provider documentation and technical specifications for integrations. Revalidate exact scopes, protocol versions, event schemas, regional endpoints and provider approval requirements during connector implementation:

- [Google Meet artifacts](https://developers.google.com/workspace/meet/api/guides/artifacts)
- [Google Meet authorization](https://developers.google.com/workspace/meet/api/guides/authenticate-authorize)
- [Google Meet event delivery](https://developers.google.com/workspace/meet/api/guides/events-overview)
- [Recall transcription](https://docs.recall.ai/docs/transcription)
- [Jira delegated OAuth](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture)
