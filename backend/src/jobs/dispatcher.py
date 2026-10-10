"""Legacy compatibility module for Transactional Outbox Dispatcher.

FEATURE NOTICE:
This module has been renamed to `jobs.outbox_dispatcher` to provide unambiguous,
feature-based naming for engineers and clarify that it implements the Transactional Outbox pattern.

Please import directly from `jobs.outbox_dispatcher` in all new code.
"""

from jobs.outbox_dispatcher import (
    _BATCH_SIZE,
    _BUSY_SLEEP,
    _ERROR_SLEEP,
    _IDLE_SLEEP,
    _dispatch_to_celery,
    run_dispatcher,
)

__all__ = [
    "run_dispatcher",
    "_dispatch_to_celery",
    "_BATCH_SIZE",
    "_IDLE_SLEEP",
    "_BUSY_SLEEP",
    "_ERROR_SLEEP",
]

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_dispatcher())
