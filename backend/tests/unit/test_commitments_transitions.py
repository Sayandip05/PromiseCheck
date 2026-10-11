"""Unit tests for commitment state transitions, OCC optimistic concurrency control, and batch candidate creation."""

import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException

from modules.commitments.schemas import CommitmentUpdateRequest
from modules.commitments.service import (
    VALID_STATUS_TRANSITIONS,
    CommitmentService,
)

pytestmark = pytest.mark.unit


def test_invalid_status_transitions_rejected():
    """Verify state transition machine: delivered or cancelled commitments reject invalid transitions."""
    delivered_transitions = VALID_STATUS_TRANSITIONS.get("delivered", set())
    # A delivered commitment cannot be reverted to awaiting-review or at-risk
    assert "awaiting-review" not in delivered_transitions
    assert "at-risk" not in delivered_transitions
    assert "overdue" not in delivered_transitions

    cancelled_transitions = VALID_STATUS_TRANSITIONS.get("cancelled", set())
    # A cancelled commitment cannot transition to on-track or delivered
    assert "on-track" not in cancelled_transitions
    assert "delivered" not in cancelled_transitions


@pytest.mark.asyncio
async def test_occ_etag_mismatch_rejected():
    """Verify If-Match header mismatch against current ETag raises 412 Precondition Failed."""
    mock_commitment = MagicMock()
    mock_commitment.id = uuid.uuid4()
    mock_commitment.workspace_id = uuid.uuid4()
    mock_commitment.updated_at = MagicMock()
    mock_commitment.updated_at.timestamp.return_value = 1700000000.0

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_commitment

    # Expected ETag would be W/"<id>:1700000000"
    mismatched_etag = 'W/"stale-id:1600000000"'
    update_payload = CommitmentUpdateRequest(title="Updated Title")

    with pytest.raises(HTTPException) as exc:
        await CommitmentService.update_commitment(
            db=mock_db,
            commitment_id=mock_commitment.id,
            workspace_id=mock_commitment.workspace_id,
            user=None,
            payload=update_payload,
            if_match=mismatched_etag,
        )

    assert exc.value.status_code == 412
    assert "Precondition Failed" in exc.value.detail


def test_candidate_commitments_batch_sync():
    """Verify create_candidate_commitments_batch_sync initializes candidates with awaiting-review and unconfirmed state."""
    mock_session = MagicMock()
    ws_id = str(uuid.uuid4())
    candidates = [
        {
            "title": "Enable SOC2 Type II compliance audit logs",
            "customer": "Fintech Alpha",
            "quote": "We will have SOC2 logs ready by Q3",
            "promised_by": "Q3 2026",
            "promised_date_iso": "2026-09-30T00:00:00",
            "context": "Customer security review discussion",
        },
        {
            "title": "Deliver custom webhook ingestion payload",
            "customer": "Fintech Alpha",
            "quote": "Custom webhooks will be available next month",
            "promised_by": "Next month",
        },
    ]

    count = CommitmentService.create_candidate_commitments_batch_sync(
        session=mock_session,
        workspace_id=ws_id,
        candidates=candidates,
        meeting_title="Q3 Security Review",
        customer_name="Fintech Alpha",
    )

    assert count == 2
    assert mock_session.add.call_count == 2

    # Verify first added entity attributes
    added_obj = mock_session.add.call_args_list[0][0][0]
    assert added_obj.title == "Enable SOC2 Type II compliance audit logs"
    assert added_obj.customer_name == "Fintech Alpha"
    assert added_obj.status == "awaiting-review"
    assert added_obj.is_confirmed is False
    assert added_obj.category == "awaiting-review"
    assert added_obj.workspace_id == uuid.UUID(ws_id)
