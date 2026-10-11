# Test Strategy and Implementation Plan

> Single source of truth for adding important tests to the backend.
> The coding agent MUST update the Progress Tracker and Findings Log in THIS file as it works.
> Read `docs/TEST_AUDIT.md`, `docs/ARCHITECTURE.md` and `docs/REFACTOR_PLAN.md` first.

## 0. Progress Tracker

Mark `[x]` with `(date, commit hash, tests added)`. Resume from the first unchecked batch.

- [x] Batch 0: Reconcile with audit + test infrastructure (2026-10-11, 1d59481, 3 tests added)
- [ ] Batch 1: Tenant isolation and authorization matrix
- [ ] Batch 2: IAM: auth, tokens, invitations, roles
- [ ] Batch 3: Commitments lifecycle, delivery, audit, outbox write
- [ ] Batch 4: Outbox dispatcher + event registry
- [ ] Batch 5: Celery tasks, task-name contracts, risk scan
- [ ] Batch 6: AI layer, connectors, SSRF, secrets
- [ ] Batch 7: Integrations/OAuth, MCP, SSE/Redis, ingestion API, idempotency, rate limiter
- [ ] Batch 8: Architecture, migration and contract guard tests
- [ ] Batch 9: End-to-end (real stack)
- [ ] Batch 10: Quality gates, CI/Makefile target, docs/TESTING.md

## 1. Goal and non-goals

**Goal:** protect the behaviours that would hurt most if they broke (tenant data leaks, auth bypass, lost or stuck events, wrong deadlines, leaked secrets), and verify the modular-monolith contracts so future changes stay safe.

**Non-goals:** chasing a coverage percentage, snapshot-testing everything, rewriting existing tests, changing anything in `src/`.

## 2. Test pyramid and targets

| Level | Definition | Needs | Marker | Target new tests |
|---|---|---|---|---|
| Unit | One function/class, no DB, no Redis, no network, no Celery broker | nothing | `@pytest.mark.unit` | ~70 |
| Integration | Real Postgres + real Redis, the real FastAPI app via httpx AsyncClient, Celery in eager mode or tasks called directly; external HTTP faked with respx/fake servers | Docker services | `@pytest.mark.integration` | ~100 |
| E2E | Full running stack (API + worker + beat + Postgres + Redis) via docker-compose, only the LLM / STT / third-party SaaS faked | docker-compose | `@pytest.mark.e2e` | ~8 |

Total target is roughly 180 new tests on top of the existing 66. **These numbers are starting estimates.** Batch 0 adjusts them against the audit. Existing coverage reduces the count. Never pad to hit a number, and never skip a CRITICAL item to save time.

Priority is risk-driven. CRITICAL items must be tested at the level named. Coverage targets are a result, not a goal: core >= 85%, modules service layers >= 80%, jobs >= 80%, ai >= 80%, connectors >= 75% line coverage, with branch coverage reported.

## 3. Hard rules

1. **Change only tests and test tooling.** Allowed: `backend/tests/**`, test fixtures/factories, `docker-compose.test.yml`, dev dependencies and pytest config in `pyproject.toml`, a Makefile/test script, `docs/`. **Do NOT change anything in `src/`.**
2. **A test that finds a real bug in `src/`:** do NOT fix the source. Mark the test `@pytest.mark.xfail(strict=True, reason="BUG-n: ...")`, log it in section 8 with file:line, expected vs actual behaviour, and continue.
3. Never delete, weaken or skip existing tests. Existing tests must pass unchanged.
4. Each test checks behaviour: DB state, response body, emitted events, audit rows, or error type. A test that only asserts `status_code == 200`, or that mocks the unit under test, does not count.
5. Deterministic: no `time.sleep`, use `freezegun` or injected clocks; no unseeded randomness; no dependence on test order; each test cleans up after itself (transaction rollback or truncate).
6. Real Postgres for anything touching the DB (row locking, `SKIP LOCKED`, UUID/JSONB, constraints). Do not use SQLite for new integration tests. If Docker is unavailable, STOP and tell me.
7. External services are faked at the HTTP boundary (`respx` or a local fake server), never by patching internal functions of the unit under test. Prefer importing from the module's public `__init__`. Patch targets must use the current paths.
8. Naming: `test_<unit>_<scenario>_<expected>`. Arrange / Act / Assert. Shared setup goes into fixtures/factories, not copy-paste. Parametrize matrices (modules x operations) instead of duplicating functions.
9. **Mutation sanity check:** per batch, pick 3 of the new tests, temporarily break the behaviour they cover in `src/`, confirm they fail, then restore with `git checkout -- src`. Before committing, `git diff --stat -- src` must be empty. Report the 3 checks.
10. Every new test must pass 3 consecutive runs. Run the full suite plus coverage at the end of each batch. Coverage may not drop.
11. One commit per batch: `test(batch-N): <summary>`. Tracker update goes in the same commit. Never force-push.
12. **STOP and ask me** when something is ambiguous, a batch would need a `src/` change, or the audit contradicts this plan.

## 4. Standard verification (after EVERY batch)

1. `pytest -q` (all levels that can run locally): zero failures; only the intended `xfail(strict)` allowed.
2. `pytest -m unit` runs with no Docker and no network.
3. New tests green 3 times in a row (`pytest <new files> --count=3` or a loop).
4. Coverage report before vs after (line + branch, per package).
5. `lint-imports` still passes and `python tools/snapshot_contracts.py --check` shows no diff.
6. `git diff --stat -- src` is empty.

## 5. Batches

### Batch 0: Reconcile + infrastructure (0 behaviour tests)
- Compare section 5 with `docs/TEST_AUDIT.md`. For every item already COVERED, mark it `(covered: <test>)` in this file and reduce the batch target. Record adjusted totals in section 8. Do not skip items the audit marks PARTIAL.
- Register markers `unit`, `integration`, `e2e` in pytest config with `--strict-markers`. Mark existing tests according to their REAL level (from the audit) without moving files.
- Provide a real Postgres + Redis for integration tests (testcontainers or `docker-compose.test.yml`). Create the schema by running Alembic `upgrade head`, not `create_all`, so the migrations are tested too.
- Add fixtures (in `tests/conftest.py` or `tests/fixtures/`): app client, DB session with per-test rollback or truncation, Redis flush per test, factories for user / workspace / membership / commitment / customer / integration, `auth_headers(user, workspace)` helper, a two-tenant fixture (`tenant_a`, `tenant_b` each with owner and member), frozen-clock fixture, fake LLM / STT / Slack / Jira / Linear / Google servers (respx routes), Celery eager helper.
- Add dev dependencies as needed: pytest-cov, pytest-randomly or pytest-repeat, freezegun, respx, testcontainers, factory-boy.
- Add 2-3 smoke tests proving the infrastructure works.

### Batch 1: Tenant isolation and authorization matrix (~30, integration, CRITICAL)
Parametrize over every tenant-owned resource and operation, using `tenant_a` and `tenant_b`:
- Resources: commitments, customers, delivery evidence, ingestion jobs, integrations, audit events, notifications/alerts, risk assessments, tickets, MCP tools, SSE stream.
- For each: A cannot list B's data (B's ids never appear in A's list), cannot GET / PATCH / DELETE B's item by id (404, not 403, so existence does not leak), cannot create an item referencing B's ids, and the DB row is unchanged afterwards.
- No auth / expired token / token for a workspace the user isn't a member of -> 401/403 on every router, driven from the FastAPI route table, so new routes are automatically covered. Document public routes in an explicit allow-list (health, auth, OAuth callback).
- Role checks inside a workspace, per the roles that exist in code.

### Batch 2: IAM (~18, mostly integration, a few unit)
- Register (duplicate email, weak or invalid input), login (wrong password, unknown user, no user-enumeration difference in response), `/auth/me` (covered: `test_jwt_token_rotation_and_replay_protection`).
- Refresh rotation: old refresh token becomes invalid after use (covered: `test_jwt_token_rotation_and_replay_protection`). **Replay of a used token revokes the session/family** (CRITICAL). Logout/revoke. `cleanup_expired_tokens` deletes only expired data.
- JWT: expired, malformed, wrong signature, wrong type (refresh used as access), tampered claims (unit).
- Google login: valid, invalid token, email-linking behaviour (fake Google endpoint).
- Invitations: create, accept, expired, reuse, wrong email, accept twice; workspace creation creates owner membership; default workspace creation on register.

### Batch 3: Commitments (~15, integration + a few unit)
- Create / update / confirm / delete / mark delivered / draft-update (covered: `test_draft_update_endpoint`) / candidate batch creation. Each valid state transition (covered: `test_commitment_status_transitions`), and every invalid transition rejected with the right error and no side effects.
- Pagination (limits, ordering, stable cursor/offset, empty page), filters, attention list.
- **Same-transaction outbox write:** the `outbox_events` row exists after success, and when the business write fails/rolls back there is NO outbox row (CRITICAL). Event payloads contain the expected ids and `workspace_id`.
- An audit event is written for each audited action (assert action, actor, workspace, entity id).
- Delivery verify (covered: `test_delivery_verification_flow`): evidence stored, commitment state updated, `COMMITMENT_DELIVERED` published on `ws:{workspace_id}:events`, cross-tenant evidence rejected.
- Customer metrics calculation (SLA health) with known fixtures.

### Batch 4: Outbox dispatcher + registry (~10, integration, CRITICAL)
- Registered task events: pending -> dispatched, correct task name/queue/kwargs sent (assert via fake `send_task`) (covered: `test_ingestion_event_routes_to_celery_task`, `test_notification_event_routes_to_celery_task`).
- No-op events (`commitment.created/updated/confirmed`): dispatched on the first poll, no retries, no error log (covered: `test_commitment_lifecycle_events_dispatch_cleanly`).
- Unknown event type: attempts increment, fails after 5, status `failed`, failure recorded (covered: `test_unknown_event_type_raises_value_error`). **Document current behaviour:** the dispatcher has no backoff and failing rows block the queue head. Add an `xfail(strict)` test asserting that a poison event must not delay later healthy events.
- Two dispatchers running concurrently on Postgres never dispatch the same row twice (`FOR UPDATE SKIP LOCKED`).
- Crash/exception between claim and mark: row is retried, not lost. Ordering by `created_at`. Batch size limit (50).
- Registry unit tests: duplicate registration, unknown lookup, kwargs builders for every registered event type (parametrized over the registry, so a new event without a test fails).

### Batch 5: Celery tasks and contracts (~14)
- **Task-name contract test:** the registered task names, queues, routes and beat schedule equal an explicit expected dict in the test: `jobs.tasks.process_transcript_ingestion`, `...process_audio_ingestion`, `...scan_commitment_deadlines`, `...cleanup_expired_tokens`, `...dispatch_notification_alert` (covered: `test_celery_task_definitions`, `test_celery_priority_queues_and_routing`) (unit).
- `scan_commitment_deadlines`: overdue, at-risk, on-track, already-delivered, boundary at exactly the deadline, timezone-aware vs naive dates, DST day, multiple workspaces isolated, idempotent on re-run (no duplicate alerts). Use freezegun.
- Ingestion tasks (with fake LLM/STT): success path creates candidate commitments and sets the job to completed; LLM failure sets the job to failed with an error message; retry behaviour; status transitions; large transcript.
- `dispatch_notification_alert` with fake Slack/email: success, connector error, integration not configured.
- `cleanup_expired_tokens`.

### Batch 6: AI, connectors, SSRF, secrets (~24, mostly unit with HTTP fakes)
- AI extractor: valid JSON (covered: `test_groq_successful_extraction`), malformed JSON (covered: `test_malformed_llm_response_fails_fast`), extra/missing fields, empty transcript (covered: `test_empty_transcript_handling`), very long transcript, timeout, rate-limit error (covered: `test_llm_api_failure_fails_fast`), retry then fallback provider, transcript containing prompt-injection text must not change the output schema (existing recovery tests reduce the count).
- Risk investigator: same failure modes.
- Each connector (Slack, Jira, Linear, Gmail, Calendar, Drive, Meet, Recall, STT, email, external MCP): success, 401/403 -> `ConnectorAuthenticationError`, 5xx/delivery failure -> `ConnectorDeliveryError`, missing config -> `ConnectorNotConfiguredError` (covered: `test_all_connectors_fail_fast_when_unconfigured`), timeout. Parametrize over the connector list.
- SSRF guard: private IPv4 ranges (covered: `test_blocked_ip_ranges`, `test_validate_no_ssrf_rejects_private_ips`), loopback, link-local/metadata `169.254.169.254`, IPv6 loopback and mapped addresses, redirect to a private IP, DNS rebinding (resolve to public then private), `file://`, `gopher://`, userinfo tricks, ports (covered: `test_validate_no_ssrf_rejects_empty_or_malformed`, `test_validate_no_ssrf_allows_public_ip`). (~6)
- Secrets: encrypt/decrypt roundtrip, tampered ciphertext rejected, wrong key rejected, key rotation if supported. Integration config is never returned by API responses (list/get/connect/test) and never appears in captured logs (use `caplog`).
- `google_auth` credential flow after the refactor: token refresh, expired token, revoked integration, workspace without integration.

### Batch 7: Integrations, MCP, realtime, ingestion API, resilience (~16, integration)
- Integrations router: connect/test/disconnect per provider with fakes (covered: `test_list_integrations_seeds_default_database_records`, `test_connect_and_disconnect_integration_persists`); reconnect; cross-tenant blocked. Google OAuth: authorize URL contains a state value, callback rejects a missing, wrong or replayed state (CSRF, CRITICAL), callback stores encrypted tokens, error from Google handled. `/operations/integrations/google/callback` path stays stable.
- MCP gateway: tool list, call each tool (list_commitments, get evidence, create commitment, create draft), auth required, invalid arguments, cross-tenant blocked.
- SSE: `/events/stream` and `/realtime/stream` both work, receive only the caller's workspace events, reject unauthenticated, `/test-publish` access control. Redis pub/sub and TTL behaviour.
- Ingestion API: transcript and audio upload validation (size, type, empty), job creation, job list isolation, outbox event written with the job.
- Idempotency: same key + same body returns the same response with no duplicate side effects (covered: `test_idempotency_retry_prevents_duplicate_commitments`, `test_idempotency_retry_customer_creation`); same key + different body conflicts; concurrent identical requests execute once. Rate limiter at the HTTP level: limit reached -> 429 with headers; per-tenant isolation; each algorithm boundary (covered: `test_sliding_window_in_memory_burst_and_recovery`, `test_token_bucket_in_memory_burst_and_refill`).
- Resilience: Redis down -> defined behaviour on key endpoints (document it); LLM down -> job failed, API still healthy; DB error -> 5xx without leaking internals.

### Batch 8: Architecture and migration guards (~6)
- A test that runs `lint-imports` and fails on violations.
- A test that runs the contract snapshot check (OpenAPI, task names, table metadata).
- Alembic on real Postgres: `upgrade head` from empty, `downgrade base`, `upgrade head` again, and no model/migration drift (`alembic check` equivalent).
- Route-coverage guard: every route in the FastAPI app is either referenced by a test or in an explicit, justified allow-list (fail on new untested routes).
- Every Celery task and every outbox event type has a test referencing it (parametrize from registries).

### Batch 9: End-to-end (~8, `docker-compose.test.yml`, marker `e2e`)
- Compose file: API + worker + beat + outbox dispatcher + Postgres + Redis + fake LLM/STT/Slack server. Document the one-command run in a Makefile target.
- Journeys:
  1. register -> workspace -> upload transcript -> dispatcher -> worker -> candidate commitments -> confirm -> deliver evidence -> verify -> SSE event received.
  2. Overdue commitment -> risk scan task -> alert delivered to the fake Slack.
  3. Audio ingestion happy path with the fake STT.
  4. Two tenants run the same journey in parallel; no data crosses.
  5. LLM down mid-ingestion -> job failed, system recovers when the LLM is back.
  6. Worker restart mid-task does not lose outbox events.
  7. Token refresh + replay detection across real HTTP.
  8. Integration connect (fake Slack) -> notification delivered.
- Keep e2e small and stable. Retries are allowed only for container startup, not for assertions.

### Batch 10: Quality gates
- Makefile (or script) targets: `test-unit`, `test-integration`, `test-e2e`, `test-all`, `coverage`, `check` (tests + `lint-imports` + snapshot check).
- Coverage thresholds per package in config (use the section 2 targets, adjusted to the achieved numbers minus a small buffer). Do not set thresholds above what is achieved.
- Add a CI workflow if I approve it (ask first; last time CI was skipped).
- Write `docs/TESTING.md`: the test pyramid, markers, how to run each level, fixtures and factories, how to add a test, how to write a new tenant-isolation test, what to do when a test finds a bug (xfail rule).
- Final report: tests before/after by level, coverage before/after per package, bugs found (section 8), flaky test check (3 runs, random order), runtime per level.

## 6. CRITICAL items (must be covered, at the stated level, before Batch 10 can close)

1. Cross-tenant read/update/delete is impossible for every module (Batch 1).
2. Refresh-token replay revokes the session (Batch 2).
3. Outbox row is written in the same transaction as the business change, and not on rollback (Batch 3).
4. Dispatcher never double-dispatches under concurrency, never loses a row, no-op events do not dead-letter (Batch 4).
5. Celery task names, queues and the beat schedule are pinned (Batch 5).
6. Deadline/SLA logic is correct at boundaries and timezones (Batch 5).
7. SSRF guard blocks private/metadata/redirect/rebinding cases (Batch 6).
8. Integration secrets never appear in responses or logs (Batch 6).
9. Google OAuth state/CSRF validation (Batch 7).
10. One full user journey works on the real stack (Batch 9).

## 7. Per-batch report template

```
Batch N: <title>
Tests added: unit X | integration Y | e2e Z   (existing 66 untouched: yes/no)
Verification: suite P passed / F failed / X xfail | 3-run stability OK | lint-imports OK | snapshot diff none | git diff src empty
Coverage line/branch before -> after (per package touched): ...
Mutation sanity checks (3): <test> breaks when <change> -> failed as expected
Bugs found (xfail strict): BUG-n ...
Items skipped or reduced because already covered: ...
Next batch: ...
```

## 8. Findings Log (agent appends here)

- Batch 0 adjusted targets: Unit ~55 (starting ~70, -15 covered), Integration ~78 (starting ~100, -22 covered), E2E ~8 (starting ~8). Total reconciled target: ~141 new tests (reduced from ~178 after reconciling 37 items covered or partially covered in audit).
- Bugs found in src/ (id, file:line, expected vs actual, test name): None in Batch 0. All 66 baseline tests and 3 new infrastructure smoke tests pass cleanly.
- Surprises, flaky tests, audit contradictions, open questions:
  1. PostgreSQL enum `role` values in baseline migration 0001 are lowercase strings (`admin`, `manager`, `member`, `viewer`), whereas SQLAlchemy's Python `Role` enum binding serialized `.name` ('ADMIN') by default. Aligned on the test side in `tests/conftest.py` via `values_callable=lambda x: [e.value for e in x]` without touching `src/`.
  2. Asyncpg connection pooling across pytest-asyncio function-scoped loops caused `RuntimeError: Task got Future attached to a different loop`. Resolved by setting `poolclass=NullPool` on `create_async_engine` in `tests/fixtures/database.py`.
  3. Alembic config `script_location = migrations` in `alembic.ini` resolved relative to CWD; pinned to `backend_dir / "migrations"` in `tests/fixtures/database.py`.
  4. Local Redis DB 0 contains 844 existing development keys; test Redis fixtures explicitly target isolated DB 15 (or port 6380) to prevent test flushes from polluting developer state.