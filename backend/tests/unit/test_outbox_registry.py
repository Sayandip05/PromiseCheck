"""Unit tests for the outbox event registry and routing specifications.

Verifies:
- Task routing, queue assignment, and kwargs builder transformations.
- Custom callable handlers and notification channel formatting.
- Explicit acknowledged no-op lifecycle events.
- Duplicate registration, invalid route handling, and unknown event rejection.
- Parametrized completeness across all registered event types.
"""

import uuid
from unittest.mock import MagicMock
import pytest

from core.outbox.registry import (
    _EVENT_REGISTRY,
    EventRoute,
    dispatch_event,
    get_route,
    register_handler,
    register_noop,
    register_task,
)

pytestmark = pytest.mark.unit


def test_registry_lookup_unknown_returns_none():
    """Unregistered event types return None from get_route."""
    assert get_route("completely.unregistered.event.type") is None


def test_registry_duplicate_registration_overwrites_cleanly():
    """Registering an event_type multiple times overwrites the route cleanly without error."""
    test_type = f"test.overwrite.{uuid.uuid4().hex}"
    try:
        register_task(test_type, "jobs.tasks.first_task", queue="default")
        route1 = get_route(test_type)
        assert isinstance(route1, EventRoute)
        assert route1.task_name == "jobs.tasks.first_task"

        register_task(test_type, "jobs.tasks.second_task", queue="high_priority")
        route2 = get_route(test_type)
        assert isinstance(route2, EventRoute)
        assert route2.task_name == "jobs.tasks.second_task"
        assert route2.queue == "high_priority"
    finally:
        _EVENT_REGISTRY.pop(test_type, None)


def test_dispatch_event_unknown_type_raises_value_error():
    """dispatch_event raises ValueError for unregistered event types."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "unknown.foo.bar"
    row.payload = {}

    with pytest.raises(ValueError, match="No Celery handler for event_type 'unknown.foo.bar'"):
        dispatch_event(celery_app, row)


def test_dispatch_event_invalid_route_configuration_raises_value_error():
    """dispatch_event raises ValueError if an EventRoute has neither task_name nor is_noop=True."""
    test_type = f"test.invalid_route.{uuid.uuid4().hex}"
    _EVENT_REGISTRY[test_type] = EventRoute(task_name=None, is_noop=False)
    try:
        celery_app = MagicMock()
        row = MagicMock()
        row.id = uuid.uuid4()
        row.event_type = test_type
        row.payload = {}

        with pytest.raises(ValueError, match="Invalid route configuration for event_type"):
            dispatch_event(celery_app, row)
    finally:
        _EVENT_REGISTRY.pop(test_type, None)


def test_custom_callable_handler_dispatch():
    """register_handler invokes custom callable handler with (celery_app, row)."""
    test_type = f"test.custom_handler.{uuid.uuid4().hex}"
    called_with = []

    def _custom_handler(c_app, row):
        called_with.append((c_app, row.id))

    register_handler(test_type, _custom_handler)
    try:
        celery_app = MagicMock()
        row = MagicMock()
        row.id = uuid.uuid4()
        row.event_type = test_type
        row.payload = {"foo": "bar"}

        dispatch_event(celery_app, row)
        assert len(called_with) == 1
        assert called_with[0] == (celery_app, row.id)
    finally:
        _EVENT_REGISTRY.pop(test_type, None)


@pytest.mark.parametrize(
    "event_type",
    [
        "ingestion.transcript.process",
        "ingestion.audio.process",
        "risk.scan.request",
        "notification.deadline.overdue",
        "notification.deadline.at_risk",
        "commitment.created",
        "commitment.updated",
        "commitment.confirmed",
    ],
)
def test_all_expected_event_types_are_registered_in_registry(event_type: str):
    """Every expected domain outbox event type must be registered in _EVENT_REGISTRY."""
    route = get_route(event_type)
    assert route is not None, f"Event type '{event_type}' must have a registered route or handler"
    if isinstance(route, EventRoute):
        assert route.is_noop or bool(route.task_name)
    else:
        assert callable(route)


def test_transcript_ingestion_kwargs_builder():
    """ingestion.transcript.process formats kwargs correctly and applies defaults."""
    route = get_route("ingestion.transcript.process")
    assert isinstance(route, EventRoute)
    assert route.task_name == "jobs.tasks.process_transcript_ingestion"
    assert route.queue == "ingestion"
    assert route.kwargs_builder is not None

    # With full payload
    built = route.kwargs_builder({
        "job_id": "job-1",
        "workspace_id": "ws-1",
        "transcript_text": "Meeting transcript",
        "customer_name": "Acme",
        "meeting_title": "Sprint Sync",
    })
    assert built == {
        "job_id": "job-1",
        "workspace_id": "ws-1",
        "transcript_text": "Meeting transcript",
        "customer_name": "Acme",
        "meeting_title": "Sprint Sync",
    }

    # With fallback defaults
    built_default = route.kwargs_builder({
        "job_id": "job-2",
        "workspace_id": "ws-2",
        "transcript_text": "Another transcript",
    })
    assert built_default["customer_name"] == "Customer"
    assert built_default["meeting_title"] == "Meeting"


def test_audio_ingestion_kwargs_builder():
    """ingestion.audio.process formats kwargs correctly and applies defaults."""
    route = get_route("ingestion.audio.process")
    assert isinstance(route, EventRoute)
    assert route.task_name == "jobs.tasks.process_audio_ingestion"
    assert route.queue == "ingestion"
    assert route.kwargs_builder is not None

    built = route.kwargs_builder({
        "job_id": "job-audio-1",
        "workspace_id": "ws-audio-1",
        "file_path": "/tmp/recording.mp3",
    })
    assert built["job_id"] == "job-audio-1"
    assert built["file_path"] == "/tmp/recording.mp3"
    assert built["customer_name"] == "Customer"
    assert built["meeting_title"] == "Meeting"


def test_risk_scan_request_kwargs_builder():
    """risk.scan.request targets jobs.tasks.scan_commitment_deadlines with empty kwargs."""
    route = get_route("risk.scan.request")
    assert isinstance(route, EventRoute)
    assert route.task_name == "jobs.tasks.scan_commitment_deadlines"
    assert route.queue == "high_priority"
    assert route.kwargs_builder is not None
    assert route.kwargs_builder({"any": "payload"}) == {}


def test_notification_deadline_overdue_handler_routes_cleanly():
    """notification.deadline.overdue sends dispatch_notification_alert on high_priority queue."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "notification.deadline.overdue"
    row.payload = {
        "workspace_id": "ws-abc",
        "commitment_id": "comm-123",
        "title": "SOC2 Certification",
    }

    dispatch_event(celery_app, row)
    celery_app.send_task.assert_called_once_with(
        "jobs.tasks.dispatch_notification_alert",
        kwargs={
            "channel": "ws:ws-abc:events",
            "event_type": "NOTIFICATION_DEADLINE_OVERDUE",
            "payload": {
                "workspace_id": "ws-abc",
                "commitment_id": "comm-123",
                "title": "SOC2 Certification",
            },
        },
        queue="high_priority",
    )


def test_notification_deadline_at_risk_handler_routes_cleanly():
    """notification.deadline.at_risk sends dispatch_notification_alert with NOTIFICATION_DEADLINE_AT_RISK."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "notification.deadline.at_risk"
    row.payload = {
        "workspace_id": "ws-xyz",
        "commitment_id": "comm-456",
        "title": "Database Migration",
    }

    dispatch_event(celery_app, row)
    celery_app.send_task.assert_called_once_with(
        "jobs.tasks.dispatch_notification_alert",
        kwargs={
            "channel": "ws:ws-xyz:events",
            "event_type": "NOTIFICATION_DEADLINE_AT_RISK",
            "payload": {
                "workspace_id": "ws-xyz",
                "commitment_id": "comm-456",
                "title": "Database Migration",
            },
        },
        queue="high_priority",
    )


def test_notification_fallback_to_global_channel_when_no_workspace():
    """When workspace_id is absent from payload, channel falls back to global:events."""
    celery_app = MagicMock()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.event_type = "notification.deadline.overdue"
    row.payload = {"commitment_id": "comm-orphan"}

    dispatch_event(celery_app, row)
    celery_app.send_task.assert_called_once_with(
        "jobs.tasks.dispatch_notification_alert",
        kwargs={
            "channel": "global:events",
            "event_type": "NOTIFICATION_DEADLINE_OVERDUE",
            "payload": {"commitment_id": "comm-orphan"},
        },
        queue="high_priority",
    )


def test_commitment_lifecycle_events_are_explicit_noops():
    """commitment.created, updated, and confirmed are registered with is_noop=True."""
    for ev_type in ("commitment.created", "commitment.updated", "commitment.confirmed"):
        route = get_route(ev_type)
        assert isinstance(route, EventRoute), f"{ev_type} must be an EventRoute"
        assert route.is_noop is True, f"{ev_type} must have is_noop=True"
        assert route.task_name is None

        # dispatch_event must return without calling send_task
        celery_app = MagicMock()
        row = MagicMock()
        row.id = uuid.uuid4()
        row.event_type = ev_type
        row.payload = {"id": "comm-1"}

        dispatch_event(celery_app, row)
        celery_app.send_task.assert_not_called()
