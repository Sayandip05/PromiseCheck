"""IAM Celery background maintenance tasks."""

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select as sa_select
from sqlalchemy.orm import Session

from core.database import sync_engine
from core.logging import get_logger
from jobs.celery_app import celery_app
from modules.iam.models import RefreshToken
from modules.iam.models import Session as UserSession

logger = get_logger("modules.iam.tasks")


@celery_app.task(
    name="jobs.tasks.cleanup_expired_tokens",
    bind=True,
    queue="default",
    max_retries=1,
)
def cleanup_expired_tokens(self) -> dict[str, int]:
    """Nightly batched deletion of expired refresh tokens and sessions.

    Deletes in LIMIT=1000 batches with a 50 ms sleep between each batch to
    avoid a single large DELETE holding a row-level lock and triggering an
    autovacuum storm on high-volume tables.

    Rows are only removed after they have been expired for at least 24 hours
    (expires_at < NOW() - 1 day) so in-flight token verifications that may
    still be reading the row are never raced.
    """
    logger.info("[Celery Worker] Starting nightly expired token cleanup")
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    batch_size = 1000
    total_tokens = 0
    total_sessions = 0

    with Session(sync_engine) as session:
        # ── Refresh tokens ───────────────────────────────────────────────────
        while True:
            # Fetch a batch of IDs to delete (avoids large lock escalation)
            ids = session.execute(
                sa_select(RefreshToken.id)
                .where(RefreshToken.expires_at < cutoff)
                .limit(batch_size)
            ).scalars().all()
            if not ids:
                break
            result = session.execute(
                delete(RefreshToken).where(RefreshToken.id.in_(ids))
            )
            session.commit()
            total_tokens += result.rowcount
            if result.rowcount < batch_size:
                break
            time.sleep(0.05)  # 50 ms breathing room between batches

        # ── Sessions ─────────────────────────────────────────────────────────
        while True:
            ids = session.execute(
                sa_select(UserSession.id)
                .where(UserSession.expires_at < cutoff)
                .limit(batch_size)
            ).scalars().all()
            if not ids:
                break
            result = session.execute(
                delete(UserSession).where(UserSession.id.in_(ids))
            )
            session.commit()
            total_sessions += result.rowcount
            if result.rowcount < batch_size:
                break
            time.sleep(0.05)

    logger.info(
        f"[Celery Worker] Token cleanup complete: "
        f"{total_tokens} refresh tokens, {total_sessions} sessions deleted"
    )
    return {"refresh_tokens_deleted": total_tokens, "sessions_deleted": total_sessions}
