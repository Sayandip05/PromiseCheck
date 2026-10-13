# Testing Guide

This document describes the testing architecture, standards, test pyramid, tooling, and developer workflows for PromiseCheck.

---

## 1. Test Pyramid & Design Philosophy

PromiseCheck follows a risk-driven test pyramid. Tests verify actual business behavior, security boundaries, and data integrity rather than superficial HTTP status codes.

```
       / \
      /   \      E2E Journeys (~9 tests)
     / E2E \     - Full multi-step user workflows
    /-------\    - Real DB, Redis, Celery, outbox dispatch
   /         \   
  / Integrat. \  Integration Tests (~155 tests)
 /             \ - Real PostgreSQL (transactions/locking/JSONB)
/---------------\- Real Redis, FastAPI TestClient, outbox transactions
/                 \
/      Unit         \ Unit Tests (~160 tests)
/                    \- Fast, in-memory, pure logic, no DB/network
-----------------------
```

### Pytest Markers

All test functions or modules are marked with explicit pytest markers configured in `pyproject.toml`:

| Marker | Purpose | Environment Dependencies | Typical Execution Time |
|---|---|---|---|
| `@pytest.mark.unit` | Pure functions, domain services, Pydantic schemas, cryptographic logic, SSRF IP parsers | None (isolated, in-memory) | < 3 seconds |
| `@pytest.mark.integration` | API routes, database repositories, outbox transactional writes, Celery tasks, OAuth flows | Real PostgreSQL + Redis | ~35 seconds |
| `@pytest.mark.e2e` | Complete end-to-end user journeys spanning ingestion, commitments, alerts, and auth replay | Real PostgreSQL + Redis + full stack | ~6 seconds |

---

## 2. Quick Command Reference

A root [`Makefile`](file:///Users/sayandip/Desktop/development/PromiseCheck/Makefile) provides standard targets for local development and quality gates:

```bash
# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run end-to-end journeys only
make test-e2e

# Run the entire test suite (324 tests)
make test-all

# Run full test suite with code coverage report
make coverage

# Verify modular-monolith boundary contracts (import-linter)
make lint-imports

# Verify contract snapshots against baseline (OpenAPI, Celery tasks, DB tables)
make contracts-check

# Run full quality gate (lint-imports + snapshot freeze + all tests)
make check
```

---

## 3. Fixtures & Factories Guide

### Database Fixtures

- **`postgres_manager`** (`tests/fixtures/database.py`):
  Manages an ephemeral test PostgreSQL instance (via testcontainers or dedicated local test container). Runs Alembic migrations (`upgrade head`) to maintain an up-to-date PostgreSQL schema.
- **`db_session`** (`tests/fixtures/database.py`):
  Yields an isolated `AsyncSession` bound to the test database. Automatically rolls back or cleans up after each test to ensure test isolation.

### Client Fixtures

- **`app_client`**:
  A FastAPI/Starlette `TestClient` initialized with database dependency overrides (`get_db` bound to the test PostgreSQL session).
  *Note:* Always pass unique IP headers (e.g. `headers={"X-Forwarded-For": f"198.51.100.{unique_id}"}`) when invoking rate-limited endpoints like `/api/v1/auth/login` or `/api/v1/auth/register` to prevent cross-test rate limiter collisions.

### Factories (`tests/fixtures/factories.py`)

Always use `factory-boy` model factories instead of raw dictionaries or manual DB inserts:

- **`UserFactory`**: Generates a `User` model with realistic fake names, hashed passwords (`SecurePassword123!`), and unique emails.
- **`WorkspaceFactory`**: Generates a `Workspace` model with unique slugs.
- **`CommitmentFactory`**: Generates a `Commitment` model associated with a workspace, user, and customer.
- **`MembershipFactory`**: Generates workspace membership records (`Role.ADMIN`, `Role.MEMBER`, `Role.VIEWER`).
- **`IngestionJobFactory`**: Generates an `IngestionJob` record with realistic transcription metadata.

---

## 4. How to Add a New Test

### Adding a Unit Test

Save under `backend/tests/unit/test_<module_or_feature>.py`:

```python
import pytest
from core.secret_encryption import encrypt_secret, decrypt_secret

pytestmark = pytest.mark.unit


def test_encryption_roundtrip():
    # Arrange
    plaintext = "super_secret_api_token"

    # Act
    encrypted = encrypt_secret(plaintext)
    decrypted = decrypt_secret(encrypted)

    # Assert
    assert decrypted == plaintext
    assert encrypted != plaintext
```

### Adding an Integration Test

Save under `backend/tests/integration/test_<feature>_lifecycle.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.fixtures.factories import UserFactory, WorkspaceFactory

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_resource_lifecycle(app_client: TestClient, db_session: AsyncSession):
    # Arrange
    user = UserFactory()
    workspace = WorkspaceFactory()
    db_session.add_all([user, workspace])
    await db_session.commit()

    # Act
    response = app_client.post(
        f"/api/v1/workspaces/{workspace.id}/items",
        json={"name": "New Item"},
    )

    # Assert
    assert response.status_code == 201
    assert response.json()["name"] == "New Item"
```

---

## 5. How to Write a Tenant-Isolation Test

Tenant isolation is a **CRITICAL** system requirement. Every resource access must verify that Tenant B cannot access, mutate, or delete Tenant A's data.

### Standard Tenant Isolation Pattern:

```python
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from modules.iam.models import Role, Membership
from tests.fixtures.factories import UserFactory, WorkspaceFactory, CommitmentFactory

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_cross_tenant_isolation_guard(app_client: TestClient, db_session: AsyncSession):
    # 1. Arrange: Create Tenant A and Tenant B
    user_a = UserFactory()
    ws_a = WorkspaceFactory()
    user_b = UserFactory()
    ws_b = WorkspaceFactory()
    db_session.add_all([user_a, ws_a, user_b, ws_b])
    db_session.add(Membership(workspace_id=ws_a.id, user_id=user_a.id, role=Role.ADMIN))
    db_session.add(Membership(workspace_id=ws_b.id, user_id=user_b.id, role=Role.ADMIN))
    await db_session.commit()

    # 2. Create resource in Tenant A
    resource_a = CommitmentFactory(workspace_id=ws_a.id)
    db_session.add(resource_a)
    await db_session.commit()

    # 3. Act: Tenant B attempts to read/modify Tenant A's resource
    # Using Tenant B's authentication / workspace context:
    headers_b = {"X-Workspace-Id": str(ws_b.id)}
    res = app_client.get(f"/api/v1/commitments/{resource_a.id}", headers=headers_b)

    # 4. Assert: Must return 404 Not Found (or 403 Forbidden) and NEVER reveal Tenant A data
    assert res.status_code in (404, 403), f"Leaked resource across tenants: {res.status_code}"
```

---

## 6. Strict Xfail Bug Logging Policy (`xfail(strict=True)`)

When writing tests for existing code:
1. **Zero modifications to `backend/src/`**: Do NOT edit production application code to fix bugs during test authoring.
2. If a test exposes a real bug in `backend/src/`:
   - Mark the test with `@pytest.mark.xfail(strict=True, reason="BUG-n: <short description>")`.
   - Log the bug in Section 8 of [`docs/TEST_PLAN.md`](file:///Users/sayandip/Desktop/development/PromiseCheck/docs/TEST_PLAN.md) detailing:
     - Bug ID and title
     - File path and line numbers
     - Expected behavior vs. actual behavior
     - Root cause analysis
3. **Why `strict=True`?**
   If the bug is accidentally altered or when an engineer later fixes the underlying code in `src/`, pytest will report an **`XPASS` (unexpected pass)** and fail the test run. This immediately signals that the bug has been resolved and the `@pytest.mark.xfail` decorator should be removed.

---

## 7. Architecture Boundary & Contract Guards

PromiseCheck enforces strict modular-monolith boundaries verified via `make check`:

1. **`import-linter` Boundary Contracts** (`pyproject.toml`):
   - Layered architecture: `api` -> `modules` -> `jobs` -> `connectors | ai` -> `core`.
   - Acyclic modules: no circular dependencies between siblings in `modules/`.
   - Internal module encapsulation: private submodules (e.g. `modules.iam.models`) cannot be directly imported by external modules without going through the module's public `__init__.py`.
2. **Snapshot Freeze** (`backend/tools/snapshot_contracts.py`):
   - Automatically compares current FastAPI OpenAPI endpoints, Celery task names, and SQLAlchemy table schemas against golden baselines in `docs/baseline/`.
   - Any uncataloged route addition or accidental schema drift will immediately trigger a diff and break `make check`.
