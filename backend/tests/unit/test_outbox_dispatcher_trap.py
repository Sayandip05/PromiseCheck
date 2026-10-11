"""Tests verifying outbox event dispatcher routing and event registry.

Step 14: Event handler registry + notifications as subscriber.
"""

import uuid
from unittest.mock import MagicMock
import pytest

from core.outbox.registry import get_route
from jobs.outbox_dispatcher import _dispatch_to_celery


def test_commitment_lifecycle_events_dispatch_cleanly():
    """Verifies commitment lifecycle events (created, updated, confirmed) dispatch

    without raising unhandled ValueError, resolving the failure mode investigated in Step 13.
    """
    celery_app = MagicMock()
    for ev_type in ("commitment.created", "commitment.updated", "commitment.confirmed"):
        row = MagicMock()
        row.id = uuid.uuid4()
        row.event_type = ev_type
        row.payload = {"id": str(uuid.uuid4()), "title": "SOC2 Compliance", "customer": "Acme Corp"}

        # Dispatches cleanly via acknowledged no-op in outbox registry
        _dispatch_to_celery(celery_app, row)

    # Celery should not have received tasks for no-op commitment lifecycle events
    celery_app.send_task.assert_not_called()


def test_unknown_event_type_raises_value_error():
    """Verifies that truly unknown event types still raise ValueError and fail as expected."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "unregistered.random.event"
    row.payload = {}

    with pytest.raises(ValueError, match="No Celery handler for event_type 'unregistered.random.event'"):
        _dispatch_to_celery(celery_app, row)


def test_ingestion_event_routes_to_celery_task():
    """Verifies that ingestion outbox events properly route to Celery worker tasks."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "ingestion.transcript.process"
    row.payload = {
        "job_id": "job-123",
        "workspace_id": "ws-456",
        "transcript_text": "Customer commitment transcript text",
        "customer_name": "Acme Corp",
        "meeting_title": "Quarterly Review",
    }

    _dispatch_to_celery(celery_app, row)
    celery_app.send_task.assert_called_once_with(
        "jobs.tasks.process_transcript_ingestion",
        kwargs={
            "job_id": "job-123",
            "workspace_id": "ws-456",
            "transcript_text": "Customer commitment transcript text",
            "customer_name": "Acme Corp",
            "meeting_title": "Quarterly Review",
        },
        queue="ingestion",
    )


def test_notification_event_routes_to_celery_task():
    """Verifies that notification outbox events properly route to Celery worker tasks."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "notification.deadline.overdue"
    row.payload = {
        "commitment_id": "comm-789",
        "workspace_id": "ws-456",
        "title": "Security Review",
    }

    _dispatch_to_celery(celery_app, row)
    celery_app.send_task.assert_called_once_with(
        "jobs.tasks.dispatch_notification_alert",
        kwargs={
            "channel": "ws:ws-456:events",
            "event_type": "NOTIFICATION_DEADLINE_OVERDUE",
            "payload": {
                "commitment_id": "comm-789",
                "workspace_id": "ws-456",
                "title": "Security Review",
            },
        },
        queue="high_priority",
    )
