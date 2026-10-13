# Architecture Decision Record (ADR) Log: Historical Foundation

## Purpose & Scope
This document records the foundational architectural decisions established in the **PromiseCheck** platform prior to the Service Layer extraction. It documents the rationale, trade-offs, and invariants enforced across the codebase so future contributors preserve these guarantees.

---

## Index of Architectural Decisions

| ADR ID | Title | Scope | Status | Date Accepted |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | Modular Monolith Architecture with Internal Boundaries | Core Architecture | Accepted | 2026-09-15 |
| **ADR-002** | Feature-Based Naming & Explicit Module Semantics | Code Standards | Accepted | 2026-09-18 |
| **ADR-003** | Envelope Encryption At Rest for Third-Party Secrets | Security & Data Protection | Accepted | 2026-09-22 |
| **ADR-004** | Strict Tenant Isolation & Anti-IDOR Enforcement | Security & Authorization | Accepted | 2026-09-25 |
| **ADR-005** | Pure Idempotent HTTP GET Endpoints (RFC 9110) | API Design | Accepted | 2026-09-28 |
| **ADR-006** | Fail-Fast External Connector Interface Contract | Integrations | Accepted | 2026-10-01 |
| **ADR-007** | Transactional Outbox Pattern for Intent Durability | Asynchronous Processing | Accepted | 2026-10-03 |
| **ADR-008** | Multi-Queue Priority Celery Worker Architecture | Background Processing | Accepted | 2026-10-05 |
| **ADR-009** | Dual Redis Role: Ephemeral Pub/Sub & 24h Stream Ring Buffer | Realtime Gateway | Accepted | 2026-10-08 |
| **ADR-010** | Human-Friendly API Error Explanations | Developer & User Experience | Accepted | 2026-10-09 |
| **ADR-011** | Environment-Driven Dynamic Origin & Base URL Discovery | Infrastructure & Deployment | Accepted | 2026-10-10 |
| **ADR-012** | Automated Architecture Boundary & Contract Freeze Enforcement | Architecture Governance | Accepted | 2026-10-13 |
| **ADR-013** | Configurable Host Port Mapping for Containerized PostgreSQL | Local Infrastructure | Accepted | 2026-10-13 |
| **ADR-014** | Repository Workspace Hygiene & Removal of Ad-Hoc Artifacts | Codebase Standards | Accepted | 2026-10-14 |

---

### ADR-001: Modular Monolith Architecture with Internal Boundaries
- **Context:** The system coordinates transcript ingestion, AI promise extraction, delivery verification, and multi-tenant integrations. Distributing these early across microservices would introduce distributed transaction failure modes, network latency, and operational overhead.
- **Decision:** Implement a **Modular Monolith**. All domains exist within a single codebase, share a single PostgreSQL database instance, and run under unified FastAPI and Celery worker processes.
- **Consequence:** High execution speed, atomic database transactions across business entities, and single-container deployment feasibility. Cross-module database model coupling must be actively prevented through service boundaries.
- **Revisit Trigger:** When independent teams require isolated deployment pipelines or measured domain bottlenecks necessitate separate process isolation.

---

### ADR-002: Feature-Based Naming & Explicit Module Semantics
- **Context:** Generic module names like `crypto.py`, `base.py`, `dispatcher.py`, or `parser.py` caused developer confusion (e.g. confusing cryptography with cryptocurrency, or mixing HTTP dispatchers with outbox dispatchers).
- **Decision:** Mandate feature-based, capability-revealing names:
  - `core/secret_encryption.py` (not generic `crypto.py`)
  - `connectors/connector_interface.py` (not generic `base.py`)
  - `jobs/outbox_dispatcher.py` (not generic `dispatcher.py`)
  - `ai/promise_extractor.py` and `ai/risk_investigator.py` (not generic `parser.py`)
- **Consequence:** High code self-documentation; developers immediately understand single responsibilities without opening file contents.

---

### ADR-003: Envelope Encryption At Rest for Third-Party Secrets
- **Context:** PromiseCheck integrates with Slack, Gmail, Google Calendar, and Jira, storing third-party OAuth tokens, bot tokens, and webhooks in `workspace_integrations`. Storing secrets in plaintext exposes tenants to severe data exfiltration if the database is leaked.
- **Decision:** Implement symmetric envelope encryption at rest using Fernet authenticated cryptography (AES-128-CBC with HMAC-SHA256 authentication).
  - Implemented in `backend/src/core/secret_encryption.py`.
  - Secrets are encrypted before being written to `WorkspaceIntegration.encrypted_config` and decrypted only in memory when initializing connectors.
  - A central `SECRET_ENCRYPTION_KEY` environment variable protects tenant credentials.
- **Consequence:** Zero plaintext credentials stored in database tables or audit logs.

---

### ADR-004: Strict Tenant Isolation & Anti-IDOR Enforcement
- **Context:** Multi-tenant B2B SaaS platforms are vulnerable to Insecure Direct Object References (IDOR) if a user from Workspace A queries an ID belonging to Workspace B.
- **Decision:**
  - All tenant models inherit from `TenantMixin` (`workspace_id: Mapped[uuid.UUID]`).
  - All database queries filter explicitly by `workspace_id == active_workspace_id`.
  - Every HTTP endpoint resolves `get_active_workspace_id(db, user)` from session JWTs, completely eliminating cross-tenant visibility.
- **Consequence:** High tenant security; foreign workspace lookups return `HTTP 404 Not Found` rather than leaking record existence.

---

### ADR-005: Pure Idempotent HTTP GET Endpoints (RFC 9110)
- **Context:** In early prototypes, certain `GET` endpoints triggered database mutations (such as generating background draft updates, refreshing access tokens, or creating audit log entries). This violated HTTP semantics, broke reverse-proxy caching, and caused duplicate side effects on repeated browser fetches.
- **Decision:** Enforce pure, side-effect-free HTTP `GET` handlers. All mutations, token refreshes, and persistence actions are strictly isolated to `POST`, `PUT`, `PATCH`, or `DELETE` methods.
- **Consequence:** Complies with HTTP RFC 9110; browser retries and crawler requests cannot mutate platform state.

---

### ADR-006: Fail-Fast External Connector Interface Contract
- **Context:** External connectors previously returned silent mocks or fallback dummies when API keys were missing, masking production configuration errors.
- **Decision:** Introduce a formal `BaseConnector` contract in `connectors/connector_interface.py`:
  - Methods: `validate_credentials()`, `health_check()`.
  - Raise typed exceptions: `ConnectorNotConfiguredError` (HTTP 400) and `ConnectorDeliveryError` (HTTP 502) rather than silently returning mock success dictionaries.
- **Consequence:** Production misconfigurations fail immediately with actionable feedback rather than creating silent delivery failures.

---

### ADR-007: Transactional Outbox Pattern for Intent Durability
- **Context:** Direct broker publishing inside HTTP endpoints (`celery_task.delay()`) risks dropping background tasks if the broker is restarting or temporarily unreachable during the HTTP request.
- **Decision:** Implement the Transactional Outbox pattern:
  - Database table `outbox_events` stores intent rows inside the **exact same database transaction** as business entities (`IngestionJob`, `Commitment`).
  - An asynchronous dispatcher (`jobs/outbox_dispatcher.py`) polls pending events using `SELECT ... FOR UPDATE SKIP LOCKED` and routes them to Celery via `apply_async()`.
  - Dead-letter protection: events exceeding 5 retry attempts are marked `status = 'failed'` with error logs to prevent hot-polling loops.
- **Consequence:** 100% durable intent storage; zero dropped background jobs even during message broker downtime.

---

### ADR-008: Multi-Queue Priority Celery Worker Architecture
- **Context:** Long-running LLM extraction and audio transcription tasks previously choked interactive notification alerts and token cleanups in a single shared FIFO queue.
- **Decision:** Configure 3 dedicated task queues in `jobs/celery_app.py`:
  - `high_priority`: For deadline risk scans, notification alerts, and SLA monitoring.
  - `ingestion`: For heavy audio transcription and LLM promise extraction.
  - `default`: For periodic maintenance and token cleanup.
  - Multi-container isolation via `docker-compose.yml` with concurrency cap `-c 4` and distributed Redis scheduler lock (`lock:celery_beat:scan_deadlines`).
- **Consequence:** Heavy audio jobs can never starve time-sensitive SLA alerts.

---

### ADR-009: Dual Redis Role: Ephemeral Pub/Sub & 24h Stream Ring Buffer
- **Context:** Web browsers connecting via Server-Sent Events (SSE) need real-time notifications, but Redis Pub/Sub is fire-and-forget (messages are lost if client Wi-Fi reconnects). However, unbounded Redis Streams cause memory leaks over time.
- **Decision:**
  - **Redis Pub/Sub:** Used strictly for live SSE browser push (`/realtime/stream` & `/events/stream`). Zero retention.
  - **Redis Streams (`stream:ws:{id}:events`):** Used strictly as a 24-hour reconnection ring buffer. Capped at `maxlen=1000` with explicit `EXPIRE 86400` on every write.
  - Reconnecting clients pass `Last-Event-ID` to replay missed events from the stream before listening to the live Pub/Sub channel.
- **Consequence:** Reliable SSE reconnections without Redis memory accumulation.

---

### ADR-010: Human-Friendly API Error Explanations
- **Context:** Complex HTTP 400, 401, 403, 404, 422, and 500 status codes produced raw JSON dumps (`{"detail": "..."}`) that non-technical account executives could not interpret.
- **Decision:**
  - Implemented client-side and server-side error explainers (`frontend/src/lib/api.ts:formatApiError`).
  - Maps status codes and backend error codes to human-friendly remediation messages (e.g. explaining expired OAuth tokens, audio size limits, or invalid status transitions).
- **Consequence:** Immediate self-service diagnosis for end users without requiring engineering support tickets.

---

### ADR-011: Environment-Driven Dynamic Origin & Base URL Discovery
- **Context:** Hardcoded URLs (`http://localhost:8001`, `http://localhost:3000`) in OAuth callbacks and frontend API clients broke production container deployments and reverse proxies.
- **Decision:**
  - Backend uses `settings.API_BASE_URL` and `settings.PUBLIC_APP_URL` configured via environment variables.
  - Frontend (`frontend/src/lib/api.ts` and `frontend/src/hooks/useRealtimeEvents.ts`) auto-detects browser origins dynamically (`window.location.origin/api/v1`) when non-localhost hosts are detected.
- **Consequence:** Seamless multi-environment compatibility across local development, Docker Compose, staging, and production domains.

---

### ADR-012: Automated Architecture Boundary & Contract Freeze Enforcement
- **Context:** As the modular monolith expands across multiple features and contributors, implicit dependencies (e.g. bypassing a domain service to query sibling models directly) and silent API/task contract drift can re-introduce tight coupling and break external consumers.
- **Decision:**
  - Enforce programmatic architecture boundaries using `import-linter` contracts configured in `backend/pyproject.toml` (`Layered Architecture`, `No cycles between modules`, `Encapsulate module internals`).
  - Enforce contract freeze testing using `backend/tools/snapshot_contracts.py --check` against golden snapshots in `docs/baseline/` (OpenAPI schema, Celery user tasks, and SQLAlchemy table metadata).
  - Integrate into `make check` and the contract guard test suite (`backend/tests/contracts/test_architecture_and_migration_guards.py`).
- **Consequence:** Architectural boundaries and public interface contracts are verified automatically with 0 build ambiguity and 0 runtime overhead.

---

### ADR-013: Configurable Host Port Mapping for Containerized PostgreSQL
- **Context:** Developers frequently run native PostgreSQL instances on local machines (e.g. macOS PostgreSQL 18 service on default port 5432) or multi-project databases (e.g. `inviq_dev_db` on port 5433). Hardcoding `5432:5432` in `docker-compose.yml` caused Docker daemon bind conflicts (`address already in use`), blocking the application's PostgreSQL container from starting.
- **Decision:**
  - Update `docker-compose.yml` to parameterize the host port: `${POSTGRES_PORT:-5434}:5432`.
  - Inside the internal Docker bridge network, containers continue communicating over default port `5432` (`postgresql://postgres:postgres@postgres:5432/promisecheck`).
- **Consequence:** Prevents host port collisions on developer workstations while preserving consistent container-to-container service discovery.

---

### ADR-014: Repository Workspace Hygiene & Removal of Ad-Hoc Artifacts
- **Context:** Unmanaged, empty directories (such as legacy `scratch/`) and transient caches (`.grimp_cache/`, `.import_linter_cache/`) clutter the repository root, create confusion about codebase structure, and risk accidental commits of sensitive or temporary artifacts.
- **Decision:**
  - Remove empty legacy scratch directories from the repository root.
  - Standardize scratch space: any scratch scripts or temporary test data must reside in developer-local or ignored environments.
  - Explicitly ignore all linter and AST caches (`.grimp_cache/`, `.import_linter_cache/`) in the root `.gitignore`.
- **Consequence:** Clean, predictable repository hierarchy with zero untracked debris or transient cache leakage.
