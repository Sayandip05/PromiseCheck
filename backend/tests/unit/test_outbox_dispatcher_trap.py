"""Tests reproducing the outbox dispatcher failure mode for commitment.* events.

Part of Step 13 (Gated investigation).
"""

import uuid
from unittest.mock import MagicMock
import pytest

from jobs.outbox_dispatcher import _dispatch_to_celery


def test_commitment_created_event_should_dispatch_without_error():
    """Failing test reproducing the outbox dispatcher failure mode for commitment.created.

    Currently, CommitmentService emits 'commitment.created', 'commitment.updated', and
    'commitment.confirmed' outbox events. However, _dispatch_to_celery has no route for
    'commitment.*', raising ValueError("No Celery handler for event_type 'commitment.created'").

    This test asserts that commitment.created can be dispatched cleanly, which FAILS
    against current code and will pass once the event registry / handler is introduced in Step 14.
    """
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "commitment.created"
    row.payload = {"id": str(uuid.uuid4()), "title": "SOC2 Type II", "customer": "Acme Corp"}

    # FAILS: Raises ValueError("No Celery handler for event_type 'commitment.created'")
    _dispatch_to_celery(celery_app, row)
