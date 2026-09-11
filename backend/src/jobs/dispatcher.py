"""Transactional outbox event dispatcher loop."""

import asyncio

from core.logging import get_logger

logger = get_logger("outbox_dispatcher")


async def run_dispatcher() -> None:
    """Poll the PostgreSQL outbox table and dispatch events to the Redis message broker."""
    logger.info("PromiseCheck Outbox Dispatcher started")
    while True:
        try:
            # Poll pending events from outbox table
            # Dispatch to Celery queue via celery_app
            # Mark dispatched in outbox transaction
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Outbox Dispatcher shutting down gracefully")
            break
        except Exception as exc:
            logger.error("Error in dispatcher polling cycle", exc_info=exc)
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
