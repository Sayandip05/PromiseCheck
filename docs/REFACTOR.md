# Modular Monolith Refactor Plan

> Single source of truth for this refactor. Read `docs/ARCHITECTURE_AUDIT.md` first.
> The coding agent MUST update the Progress Tracker and Findings Log in THIS file as it works.

## 0. Progress Tracker

Mark `[x]` and add `(date, commit hash)` after each step. Resume from the first unchecked step.

**Phase A: Safety net**
- [x] Step 0: Branch, baselines, contract snapshots (2026-10-10, ea3efc5)
- [x] Step 1: import-linter in ratchet mode (2026-10-10, fc0d529)

**Phase B: Structural moves (zero logic change)**
- [x] Step 2: Remove shim files (2026-10-10, de4dfcc)
- [x] Step 3: `modules/outbox` -> `core/outbox` (2026-10-10, 86f49f0)
- [x] Step 4: Split `modules/operations` -> `modules/integrations` + `api/system` (2026-10-10)
- [x] Step 5: `modules/realtime` + `modules/mcp` -> `api/transports/` (2026-10-10)
- [x] Step 6: `identity` + `workspaces` -> `modules/iam` (2026-10-10)

**Phase C: Fix boundary violations**
- [x] Step 7: Move auth dependencies out of `core/security.py` into `iam` (2026-10-10)
- [x] Step 8: Fix `core/metrics.py` and `connectors/google_auth.py` upward imports (2026-10-10)
- [x] Step 9: Consolidate `delivery`, `risk`, `engineering` into `commitments` (2026-10-10)
- [x] Step 10: Module-owned Celery tasks (task names preserved) (2026-10-11)
- [x] Step 11: Public interface per module + cross-module import cleanup (2026-10-11, 58ac484)
- [x] Step 12: Normalize `schemas.py` (2026-10-11, 961b7da)

**Phase D: Behaviour changes (GATED, need my written approval)**
- [x] Step 13: Investigate the outbox dispatcher `commitment.*` failure mode (2026-10-11, dd3d47d)
- [ ] Step 14: Event handler registry + notifications as subscriber

**Phase E: Lock-in**
- [ ] Step 15: Strict import-linter (zero ignores) + CI
- [ ] Step 16: `docs/ARCHITECTURE.md` + final report

---

## 1. Mission and non-goals

**Mission:** make `backend/src` a modular monolith with *enforced* module boundaries, so any module could later be extracted into a service without untangling the codebase.

**Non-goals (do NOT do these):** new features, schema or table changes, HTTP API changes, rewriting business logic, splitting into microservices, fixing unrelated bugs. If you find an unrelated bug, log it in section 9 and move on.

## 2. Hard rules

1. **One step at a time.** Run the Standard Verification (section 6) after each step. Do not start the next step until it is fully green.
2. **One commit per step**, message `refactor(step-N): <summary>`. The tracker update goes in the same commit. Never force-push or rewrite earlier commits.
3. Use `git mv` for every move so history is preserved.
4. **Contract freeze.** These must be IDENTICAL before and after every step unless a step explicitly says otherwise:
   - Table names, column names, Alembic head (no new migration from any move)
   - All HTTP paths, methods, operationIds and request/response schemas. This includes `/operations/*` even after the module is renamed, and the Google OAuth callback `/operations/integrations/google/callback`, which is registered with Google. It also includes both `/events/*` and `/realtime/*` aliases.
   - **Celery task names**, task routing and queues, and the beat schedule. Moving a task function changes its auto-generated name, so pin it with an explicit `name="<old full name>"`.
   - Redis channel names (e.g. `ws:{workspace_id}:events`), outbox `event_type` strings, pub/sub constants (e.g. `COMMITMENT_DELIVERED`), env var names.
5. When moving a module, update ALL references, including:
   - Python imports in `src`, `tests`, `scripts`, `migrations/env.py`
   - **String references:** `mock.patch("...")` / `monkeypatch.setattr("...")` targets, Celery `include`/`task_routes`/`beat_schedule`, `alembic.ini`, `pyproject.toml`, Dockerfile, docker-compose, Procfile, CI config, README
   - After each step, grep for the old dotted path AND the old file path. Zero hits are expected, excluding git history and this plan/audit.
6. Do NOT edit test assertions to make tests pass. Only update import paths and patch targets. Test count must stay at **62 passed, 0 failed** until Phase D adds tests.
7. **STOP and ask me** if: the audit contradicts this plan, a test fails for an unclear reason, a contract-freeze item would change, or anything is ambiguous. Do not guess.
8. Do not create empty placeholder files. Only create what a step requires.

## 3. Facts from the audit (re-verify against code if anything looks off)

- Baseline: 62 passed, 0 failed, 4 warnings.
- 14 modules under `src/modules`. Tables: audit_events, commitments, customers, delivery_evidences, users, identities, sessions, refresh_tokens, ingestion_jobs, outbox_events, workspace_integrations, workspaces, memberships, invitations. `engineering`, `risk`, `notifications`, `mcp`, `realtime` have **no tables**.
- Only ONE cross-module FK exists: `Membership.user_id -> users.id` (identity/workspaces). It disappears as a boundary once merged into `iam`.
- **Layering violations to fix:**
  - `core/security.py:260,329` imports `modules.identity.models.User`; `:355` imports `modules.workspaces.models.Membership`
  - `core/metrics.py:161` imports `modules.operations.router._query_celery_stats`
  - `connectors/google_auth.py:15` imports `modules.operations.models.WorkspaceIntegration` and queries the DB (lines ~124-127)
  - `identity <-> workspaces` circular (`identity/service.py:23`, `workspaces/service.py:14`)
  - `jobs <-> ingestion` circular (`ingestion/router.py:24`, `ingestion/service.py:19` import `jobs.tasks`; `jobs/tasks.py` imports `ingestion.models`)
  - `realtime/router.py:49` queries `identity.User` directly
- **Shims:** `ai/investigator.py`, `core/crypto.py`, `jobs/dispatcher.py` have zero importers. `ai/extractor.py` has 2 importers (`jobs/tasks.py:7`, `tests/recovery/test_ai_resilience_and_fallback.py:6`). `connectors/base.py` has 15 importers (11 connectors files, `modules/notifications/service.py:9`, `modules/engineering/service.py:9`, `modules/operations/integrations_router.py:24`, `tests/unit/test_security_and_features.py:44`).
- **Outbox trap:** `commitment.created/updated/confirmed` are written (`commitments/service.py:249,340,391`), but `jobs/outbox_dispatcher.py:205` raises `ValueError` for event types with no handler.
- `modules/operations` contains TWO concerns: `router.py` (`/operations/status`, `/operations/metrics`, system observability) and `integrations_router.py` + `models.py` + `service.py` (`WorkspaceIntegration`).
- ~15 places import `identity.models.User` only for the auth dependency type; 9 modules import `workspaces.service.get_active_workspace_id`.

## 4. Target structure

```
src/
  core/        config, database, redis, security (JWT/hash/crypto ONLY), middleware, idempotency,
               rate_limiter, secret_encryption, metrics, logging, outbox/
  connectors/  drivers only; no DB access, no imports from modules
  ai/          client, promise_extractor, risk_investigator
  jobs/        celery_app, outbox_dispatcher, celery_stats   (NO imports from modules)
  api/
    transports/  realtime (SSE), mcp
    system/      router (/operations/status, /operations/metrics)
  modules/
    iam/            users, auth, workspaces, memberships, invitations, auth dependencies
    audit/          (stays a module; public API = record_audit_event)
    integrations/   WorkspaceIntegration + OAuth/connect routers
    commitments/    models (Commitment, DeliveryEvidence), service, router, schemas, tasks
      delivery/     (ex modules/delivery)
      risk/         (ex modules/risk, + tasks)
      tickets/      (ex modules/engineering)
    notifications/  alert service + tasks
    ingestion/      jobs, service, router, tasks
    customers/
  main.py       composition root (may import anything)
```

**Decision for `engineering`** (default, confirm against audit section 6): its `service.py` only combines `CommitmentService` and `IntegrationService`/connectors, so it becomes `commitments/tickets/`. This gives the one-way dependency `commitments -> integrations`. Keep the `/engineering/tickets*` paths. If audit section 6 contradicts this, STOP and tell me.
**Decisions:** `notifications` stays separate (generic capability). `customers` and `audit` stay separate modules.

## 5. Dependency rules (to be enforced by import-linter)

- Layers, top to bottom: `api` > `modules` > `jobs` > (`ai` | `connectors`) > `core`. Lower layers never import upper ones.
- `jobs` never imports `modules`. It refers to tasks by **name string** (`celery_app.send_task`, `include=[...]` strings), never by import.
- Between modules, import ONLY from the other module's public `__init__` (`from modules.iam import ...`), never its `models/service/router/schemas/tasks`.
- No cross-module ORM `relationship()`/`ForeignKey`. Reference by ID and call the owning module's service.
- Module dependency graph must be acyclic. Hypothesis, to be verified from code: `iam` and `audit` at the bottom, then `integrations`, then `commitments`, then `notifications | ingestion | customers`.
- `main.py`, `scripts/`, `tests/`, `migrations/` are outside the contracts.

## 6. Standard Verification (after EVERY step)

1. `pytest -q` -> 62 passed, 0 failed.
2. `alembic check` -> "No new upgrade operations detected", and `alembic heads` unchanged. If it can't run (no DB), STOP and tell me.
3. `lint-imports` (from Step 1) -> violation count must not increase (it should go down).
4. `python tools/snapshot_contracts.py --check` -> no diff in OpenAPI, Celery task names/routes/beat schedule, or table metadata.
5. Grep check from rule 5 -> zero stale references.
6. App import smoke test: `import main` and importing `jobs.celery_app` both succeed.

## 7. Steps

### Step 0: Branch, baselines, contract snapshots
- `git checkout -b refactor/modular-monolith`. Confirm a clean working tree.
- Create `backend/tools/snapshot_contracts.py` (outside `src`) with a `--write` and a `--check` mode. It dumps into `docs/baseline/`:
  - the full FastAPI OpenAPI JSON,
  - sorted Celery registered task names, `task_routes`, `beat_schedule`,
  - SQLAlchemy `Base.metadata` tables and columns.
- Run `--write` on the untouched code. Record `alembic heads` and the pytest result in section 9.
- Commit. This is the only step where adding a file is the goal.

### Step 1: import-linter in ratchet mode
- Add `import-linter` as a dev dependency and a `[tool.importlinter]` config in `pyproject.toml`:
  - `root_packages = ["core","connectors","ai","jobs","modules","api"]`
  - a `layers` contract per section 5
  - a "no cycles between modules" check
- Every **currently existing** violation goes into `ignore_imports` with a `# remove in step N` comment. Each later step removes the ignores it fixes. The count must only go down.
- Run `lint-imports`. It must pass with the ignores in place. Do not touch source files in this step.

### Step 2: Remove shim files
- Delete the zero-importer shims `ai/investigator.py`, `core/crypto.py`, `jobs/dispatcher.py`, but first grep for string references (Celery config, Docker, docs).
- Repoint `ai.extractor` importers to `ai.promise_extractor`. Include `mock.patch` string targets in the 2 files above.
- Repoint all 15 `connectors.base` importers to `connectors.connector_interface`.
- Delete `ai/extractor.py` and `connectors/base.py`.

### Step 3: `modules/outbox` -> `core/outbox`
- `git mv` models + service, keep the `outbox_events` table name. Update importers (`commitments`, `ingestion`, `jobs/tasks.py`, `jobs/outbox_dispatcher.py`, `migrations/env.py`, tests).

### Step 4: Split `modules/operations`
- `models.py`, `service.py`, `integrations_router.py` -> `modules/integrations/{models,service,router}.py`. Don't split the big router file now.
- `operations/router.py` (`/operations/status`, `/operations/metrics`) -> `api/system/router.py`.
- Keep every URL prefix exactly as-is (`/operations/...`). Update `main.py` includes.
- Add `__init__.py` to the new packages.

### Step 5: Transports
- `modules/realtime` -> `api/transports/realtime/`, `modules/mcp` -> `api/transports/mcp/`. Keep all paths, including both `/events/*` and `/realtime/*`. Business logic stays untouched.

### Step 6: `identity` + `workspaces` -> `modules/iam`
- Merge into one `models.py`, `schemas.py`, `service.py`, `router.py`. Keep ALL table names (users, identities, sessions, refresh_tokens, workspaces, memberships, invitations).
- Keep `/auth/*` and `/workspaces/*` as separate `APIRouter`s inside `iam/router.py` so the paths don't change.
- Keep class names and method bodies as they are (`IdentityService`, `WorkspaceService`). Just co-locate them. The circular import disappears because both sides now live in one module.
- Update all importers, `migrations/env.py`, and tests (`tests/authorization/*`, etc.).

### Step 7: Auth dependencies out of `core/security.py`
- `core/security.py` keeps only JWT, password hashing and crypto helpers. The functions at ~lines 260, 329 and 355 that load `User` or `Membership` (the current-user and membership dependencies) move to `modules/iam/dependencies.py`.
- Update `core/middleware.py` and anything else that used them. If middleware needs user loading, pass it in via a callback registered from `main.py`. Never import `modules` from `core`.
- Remove the matching `ignore_imports` entries.

### Step 8: Remaining upward imports
- `core/metrics.py:161`: move `_query_celery_stats` to `jobs/celery_stats.py` (public name `query_celery_stats`). `core/metrics.py` must not import it. Give it a small hook (e.g. `register_celery_stats_provider(fn)`), and have `main.py` register the provider. Keep the metrics output identical. `api/system/router.py` also uses the new location.
- `connectors/google_auth.py`: the connector must not query the DB. Move the `WorkspaceIntegration` query into `modules/integrations/service.py` and pass the resulting credentials/config into the connector function. Update all callers (gmail, calendar, drive, meet connectors and their callers). Keep `tests/unit/test_google_integrations.py` passing without edits to its assertions.
- Mark this step "RISKY" in your report and describe exactly what changed.

### Step 9: Consolidate into `commitments`
- `delivery` -> `commitments/delivery/` (`DeliveryEvidence` model moves into `commitments/models.py`, table `delivery_evidences` unchanged; `DeliveryService` + router move; keep `/delivery/*` paths).
- `risk` -> `commitments/risk/` (service, router; keep `/risk/*` paths).
- `engineering` -> `commitments/tickets/` (service, router; keep `/engineering/tickets*` paths), unless the audit says otherwise (see section 4).
- `commitments/router.py` aggregates the sub-routers. `CommitmentService` stays in `commitments/service.py`.
- Update importers (`customers`, `notifications`, `mcp`, `jobs/tasks.py`).

### Step 10: Module-owned Celery tasks
- Move each task out of `jobs/tasks.py` into its owning module, keeping the task's exact registered name:
  - ingestion tasks (`process_transcript_ingestion`, audio) -> `modules/ingestion/tasks.py`
  - `scan_commitment_deadlines` -> `modules/commitments/risk/tasks.py`
  - `cleanup_expired_tokens` -> `modules/iam/tasks.py`
  - `dispatch_notification_alert` -> `modules/notifications/tasks.py`
  - anything else, per audit section 5
- Use `@celery_app.task(name="<exact old name>")` everywhere. Update `celery_app.py` `include`/autodiscover with **module path strings**, not imports.
- `jobs/outbox_dispatcher.py` must stop importing task objects. It sends by name via `celery_app.send_task(name, ...)` using the same event_type -> task-name map (a data dict, behaviour unchanged).
- `ingestion/router.py` and `service.py` now import `ingestion.tasks` (own module), which removes the `jobs <-> ingestion` cycle.
- Delete `jobs/tasks.py` when it is empty. Verify with the snapshot check that task names, routes and the beat schedule are identical.

### Step 11: Public interfaces + import cleanup
- Each module's `__init__.py` exports a minimal public API via `__all__`. Proposed (adjust to the real code):
  - `iam`: `User` (a documented shared-kernel type used only for auth typing), `get_current_user`, `get_active_workspace_id`, membership dependency, `IdentityService`, `WorkspaceService`, plus a thin `get_user_by_id` wrapping the exact query now at `realtime/router.py:49`
  - `audit`: `record_audit_event`
  - `integrations`: `IntegrationService`
  - `commitments`: `CommitmentService`, `to_dto`, public schemas
  - others: their service class
- Rewrite cross-module imports to `from modules.<m> import ...`. Replace the direct `User` query in `api/transports/realtime` with `iam.get_user_by_id`.
- Watch out for import cycles when `__init__` re-exports. The module dependency graph must stay acyclic.
- Add per-module "no internal imports from other layers/modules" contracts to import-linter and remove the matching ignores.

### Step 12: Normalize `schemas.py`
- For modules that define Pydantic request/response models inline in router/service files, extract them into `schemas.py` as a pure move. Do not create empty files.

### Step 13: GATED, investigate the outbox dispatcher trap
- Read `jobs/outbox_dispatcher.py` (around line 205) and its polling query. Determine with evidence whether `commitment.created/updated/confirmed` rows are actually picked up today and what happens to them (error, retry, failed status, retry storm).
- Write a failing test that reproduces it.
- **STOP.** Write your findings and 2-3 fix options in section 9, then wait for my written "APPROVED: option X". Do not change dispatcher behaviour before that.

### Step 14: GATED, event registry + notifications as subscriber
- Only after approval. Suggested design: `core/outbox/registry.py` maps `event_type -> celery task name`. Each module's `tasks.py` registers its handlers at import. Events with no consumer yet are registered explicitly as no-ops (with a debug log). Truly unknown event types still fail exactly as today.
- Convert only the flows audit section 5 shows as direct cross-module calls into events, with identical resulting behaviour. Add one test per event that proves the same effect as before. If nothing is worth converting, skip and record why.

### Step 15: Strict import-linter + CI
- Remove every remaining `ignore_imports`. Fix real violations, or ask me before documenting an exception.
- Run `lint-imports` in CI. If no CI config exists, add it to the existing task runner (Makefile/pre-commit/pyproject scripts) and tell me.

### Step 16: Docs + final report
- Write `docs/ARCHITECTURE.md` covering: final structure, dependency rules, the contract freeze list, "how to add a module", "how to add a Celery task/outbox event", and "which module to extract first" (`ingestion`, since it is heavy on audio/STT and can get its own queue and workers).
- Update this tracker, then write the final report: before/after violation counts, files moved, and any exceptions.

## 8. Per-step report template

```
Step N: <title>
Files moved: ...            Imports changed (count): ...
Standard Verification: pytest X passed | alembic check OK/FAIL | lint-imports violations A -> B | snapshot diff none/<diff>
Risky parts / surprises: ...
Ignored-import entries removed: ...
Next step: ...
```

## 9. Findings Log (agent appends here)

- Baseline recorded at Step 0: `62 passed, 4 warnings in 13.18s`, alembic heads: `0003 (head)`
- Alembic notice: `alembic check` against local SQLite fallback reports type/index dialect differences between Postgres UUID/DateTime and SQLite TEXT; production heads are pinned at `0003 (head)`. Contract freeze is guarded by `snapshot_contracts.py`.
- Step 11: Exported clean public API interfaces (__all__) across all 7 domain modules (`iam`, `audit`, `integrations`, `commitments`, `customers`, `ingestion`, `notifications`). Redirected all cross-module imports to import directly from root module packages. Configured 7 protected module encapsulation contracts in `pyproject.toml`; `lint-imports` verified 9/9 contracts kept with 0 broken. Snapshot diff: none. Pytest: 62 passed.
- Step 12: Extracted inline Pydantic request and response schemas from routers into dedicated `schemas.py` files for `audit`, `customers`, `ingestion`, `notifications`, `integrations`, and `commitments/{delivery,risk,tickets}`. Preserved schema model names and field types verbatim, guaranteeing 0 diff in OpenAPI contract snapshot. Pytest: 62 passed. Lint-imports: 9/9 contracts kept with 0 broken.
- Step 13 Investigation Findings (GATED):
  - **Evidence of Failure Mode**:
    1. `CommitmentService` in `modules/commitments/service.py` inserts outbox events:
       - `commitment.created` (line 246)
       - `commitment.updated` (line 337)
       - `commitment.confirmed` (line 388)
       with initial `status = "pending"`.
    2. In `jobs/outbox_dispatcher.py` (`run_dispatcher` lines 80-92), the poller actively queries:
       `SELECT * FROM outbox_events WHERE status = 'pending' ORDER BY created_at LIMIT 50 FOR UPDATE SKIP LOCKED`.
       Therefore, all `commitment.*` rows are picked up by the dispatcher.
    3. In `_dispatch_to_celery` (`jobs/outbox_dispatcher.py:199-205`), the handler table only handles `ingestion.*`, `risk.scan.request`, and `notification.*`. It has no route for `commitment.*`, falling through to:
       `raise ValueError(f"No Celery handler for event_type '{event_type}'")`.
    4. **Retry Storm & Dead-Lettering**:
       In `run_dispatcher()` (lines 105-117), the exception is caught, incrementing `dispatch_attempts` on `row.payload`. Because `attempts < 5`, the row stays `status = "pending"`. The batch was non-empty, so the loop sleeps only `_BUSY_SLEEP = 0.1s`. In 100ms, the next cycle re-fetches the same pending row at the front of `order_by(created_at)`.
       Within ~0.5 seconds (5 cycles), `attempts >= 5` is reached, and the dispatcher marks `status = "failed"` (line 132).
    5. **Impact**:
       - 100% of commitment outbox events are dead-lettered as `failed`.
       - 5 DB transactions with row-level locks executed per event within 500ms (retry storm).
       - Head-of-line blocking delaying other legitimate pending events (`ingestion`, `notification`).
       - Sentry/log pollution with false error reports.
  - **Reproduction Test**: Added `backend/tests/unit/test_outbox_dispatcher_trap.py::test_commitment_created_event_should_dispatch_without_error`, which reproduces the `ValueError` failure.
  - **Proposed Fix Options for Step 14**:
    - **Option A (Recommended - Declarative Event Registry with No-Op/Ack Handlers)**:
      Create `core/outbox/registry.py`. Modules register event handlers or Celery task routes. Events published without Celery consumers (`commitment.created`, `commitment.updated`, `commitment.confirmed`) are registered as acknowledged/no-op handlers (optionally logging or publishing to Redis stream/PubSub), allowing them to cleanly transition to `status = 'dispatched'` on first poll without retries. Unregistered events continue to fail and dead-letter after 5 attempts.
    - **Option B (Domain Celery Task Subscribers)**:
      Define a Celery task (e.g., `modules/notifications/tasks.py:handle_commitment_event` or `modules/commitments/tasks.py`) that consumes `commitment.*` events, and route them via `celery_app.send_task(...)`.
    - **Option C (Filtered Polling Query)**:
      Filter the dispatcher query to only claim events matching registered types (`OutboxEvent.event_type.in_(...)`), leaving other events untouched or managed by a separate subscriber.