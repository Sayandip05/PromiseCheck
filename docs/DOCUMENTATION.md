# PromiseCheck: Unified Architecture, Testing & Engineering Reference

This document is the consolidated reference for PromiseCheck's modular monolith architecture, service layer contracts, testing architecture, verification gates, and historical refactoring decisions.

---

## Table of Contents

1. [System Overview & Architecture Philosophy](#1-system-overview--architecture-philosophy)
2. [Directory Layout & Domain Modules](#2-directory-layout--domain-modules)
3. [Architecture Boundaries & Contract Freezing](#3-architecture-boundaries--contract-freezing)
4. [Testing Architecture & Developer Guide](#4-testing-architecture--developer-guide)
5. [Test Plan Execution & Final Quality Report](#5-test-plan-execution--final-quality-report)
6. [Catalog of Documented Bugs (BUG-1 to BUG-9)](#6-catalog-of-documented-bugs-bug-1-to-bug-9)
7. [Architecture Decision Records (ADR Summary)](#7-architecture-decision-records-adr-summary)

---

## 1. System Overview & Architecture Philosophy

PromiseCheck is a multi-tenant B2B SaaS platform designed to capture commitments made in sales and customer success conversations, trace them to engineering tickets, detect delivery conflicts, and verify fulfillment.

### Why a Modular Monolith?
- **Domain Encapsulation Without Microservice Overhead**: Coordinates transcript ingestion, AI promise extraction, delivery verification, and multi-tenant integrations in a single codebase with a single PostgreSQL instance and unified worker processes.
- **Transactional Consistency**: Allows business mutations and background event intent to be written atomically within the **same database transaction** via the Transactional Outbox pattern.
- **Future Extraction Readiness**: Each module is self-contained. Any domain (such as `ingestion`, with heavy audio processing) can be split into an independent service without refactoring core logic.

---

## 2. Directory Layout & Domain Modules

```
backend/src/
├── main.py                     # Composition root: initializes app, mounts routers, registers hooks
│
├── core/                       # Shared foundational kernel (leaf layer)
│   ├── config.py               # Environment & application settings
│   ├── database.py             # SQLAlchemy AsyncEngine & sync_engine for Celery
│   ├── redis.py                # Redis client, caching, Pub/Sub, and 24h stream ring buffer
│   ├── security.py             # JWT encoding/decoding, password hashing
│   ├── secret_encryption.py    # Envelope encryption at rest (Fernet AES-128 with HMAC-SHA256)
│   ├── middleware.py           # HTTP middleware (rate limiting, idempotency, auth context)
│   ├── idempotency.py          # Distributed idempotency key checks
│   ├── rate_limiter.py         # Dual rate limiting (Token Bucket & Sliding Window)
│   ├── metrics.py              # Prometheus metrics provider & registry hooks
│   ├── logging.py              # Structured JSON logging
│   └── outbox/                 # Transactional Outbox pattern (models, service, registry)
│
├── connectors/                 # External service client drivers (stateless, no DB access)
│   ├── connector_interface.py  # BaseConnector contract with fail-fast exception handling
│   ├── slack.py, jira.py, linear.py, google_auth.py, google_calendar.py, speech_to_text.py
│   └── ssrf_guard.py           # SSRF validation against private CIDRs and cloud metadata
│
├── ai/                         # LLM prompt construction & structured extraction
│   ├── client.py               # LiteLLM/OpenAI/Anthropic client wrapper
│   ├── promise_extractor.py    # Structured extraction of commitment candidates
│   └── risk_investigator.py   # ReAct agent investigating ticket conflicts
│
├── jobs/                       # Background task definitions & Celery runtime
│   ├── celery_app.py           # Celery instance and multi-queue priority routing
│   └── outbox_dispatcher.py    # Polling daemon with SELECT ... FOR UPDATE SKIP LOCKED
│
├── modules/                    # Self-contained business domains
│   ├── iam/                    # Users, workspaces, memberships, roles, JWT token rotation
│   ├── commitments/            # Candidate promises, lifecycle, delivery evidence, SLA tracking
│   ├── ingestion/              # Transcript chunk ingestion, audio upload, STT dispatch
│   ├── integrations/           # OAuth lifecycle (Slack, Jira, Linear, Google Workspace)
│   ├── notifications/          # At-risk/overdue SLA alerts, approval-gated messages
│   ├── customers/              # Accounts, domain mapping, assigned owners
│   └── audit/                  # Append-only immutable audit trail
│
└── api/                        # Transport delivery mechanisms
    ├── system/router.py        # /healthz and /api/v1/health endpoints
    └── transports/
        ├── mcp/                # FastMCP server tools and external client gateway
        └── realtime/           # Server-Sent Events (SSE) router (/realtime/stream)
```

---

## 3. Architecture Boundaries & Contract Freezing

PromiseCheck enforces strict modular-monolith boundaries at build and test time:

### Layering Hierarchy (`import-linter`)
```
api  ->  modules  ->  jobs  ->  (connectors | ai)  ->  core
```
- **Layered Architecture**: Upper layers can import lower layers; lower layers can NEVER import upper layers.
- **Acyclic Modules**: No circular dependencies are allowed between sibling feature modules in `modules/`.
- **Internal Module Encapsulation**: Private internals (e.g. `modules.iam.models`) cannot be directly imported by external modules without importing from the public `__init__.py`.

### Contract Freeze Mechanism (`backend/tools/snapshot_contracts.py`)
- Automatically validates current contracts against golden baselines stored in `docs/baseline/`:
  - `openapi.json`: All 48 REST endpoints, parameters, and response schemas.
  - `celery_tasks.json`: Pinned task names, queues, and beat schedules.
  - `table_metadata.json`: Pinned SQLAlchemy table definitions and schemas.
- Run `make contracts-check` to assert zero contract drift.

---

## 4. Testing Architecture & Developer Guide

### Test Pyramid & Markers
All tests reside in `backend/tests/` and use explicit pytest markers:

| Level | Definition | Marker | Execution Time | Scope |
|---|---|---|---|---|
| **Unit** | Isolated in-memory logic (no DB, no network, no broker) | `@pytest.mark.unit` | ~2.3 seconds | ~160 tests |
| **Integration** | Real PostgreSQL + Redis, FastAPI TestClient, outbox transactions | `@pytest.mark.integration` | ~35 seconds | ~155 tests |
| **E2E** | Full multi-step user journeys spanning ingestion, dispatch, worker & auth | `@pytest.mark.e2e` | ~6.1 seconds | 9 tests |

### Makefile Quality Targets
```bash
make test-unit         # Run isolated unit tests
make test-integration  # Run integration tests against PostgreSQL & Redis
make test-e2e          # Run end-to-end full stack user journeys
make test-all          # Run the entire test suite (324 tests)
make coverage          # Run full test suite with code coverage (enforces fail-under 65%)
make lint-imports      # Verify 9 modular-monolith boundary contracts
make contracts-check   # Verify contract snapshot freeze against baseline
make check             # Full quality gate (lint-imports + snapshot check + test-all)
```

### Standard Tenant Isolation Pattern (Anti-IDOR)
Multi-tenancy must be enforced at every module layer. Every test verifying a tenant-scoped resource must assert that Tenant B cannot access Tenant A's data:
```python
# 1. Arrange: Create Tenant A and Tenant B
user_a, ws_a = UserFactory(), WorkspaceFactory()
user_b, ws_b = UserFactory(), WorkspaceFactory()
resource_a = CommitmentFactory(workspace_id=ws_a.id)

# 2. Act: Tenant B attempts to access Tenant A's resource
headers_b = {"X-Workspace-Id": str(ws_b.id)}
res = app_client.get(f"/api/v1/commitments/{resource_a.id}", headers=headers_b)

# 3. Assert: Must return 404 Not Found (or 403 Forbidden) and NEVER leak existence
assert res.status_code in (404, 403)
```

### Strict Xfail Bug Logging Policy
- **Zero Modifications to `backend/src/`**: When tests expose a real bug in production code, do NOT alter `src/`.
- Decorate the test with `@pytest.mark.xfail(strict=True, reason="BUG-n: <description>")`.
- `strict=True` guarantees that when an engineer later fixes the bug in `src/`, pytest reports an `XPASS` and fails the build, ensuring the marker is removed promptly.

---

## 5. Test Plan Execution & Final Quality Report

The 11-batch test hardening plan (Batches 0 through 10) was fully completed and committed on branch `refactor/modular-monolith`:

### Test Suite Comparison
| Metric | Pre-Hardening Baseline | Post-Hardening Suite |
|---|---|---|
| **Total Tests** | 66 tests | **324 tests** (+258 new high-leverage tests) |
| **Unit Tests** | 60 | **160 tests** (156 passed, 4 strict xfailed) |
| **Integration Tests** | 6 | **155 tests** (147 passed, 8 strict xfailed) |
| **E2E Journey Tests** | 0 | **9 tests** (8 passed, 1 strict xfailed) |
| **Pass / Fail Status** | 66 passed | **311 passed, 13 strict xfail, 0 failed** |
| **Execution Time** | ~10s | **~80s full suite** (`test-unit` runs in 2.3s) |
| **Modular Contracts** | Unenforced | **9 kept, 0 broken (`import-linter`)** |
| **Baseline Snapshots** | None | **Zero diff (`snapshot_contracts.py`)** |
| **Code Coverage** | Untracked | **71% overall** (`core`: 85%, `ai`: 84%, `jobs`: 75%) |
| **Flakiness (3 Runs)** | Untracked | **0% flakiness (100% deterministic)** |
| **`src/` Integrity** | — | **0 edits (`git diff --stat -- backend/src` is completely empty)** |

---

## 6. Catalog of Documented Bugs (BUG-1 to BUG-9)

All bugs below were discovered by the test suite, documented, and marked `@pytest.mark.xfail(strict=True)`:

1. **BUG-1** (`src/modules/iam/router.py:165`):
   `GET /api/v1/workspaces/{workspace_id}/members` does not verify that the authenticated user belongs to the requested workspace. A user from Workspace A can pass Workspace B's ID and list its members.
2. **BUG-2** (`src/modules/commitments/router.py:102-120`):
   `PATCH /api/v1/commitments/{id}` transitions commitment status without filtering by `workspace_id`. A user from Workspace B can alter the status of a commitment belonging to Workspace A.
3. **BUG-3** (`src/modules/commitments/delivery/router.py:35-46`):
   `POST /api/v1/delivery/verify` and `GET /api/v1/delivery/evidence` fail on PostgreSQL with HTTP 500 (`UndefinedColumnError`) because `workspace_id` is defined on Python model `DeliveryEvidence` but absent from Alembic migration 0001.
4. **BUG-4** (`src/modules/iam/service.py:180-210`):
   Workspace invitation acceptance does not verify that the accepting user's email matches the invited email, allowing unintended users with the link to claim membership.
5. **BUG-5** (`src/jobs/outbox_dispatcher.py:45-80`):
   Outbox events with no configured Celery task handler (e.g. no-ops like `commitment.confirmed`) increment retry count on every dispatch run until needlessly dead-lettering.
6. **BUG-6** (`src/connectors/ssrf_guard.py:40-95`):
   SSRF protection does not validate IPv4-mapped IPv6 addresses (e.g. `::ffff:127.0.0.1` or `::ffff:169.254.169.254`) and does not prevent DNS rebinding attacks where a public hostname resolves to a private IP during HTTP socket connection.
7. **BUG-7** (`src/modules/integrations/router.py:529-570`):
   Google OAuth state is stateless (`ws_id:nonce`) and is not verified against Redis or session storage upon callback, creating CSRF state forge/replay vulnerability.
8. **BUG-8** (`src/modules/integrations/router.py`):
   Missing route alias for `/api/v1/operations/integrations/google/callback` expected by legacy Google Cloud OAuth console configurations.
9. **BUG-9** (`src/api/transports/mcp/tools.py:35`):
   MCP tool `list_commitments` calls `CommitmentService.list_commitments(db, ws_uuid, status=status, limit=limit, offset=offset)`, but the actual service method signature expects positional arguments `(db, workspace_id, status_filter, category_filter, search, page, page_size)`, causing a `TypeError`.

---

## 7. Architecture Decision Records (ADR Summary)

| ADR ID | Decision Title | Scope | Status |
| :--- | :--- | :--- | :--- |
| **ADR-001** | Modular Monolith Architecture with Internal Boundaries | Core Architecture | Accepted |
| **ADR-002** | Feature-Based Naming & Explicit Module Semantics | Code Standards | Accepted |
| **ADR-003** | Envelope Encryption At Rest for Third-Party Secrets (AES-128 Fernet) | Security | Accepted |
| **ADR-004** | Strict Tenant Isolation & Anti-IDOR Enforcement (`workspace_id`) | Authorization | Accepted |
| **ADR-005** | Pure Idempotent HTTP GET Endpoints (RFC 9110 compliant) | API Design | Accepted |
| **ADR-006** | Fail-Fast External Connector Interface Contract (`BaseConnector`) | Integrations | Accepted |
| **ADR-007** | Transactional Outbox Pattern for Intent Durability | Asynchronous Processing | Accepted |
| **ADR-008** | Multi-Queue Priority Celery Worker Architecture (`high_priority`, `ingestion`) | Background Processing | Accepted |
| **ADR-009** | Dual Redis Role: Ephemeral Pub/Sub & 24h Stream Ring Buffer | Realtime Gateway | Accepted |
| **ADR-010** | Human-Friendly API Error Explanations | DX & User Experience | Accepted |
| **ADR-011** | Environment-Driven Dynamic Origin & Base URL Discovery | Infrastructure | Accepted |
| **ADR-012** | Automated Architecture Boundary & Contract Freeze Enforcement | Governance | Accepted |
| **ADR-013** | Configurable Host Port Mapping for Containerized PostgreSQL (`${POSTGRES_PORT:-5434}`) | Infrastructure | Accepted |
| **ADR-014** | Repository Workspace Hygiene & Removal of Ad-Hoc Artifacts | Codebase Standards | Accepted |
