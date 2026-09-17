"""PromiseCheck FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

__version__ = "0.1.0"
from core.config import settings
from core.database import Base, async_engine, check_database_health
import modules.identity.models  # noqa: F401
import modules.workspaces.models  # noqa: F401
import modules.commitments.models  # noqa: F401
import modules.customers.models  # noqa: F401
import modules.ingestion.models  # noqa: F401
import modules.delivery.models  # noqa: F401
from core.logging import get_logger, setup_logging
from jobs.celery_app import check_redis_health

# Business module routers
from modules.audit.router import router as audit_router
from modules.commitments.router import router as commitments_router
from modules.customers.router import router as customers_router
from modules.delivery.router import router as delivery_router
from modules.engineering.router import router as engineering_router
from modules.identity.router import router as identity_router
from modules.ingestion.router import router as ingestion_router
from modules.notifications.router import router as notifications_router
from modules.operations.router import router as operations_router
from modules.operations.integrations_router import router as integrations_router
from modules.risk.router import router as risk_router
from modules.workspaces.router import router as workspaces_router
from modules.mcp.server import mcp_router
from modules.realtime.router import router as realtime_router

logger = get_logger("promisecheck.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Graceful startup and shutdown lifecycle management (Twelve-Factor Factor IX)."""
    setup_logging()
    logger.info(f"Starting PromiseCheck v{__version__} in '{settings.APP_ENV}' mode")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning(f"Database schema auto-init warning: {exc}")
    yield
    logger.info("Initiating graceful shutdown...")
    await async_engine.dispose()
    logger.info("Database connection pool disposed. Shutdown complete.")


app = FastAPI(
    title="PromiseCheck API",
    description="Customer commitments, connected from conversation to verified delivery.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

from core.middleware import register_middleware

# Register defense-in-depth security headers, rate limiting, and request tracing
register_middleware(app)

# Dynamic CORS Middleware from Twelve-Factor external configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["Health"])
async def liveness_probe() -> dict[str, str]:
    """Liveness probe: returns 200 OK immediately if the web process is alive."""
    return {"status": "ok", "service": "promisecheck"}


@app.get("/api/v1/health", tags=["Health"])
async def readiness_probe(response: Response) -> dict:
    """Readiness probe: actively checks database and Redis connectivity.

    Returns HTTP 200 if all services are reachable, or HTTP 503 if any dependency is degraded.
    """
    db_ok, db_msg = await check_database_health()
    redis_ok, redis_msg = await check_redis_health()

    is_healthy = db_ok and redis_ok
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": __version__,
        "checks": {
            "database": db_msg,
            "redis": redis_msg,
        },
    }


# Mount all feature module routers under /api/v1
app.include_router(identity_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(commitments_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(engineering_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(delivery_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(realtime_router, prefix="/api/v1")


def run() -> None:
    """Console script entrypoint."""
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)


if __name__ == "__main__":
    run()
