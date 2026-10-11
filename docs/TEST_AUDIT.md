# PromiseCheck Backend Test Suite Audit

> Comprehensive baseline audit of the PromiseCheck backend testing infrastructure, test inventory, endpoint coverage, code coverage, architecture alignment, and risk posture.
> Executed as part of Batch 0 preparation to reconcile target test matrices against ground truth.

---

## 1. Tooling & Environment

| Component | Version / Configuration | Notes |
|---|---|---|
| **Python** | 3.13.14 (Darwin ARM64) | Tested on Apple Silicon macOS |
| **Pytest** | 9.1.1 (pluggy 1.6.0) | Default test runner |
| **Pytest Plugins** | `pytest-asyncio` 1.4.0, `pytest-cov` 7.1.0, `pytest-repeat` 0.9.4 | Async execution, branch coverage, loop stability |
| **Test Fixture Helpers** | `respx` 0.23.1, `freezegun` 1.5.5, `factory-boy` 3.3.3 | Wire mocking, deterministic time, entity factories |
| **Integration Test Infrastructure** | `testcontainers` 4.15.0 (`postgres:16-alpine`), `docker-compose.test.yml` | Real PostgreSQL 16 containerization with Alembic migrations |
| **Redis** | Local Redis 7 (`redis-cli ping` -> `PONG`) / containerized | Pub/sub, stream persistence, and rate-limiting validation |
| **Static & Architecture Guard** | `import-linter` 2.15, `ruff` 0.16.7, `tools/snapshot_contracts.py` | Strict ratchet contracts with zero ignores |

---

## 2. Existing Test Inventory & Real-Level Classification

The current test suite consists of **66 tests across 20 files**. Although many files are filed under `tests/unit/`, their real architectural level depends on whether they require database persistence, Redis communication, or the full FastAPI request pipeline via `TestClient`.

### Classification Summary
- **Real Unit Tests:** 23 tests (pure in-memory, no database, no network, no broker)
- **Real Integration Tests:** 42 tests (execute against `TestClient`, SQLite DB, or Redis)
- **Real Workflow Tests:** 1 test (in-process multi-step end-to-end journey)
- **Total:** 66 tests (100% passing)

### Full Test Inventory Breakdown

| # | File Path | Test Function Name | Nominal Path | Real Level | Rationale |
|---|---|---|---|---|---|
| 1 | `tests/authorization/test_token_rotation_and_replay.py` | `test_jwt_token_rotation_and_replay_protection` | auth | Integration | Uses TestClient, writes User/Session/RefreshToken to DB |
| 2 | `tests/authorization/test_workspace_isolation.py` | `test_cross_tenant_workspace_isolation` | auth | Integration | Multi-tenant setup via TestClient & DB |
| 3 | `tests/contracts/test_rate_limiter_contracts.py` | `test_security_headers_contract` | contracts | Integration | TestClient against app routes |
| 4 | `tests/contracts/test_rate_limiter_contracts.py` | `test_rate_limiter_auth_endpoints_burst_protection` | contracts | Integration | Real rate limiter hit through TestClient |
| 5 | `tests/contracts/test_rate_limiter_contracts.py` | `test_sanitized_500_error_contract` | contracts | Integration | TestClient error-handling contract |
| 6 | `tests/integration/test_idempotency_concurrency_pagination.py` | `test_idempotency_retry_prevents_duplicate_commitments` | integration | Integration | TestClient, Redis idempotency key, DB persistence |
| 7 | `tests/integration/test_idempotency_concurrency_pagination.py` | `test_idempotency_retry_customer_creation` | integration | Integration | TestClient, Redis idempotency, DB |
| 8 | `tests/integration/test_idempotency_concurrency_pagination.py` | `test_concurrency_control_optimistic_locking` | integration | Integration | Direct DB session, tests SQLAlchemy version_id |
| 9 | `tests/integration/test_idempotency_concurrency_pagination.py` | `test_customer_pagination_and_headers` | integration | Integration | TestClient, DB customer queries |
| 10 | `tests/integration/test_redis_pubsub_and_ttl.py` | `test_redis_graceful_offline_resilience` | integration | Integration | Redis connection failure handling |
| 11 | `tests/integration/test_redis_pubsub_and_ttl.py` | `test_redis_live_pubsub_and_ttl` | integration | Integration | Real Redis pub/sub messaging and key expiration |
| 12 | `tests/integration/test_redis_pubsub_and_ttl.py` | `test_celery_task_definitions` | integration | Unit | Checks Celery task registry dictionaries in-memory |
| 13 | `tests/integration/test_worker_pubsub_streams.py` | `test_celery_priority_queues_and_routing` | integration | Unit | Inspects celery routing configurations |
| 14 | `tests/integration/test_worker_pubsub_streams.py` | `test_redis_streams_persistence_without_active_subscribers` | integration | Integration | Redis stream operations |
| 15 | `tests/integration/test_worker_pubsub_streams.py` | `test_job_state_24h_ttl_consistency` | integration | Integration | Redis key TTL checks |
| 16 | `tests/integration/test_worker_pubsub_streams.py` | `test_distributed_scheduler_lock_deduplication` | integration | Integration | Redis distributed lock logic |
| 17 | `tests/recovery/test_ai_resilience_and_fallback.py` | `test_empty_transcript_handling` | recovery | Unit | Pure function call on empty input |
| 18 | `tests/recovery/test_ai_resilience_and_fallback.py` | `test_groq_successful_extraction` | recovery | Unit | In-memory mock of LLM provider response |
| 19 | `tests/recovery/test_ai_resilience_and_fallback.py` | `test_llm_api_failure_fails_fast` | recovery | Unit | In-memory mock of LLM provider failure |
| 20 | `tests/recovery/test_ai_resilience_and_fallback.py` | `test_malformed_llm_response_fails_fast` | recovery | Unit | In-memory mock of JSON parse failure |
| 21 | `tests/unit/test_business_logic_breakpoints.py` | `test_google_auth_requires_credential` | unit | Integration | Queries DB for WorkspaceIntegration |
| 22 | `tests/unit/test_business_logic_breakpoints.py` | `test_mcp_tools_authentication_enforced` | unit | Integration | Provisions User/Workspace in DB |
| 23 | `tests/unit/test_business_logic_breakpoints.py` | `test_commitment_status_transitions` | unit | Integration | TestClient against /commitments endpoints with DB |
| 24 | `tests/unit/test_business_logic_breakpoints.py` | `test_draft_update_endpoint` | unit | Integration | TestClient against /commitments/{id}/draft with DB |
| 25 | `tests/unit/test_business_logic_breakpoints.py` | `test_scan_commitment_deadlines_writes_outbox` | unit | Integration | Writes Commitment to DB and runs deadline task |
| 26 | `tests/unit/test_config.py` | `test_cors_origins_parsing` | unit | Unit | Pure Pydantic Settings parsing |
| 27 | `tests/unit/test_config.py` | `test_production_safety_enforcement` | unit | Unit | Pure Pydantic Settings safety validation |
| 28 | `tests/unit/test_google_integrations.py` | `test_google_authorize_url_generation` | unit | Unit | Pure URL generation check |
| 29 | `tests/unit/test_google_integrations.py` | `test_google_connect_direct_token` | unit | Integration | TestClient against /operations/integrations/google |
| 30 | `tests/unit/test_google_calendar_sync_event` | `test_google_calendar_sync_event` | unit | Unit | Connector client mock via AsyncMock |
| 31 | `tests/unit/test_google_integrations.py` | `test_google_gmail_send_update` | unit | Unit | Connector client mock via AsyncMock |
| 32 | `tests/unit/test_health.py` | `test_liveness_probe` | unit | Integration | TestClient request to /operations/status |
| 33 | `tests/unit/test_health.py` | `test_readiness_probe_healthy` | unit | Integration | TestClient request with live DB and Redis checks |
| 34 | `tests/unit/test_health.py` | `test_readiness_probe_degraded` | unit | Integration | TestClient request with patched DB failure |
| 35 | `tests/unit/test_invitation_expiry.py` | `test_invitation_valid_and_expiry_filtering` | unit | Integration | DB session writes Workspace and Invitation |
| 36 | `tests/unit/test_metrics_endpoint.py` | `test_metrics_endpoint_exposition_format` | unit | Integration | TestClient request to /operations/metrics |
| 37 | `tests/unit/test_metrics_endpoint.py` | `test_metrics_records_rate_limiting_and_replays` | unit | Integration | TestClient request verifying Prometheus counters |
| 38 | `tests/unit/test_outbox_dispatcher_trap.py` | `test_commitment_lifecycle_events_dispatch_cleanly` | unit | Integration | DB writes OutboxEvent and calls dispatcher |
| 39 | `tests/unit/test_outbox_dispatcher_trap.py` | `test_unknown_event_type_raises_value_error` | unit | Integration | DB writes OutboxEvent and verifies dispatcher error |
| 40 | `tests/unit/test_outbox_dispatcher_trap.py` | `test_ingestion_event_routes_to_celery_task` | unit | Integration | DB writes OutboxEvent, verifies Celery send_task |
| 41 | `tests/unit/test_outbox_dispatcher_trap.py` | `test_notification_event_routes_to_celery_task` | unit | Integration | DB writes OutboxEvent, verifies Celery send_task |
| 42 | `tests/unit/test_package.py` | `test_package_exports` | unit | Unit | Imports module symbols |
| 43 | `tests/unit/test_rate_limiter_algorithms.py` | `test_sliding_window_in_memory_burst_and_recovery` | unit | Unit | In-memory rate-limiter algorithm |
| 44 | `tests/unit/test_rate_limiter_algorithms.py` | `test_token_bucket_in_memory_burst_and_refill` | unit | Unit | In-memory rate-limiter algorithm |
| 45 | `tests/unit/test_rate_limiter_algorithms.py` | `test_sliding_window_limiter_interface` | unit | Unit | Pure interface type checks |
| 46 | `tests/unit/test_rate_limiter_algorithms.py` | `test_token_bucket_limiter_interface` | unit | Unit | Pure interface type checks |
| 47 | `tests/unit/test_security_and_features.py` | `test_security_headers_and_tracing` | unit | Integration | TestClient middleware verification |
| 48 | `tests/unit/test_security_and_features.py` | `test_all_connectors_fail_fast_when_unconfigured` | unit | Unit | Pure connector instantiation and error checks |
| 49 | `tests/unit/test_security_and_features.py` | `test_commitments_and_customers_endpoints` | unit | Integration | TestClient against commitments and customers |
| 50 | `tests/unit/test_security_and_features.py` | `test_risk_evaluation_endpoint` | unit | Integration | TestClient against /risk/evaluate |
| 51 | `tests/unit/test_security_and_features.py` | `test_delivery_verification_flow` | unit | Integration | TestClient against /delivery/verify |
| 52 | `tests/unit/test_security_and_features.py` | `test_jwt_secret_crash_on_missing_key` | unit | Unit | Pure JWT decode error handling |
| 53 | `tests/unit/test_security_and_features.py` | `test_csp_production_policy_no_unsafe_inline` | unit | Integration | TestClient security header inspection |
| 54 | `tests/unit/test_security_and_features.py` | `test_audio_upload_size_limit_rejection` | unit | Integration | Invokes route handler with mocked DB |
| 55 | `tests/unit/test_security_and_features.py` | `test_registration_error_does_not_leak_email_pii` | unit | Integration | TestClient against /auth/register |
| 56 | `tests/unit/test_ssrf_guard.py` | `test_blocked_ip_ranges` | unit | Unit | Pure IP validation against private CIDR blocks |
| 57 | `tests/unit/test_ssrf_guard.py` | `test_validate_no_ssrf_rejects_private_ips` | unit | Unit | Pure URL validation logic |
| 58 | `tests/unit/test_ssrf_guard.py` | `test_validate_no_ssrf_rejects_empty_or_malformed` | unit | Unit | Pure malformed URL handling |
| 59 | `tests/unit/test_ssrf_guard.py` | `test_validate_no_ssrf_allows_public_ip` | unit | Unit | Pure public IP validation |
| 60 | `tests/unit/test_ssrf_guard.py` | `test_external_mcp_blocks_ssrf_attempt` | unit | Unit | Connector client SSRF guard check |
| 61 | `tests/unit/test_workspace_integrations_db.py` | `test_list_integrations_unauthenticated_returns_401` | unit | Integration | TestClient unauthenticated check |
| 62 | `tests/unit/test_workspace_integrations_db.py` | `test_list_integrations_seeds_default_database_records` | unit | Integration | TestClient seeds default records in DB |
| 63 | `tests/unit/test_workspace_integrations_db.py` | `test_connect_and_disconnect_integration_persists` | unit | Integration | TestClient persists integration updates in DB |
| 64 | `tests/unit/test_workspace_integrations_db.py` | `test_unknown_provider_returns_404` | unit | Integration | TestClient 404 validation |
| 65 | `tests/unit/test_workspace_integrations_db.py` | `test_test_integration_endpoints_for_all_providers` | unit | Integration | TestClient tests connector ping endpoints |
| 66 | `tests/workflows/test_commitment_full_lifecycle.py` | `test_commitment_end_to_end_lifecycle` | workflows | Workflow | Complete multi-step lifecycle via TestClient |

---

## 3. Test Run Stability & Warnings

Across 3 consecutive full-suite runs:
- **Pass rate:** 66 / 66 passed (0 failures, 0 errors, 0 flaky tests).
- **Duration:** 14.2s – 16.6s.
- **Active Deprecation Warnings (4 observed):**
  1. `starlette/testclient.py:53`: `DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.`
  2. `starlette/middleware/base.py:193`: `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`
  3. `backend/src/modules/commitments/router.py:105`: `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`
  4. `backend/tests/unit/test_security_and_features.py:193`: `StarletteDeprecationWarning: 'HTTP_413_REQUEST_ENTITY_TOO_LARGE' is deprecated. Use 'HTTP_413_CONTENT_TOO_LARGE' instead.`

*Remediation note:* Warnings originate in Starlette 1.6 and source router status code constants. Per the hard rules, no `src/` files will be modified; test-side warning cleanup is permitted.

---

## 4. Code & Branch Coverage Analysis

*Generated from Pytest with coverage 7.16.2 / pytest-cov 7.1.0 on `backend/src` with `--cov-branch`:*

- **Total Statements:** 4,562
- **Missed Statements:** 1,841
- **Branches:** 820
- **Partial Branches:** 81
- **Line Coverage:** 59.6%
- **Branch Coverage:** 90.1%
- **Overall Combined Coverage:** **55%**

### Package-by-Package Coverage Breakdown

| Package / Domain | Statements | Miss | Branch | BrPart | Line Cov | Branch Cov | Target | Status |
|---|---|---|---|---|---|---|---|---|
| `src/core` | 926 | 188 | 154 | 20 | 79.7% | 87.0% | >= 85% | Close (needs JWT/encryption edges) |
| `src/connectors` | 606 | 376 | 114 | 12 | 38.0% | 89.5% | >= 75% | **GAP: -37.0%** (many untested connectors) |
| `src/ai` | 107 | 40 | 40 | 12 | 62.6% | 70.0% | >= 80% | **GAP: -17.4%** (investigator untested) |
| `src/jobs` | 117 | 79 | 20 | 2 | 32.5% | 90.0% | >= 80% | **GAP: -47.5%** (dispatcher main loop uncovered) |
| `src/api` (`system`, `transports`) | 234 | 154 | 38 | 0 | 34.2% | 100.0% | >= 80% | **GAP: -45.8%** (SSE and MCP tools untested) |
| `src/modules/iam` | 432 | 245 | 86 | 8 | 43.3% | 90.7% | >= 80% | **GAP: -36.7%** (RBAC, invitations, cleanup) |
| `src/modules/audit` | 24 | 3 | 0 | 0 | 87.5% | 100.0% | >= 80% | **MET: 87.5%** |
| `src/modules/commitments` (incl. delivery, risk, tickets) | 463 | 240 | 122 | 7 | 48.2% | 94.3% | >= 80% | **GAP: -31.8%** (service logic & edge transitions) |
| `src/modules/customers` | 87 | 45 | 14 | 0 | 48.3% | 100.0% | >= 80% | **GAP: -31.7%** (SLA health metrics calculations) |
| `src/modules/ingestion` | 204 | 92 | 28 | 6 | 54.9% | 78.6% | >= 80% | **GAP: -25.1%** (audio processing & Celery tasks) |
| `src/modules/integrations` | 392 | 249 | 110 | 2 | 36.5% | 98.2% | >= 80% | **GAP: -43.5%** (OAuth CSRF, reconnect flows) |
| `src/modules/notifications` | 67 | 34 | 8 | 0 | 49.3% | 100.0% | >= 80% | **GAP: -30.7%** (alert delivery logic & tasks) |
| `src/main.py` | 95 | 26 | 8 | 1 | 72.6% | 87.5% | >= 80% | Near target |
| `src/scripts/seed_demo_workspace.py` | 70 | 70 | 20 | 0 | 0.0% | 0.0% | N/A | Excluded utility |

---

## 5. HTTP Endpoints Audit (Matrix of 32 Routes)

| # | HTTP Method | Route Path | Enclosing Module | Auth Required | Existing Test Coverage Status | Existing Tests |
|---|---|---|---|---|---|---|
| 1 | `POST` | `/api/v1/auth/register` | `iam` | No | PARTIAL | `test_jwt_token_rotation_and_replay_protection`, `test_registration_error_does_not_leak_email_pii` |
| 2 | `POST` | `/api/v1/auth/login` | `iam` | No | PARTIAL | Implicitly touched in auth fixtures |
| 3 | `POST` | `/api/v1/auth/refresh` | `iam` | No | PARTIAL | `test_jwt_token_rotation_and_replay_protection` (does not check family cascade) |
| 4 | `GET` | `/api/v1/auth/me` | `iam` | Yes (Bearer) | COVERED | `test_jwt_token_rotation_and_replay_protection` |
| 5 | `POST` | `/api/v1/auth/google` | `iam` | No | UNTESTED | Missing Google ID token login verification |
| 6 | `POST` | `/api/v1/auth/logout` | `iam` | Yes (Bearer) | UNTESTED | Session revocation endpoint |
| 7 | `GET` | `/api/v1/workspaces/` | `iam` | Yes (Bearer) | PARTIAL | `test_cross_tenant_workspace_isolation` |
| 8 | `POST` | `/api/v1/workspaces/` | `iam` | Yes (Bearer) | PARTIAL | Implicit in setup |
| 9 | `POST` | `/api/v1/workspaces/{id}/invitations` | `iam` | Yes (Admin) | UNTESTED | Tested at DB level, HTTP endpoint untested |
| 10 | `POST` | `/api/v1/workspaces/invitations/accept` | `iam` | Yes (Bearer) | UNTESTED | Accept invitation endpoint |
| 11 | `GET` | `/api/v1/audit/` | `audit` | Yes (Member) | UNTESTED | HTTP query endpoint untested |
| 12 | `GET` | `/api/v1/commitments/` | `commitments` | Yes (Member) | PARTIAL | `test_commitments_and_customers_endpoints` |
| 13 | `POST` | `/api/v1/commitments/` | `commitments` | Yes (Member) | COVERED | `test_commitment_end_to_end_lifecycle`, `test_idempotency_retry_prevents_duplicate_commitments` |
| 14 | `GET` | `/api/v1/commitments/{id}` | `commitments` | Yes (Member) | PARTIAL | `test_commitment_end_to_end_lifecycle` |
| 15 | `PATCH` | `/api/v1/commitments/{id}` | `commitments` | Yes (Member) | PARTIAL | `test_commitment_status_transitions` |
| 16 | `DELETE` | `/api/v1/commitments/{id}` | `commitments` | Yes (Admin) | UNTESTED | Soft delete / cancellation |
| 17 | `POST` | `/api/v1/commitments/{id}/draft` | `commitments` | Yes (Member) | COVERED | `test_draft_update_endpoint` |
| 18 | `POST` | `/api/v1/delivery/verify` | `commitments/delivery` | Yes (Member) | COVERED | `test_delivery_verification_flow` |
| 19 | `POST` | `/api/v1/risk/evaluate` | `commitments/risk` | Yes (Member) | COVERED | `test_risk_evaluation_endpoint` |
| 20 | `GET` | `/api/v1/engineering/tickets` | `commitments/tickets` | Yes (Member) | UNTESTED | External tracker sync queries |
| 21 | `GET` | `/api/v1/customers/` | `customers` | Yes (Member) | COVERED | `test_customer_pagination_and_headers` |
| 22 | `POST` | `/api/v1/customers/` | `customers` | Yes (Member) | COVERED | `test_idempotency_retry_customer_creation` |
| 23 | `GET` | `/api/v1/customers/{id}` | `customers` | Yes (Member) | UNTESTED | Single customer view with SLA breakdown |
| 24 | `POST` | `/api/v1/ingestion/transcript` | `ingestion` | Yes (Member) | UNTESTED | HTTP endpoint untested directly |
| 25 | `POST` | `/api/v1/ingestion/audio` | `ingestion` | Yes (Member) | PARTIAL | `test_audio_upload_size_limit_rejection` |
| 26 | `GET` | `/api/v1/notifications/` | `notifications` | Yes (Member) | UNTESTED | Notifications list |
| 27 | `GET` | `/api/v1/operations/integrations/` | `integrations` | Yes (Admin) | COVERED | `test_list_integrations_seeds_default_database_records` |
| 28 | `POST` | `/api/v1/operations/integrations/{p}/connect` | `integrations` | Yes (Admin) | COVERED | `test_connect_and_disconnect_integration_persists` |
| 29 | `GET` | `/api/v1/operations/integrations/google/callback`| `integrations` | No | UNTESTED | OAuth redirect callback with CSRF state check |
| 30 | `GET` | `/api/v1/operations/status` | `api/system` | No | COVERED | `test_liveness_probe`, `test_readiness_probe_healthy` |
| 31 | `GET` | `/api/v1/operations/metrics` | `api/system` | No | COVERED | `test_metrics_endpoint_exposition_format` |
| 32 | `GET` | `/api/v1/events/stream` & `/realtime/stream` | `api/transports/realtime` | Yes (Bearer) | UNTESTED | SSE streaming endpoints untested |

---

## 6. Checklist Assessment Against Test Plan

| Plan Batch | Target Items | Audit Finding & Gap | Reconciliation Action |
|---|---|---|---|
| **Batch 1: Tenant Isolation & Auth Matrix** | Parametrize across all 10 resources (commitments, customers, delivery, ingestion, integrations, audit, notifications, risk, tickets, MCP) | Existing test `test_cross_tenant_workspace_isolation` checks workspace switching only; does NOT verify 404 response or resource leaking on 9 other resources. | Full matrix remains **CRITICAL** (~30 tests needed). |
| **Batch 2: IAM & Tokens** | Register, Login, Refresh rotation, Replay attack family revocation, Google login, Invitations | `test_jwt_token_rotation_and_replay_protection` verifies 401 on replayed token, but does NOT verify family revocation (`refresh_token_2` revoked). Expired invitations partially tested. | Mark rotation partial; keep family revocation, JWT tampered claims, and invitation flow (~18 tests). |
| **Batch 3: Commitments Domain** | Lifecycle transitions, draft update, same-tx outbox write, audit row creation, delivery verify | `test_commitment_status_transitions` (covered), `test_draft_update_endpoint` (covered), `test_delivery_verification_flow` (covered). Same-tx outbox write and rollback guarantee UNTESTED. | Mark status transitions and delivery verify as covered; focus on transactional atomicity and audit logging (~14 tests). |
| **Batch 4: Outbox Dispatcher** | Poller, concurrency, `SKIP LOCKED`, poison event handling, registry builders | `test_outbox_dispatcher_trap.py` covers 4 routing/dispatcher cases. Concurrency, lock contention, poison event blocking, and registry builder parametrized suite are UNTESTED. | Mark no-op and basic dispatch covered; focus on PostgreSQL `SKIP LOCKED` concurrency and registry coverage (~11 tests). |
| **Batch 5: Celery Tasks & Contracts** | Task names, queues, beat schedule, deadline scanner, audio/transcript ingestion, notification | `test_celery_task_definitions` and `test_celery_priority_queues_and_routing` cover names and queues! Deadline scan outbox write partially covered. | Mark task names and queues `(covered)`; add boundary/freezegun and ingestion execution tests (~12 tests). |
| **Batch 6: AI, Connectors, SSRF, Secrets** | LLM extractor/investigator, 11 connectors, SSRF guard, AES secrets | SSRF IP blocking covered (`test_ssrf_guard.py`); extractor resilience partially covered; investigator and 10 connectors UNTESTED; secret encryption in responses/logs UNTESTED. | Mark basic SSRF and extractor fallback covered; add DNS rebinding/redirects, connector parametrization, and secret leak checks (~24 tests). |
| **Batch 7: Integrations, MCP, Realtime, Ingestion** | Connect/test/disconnect, Google OAuth CSRF state, MCP gateway, SSE streams, Idempotency, Rate limiter | Rate limiter algorithms (covered), Idempotency replay (covered). Google OAuth state/CSRF UNTESTED; SSE UNTESTED; MCP tools UNTESTED; Idempotency conflict UNTESTED. | Mark algorithms and connect/disconnect covered; add OAuth CSRF, SSE, and concurrency tests (~16 tests). |
| **Batch 8: Architecture Guards** | `import-linter` check, OpenAPI snapshot check, Alembic migration roundtrip, route coverage | Tools exist in `backend/tools/` and `pyproject.toml`, but have no automated pytest wrapper test. | Implement automated test guards (~5 tests). |
| **Batch 9: E2E Real Stack** | Full Docker container stack journeys | 0 true multi-process E2E tests exist. | Retain full target (~8 tests). |
| **Batch 10: Quality Gates** | Makefile targets, testing doc, package thresholds | Testing infrastructure and documentation. | Standardize tooling. |

---

## 7. Test Quality & Suite Flaws

1. **SQLite Dialect Fallback:**
   - The test suite runs against `promisecheck.db` (`sqlite+aiosqlite`).
   - SQLite silently ignores `SELECT ... FOR UPDATE SKIP LOCKED`, making concurrency tests on outbox dispatching and row claiming impossible on the default setup.
   - SQLite stores UUIDs and JSON as plain text/strings, masking PostgreSQL-specific JSONB indexing and native UUID constraint failures.
2. **Missing Transactional Rollback Between Tests:**
   - Tests write to a shared SQLite database file on disk (`promisecheck.db`) without rolling back or truncating tables between tests.
   - Test data leaks across test cases (e.g. unique email generators with `uuid.uuid4()` are required to avoid duplicate key conflicts).
3. **In-Memory Mocks vs. HTTP Boundary Mocks:**
   - Connectors and LLMs are frequently patched by replacing internal methods rather than mocking at the HTTP transport boundary (`respx`).
4. **Celery Eager Mode Hiding Async Failures:**
   - The global fixture `celery_eager_mode` sets `task_always_eager=True` for all tests. This masks task serialization failures (e.g., trying to pass un-serializable SQLAlchemy models in Celery args).
5. **Starlette Deprecation Noise:**
   - Deprecation warnings clutter test logs and hide legitimate application warnings.

---

## 8. High-Risk Areas (Risk Map)

```mermaid
quadrantChart
    title Risk vs Existing Test Coverage
    x-axis Low Test Coverage --> High Test Coverage
    y-axis Low Business Impact --> High Business Impact
    quadrant-1 High Risk - Well Covered
    quadrant-2 High Risk - UNDER-TESTED (CRITICAL)
    quadrant-3 Low Risk - Under-Tested
    quadrant-4 Low Risk - Well Covered
    "Tenant Isolation & RBAC": [0.15, 0.95]
    "Refresh Replay Family Revocation": [0.25, 0.90]
    "Outbox Atomic Tx & Concurrency": [0.20, 0.92]
    "Google OAuth CSRF / State": [0.05, 0.88]
    "SSRF DNS Rebinding & Redirects": [0.35, 0.85]
    "Secret Leakage in Logs/API": [0.10, 0.80]
    "Celery Task Name Drift": [0.85, 0.75]
    "Idempotency Key Collisions": [0.65, 0.70]
    "Rate Limiting Algorithms": [0.90, 0.40]
    "CORS / Security Headers": [0.85, 0.35]
```

---

## 9. End-to-End Status

- **Current Status:** 0 multi-process E2E tests exist.
- The workflow test in `tests/workflows/test_commitment_full_lifecycle.py` uses FastAPI's `TestClient` in-process with Celery eager mode and SQLite.
- Background worker processes, Celery Beat schedulers, and asynchronous outbox dispatchers have never been tested together as running daemons.
- **Docker Compose Readiness:** `docker-compose.yml` provides service definitions for API, Worker, Scheduler, Postgres, and Redis. However, no specialized `docker-compose.test.yml` with test overrides, ephemeral ports, and test mock services exists.

---

## 10. Non-Functional & Resilience Posture

- **Rate Limiting:** In-memory algorithms (sliding window and token bucket) are tested. Distributed Redis rate limiting with headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`) and HTTP 429 response structure lacks testing.
- **Idempotency:** Replay of identical request body produces identical response. However, concurrent race conditions (two simultaneous requests with same key) and payload conflict handling are untested.
- **SSRF Guard:** Basic private IP strings (`127.0.0.1`, `10.0.0.1`) are blocked. Advanced bypasses (DNS rebinding to private IP, HTTP 302 redirects to internal metadata `169.254.169.254`, IPv6 mapped addresses) are untested.
- **Service Resilience:** Behavior when Redis or PostgreSQL is down returns 500 error, but error sanitization (ensuring zero internal stack traces or connection strings leak to the client) requires rigorous testing across all endpoints.

---

## 11. Numbers Table: Starting Estimates vs. Reconciled Targets

| Test Suite Layer | Starting Estimate | Covered / Reducible | Reconciled Target (New Tests) |
|---|---|---|---|
| **Unit** | ~70 | -15 (algorithms, pure configs, base SSRF, task configs covered) | **~55** |
| **Integration** | ~100 | -18 (basic CRUD, delivery verify, outbox trap covered) | **~82** |
| **E2E** | ~8 | 0 (none exist) | **~8** |
| **Total New Tests** | **~178** | **-33** | **~145** |

---

## 12. Top 10 Audit Findings

1. **Tenant Isolation Gap:** `test_workspace_isolation.py` only verifies workspace entity separation; no test checks that tenant A cannot access, query, modify, or delete tenant B's commitments, customers, integrations, audit events, or tickets.
2. **Missing Token Family Revocation:** `test_token_rotation_and_replay.py` checks that a reused refresh token returns 401, but completely fails to check if the active family session was revoked to prevent stolen token reuse.
3. **Outbox Transactional Atomicity Untested:** Outbox rows are created, but no test verifies that rolling back a business transaction also prevents the outbox row from being inserted.
4. **Outbox Concurrency on PostgreSQL Untested:** `SKIP LOCKED` behavior cannot run on SQLite; concurrent poller race conditions are entirely unverified.
5. **SSRF Guard Rebinding & Redirect Vulnerability:** Current SSRF checks only parse initial hostname strings; redirects to internal network addresses (`169.254.169.254`) and DNS rebinding bypasses are untested.
6. **OAuth State CSRF Vulnerability Untested:** The Google OAuth flow callback endpoint `/operations/integrations/google/callback` does not have automated CSRF state replay verification.
7. **Secrets in Logs and API Serialization:** `WorkspaceIntegration` stores encrypted tokens, but no test verifies with `caplog` that raw secrets do not leak into debug logs or serialized responses.
8. **Celery Serialization Masked:** Eager mode hides potential `Pickle`/`JSON` task serialization errors with complex objects.
9. **Zero Automated Architecture Regression Tests:** `import-linter` and `tools/snapshot_contracts.py` exist as CLI tools, but no pytest test prevents regressions during test runs.
10. **Database State Pollution:** Lack of per-test transaction rollback or database isolation pollutes `promisecheck.db` across test runs.
