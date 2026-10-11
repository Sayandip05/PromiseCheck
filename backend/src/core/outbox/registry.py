"""Outbox event handler registry.

Maps outbox event_type strings to Celery task routes, callable handlers, or explicit no-ops.
Enforces that outbox dispatching remains decoupled from specific module implementations.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from core.logging import get_logger

logger = get_logger("outbox_registry")


@dataclass(frozen=True)
class EventRoute:
    """Routing specification for an outbox event."""

    task_name: Optional[str] = None
    queue: str = "default"
    kwargs_builder: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None
    is_noop: bool = False
    description: str = ""


# Internal registry mapping event_type -> EventRoute or callable
_EVENT_REGISTRY: dict[str, Union[EventRoute, Callable[[Any, Any], None]]] = {}


def register_task(
    event_type: str,
    task_name: str,
    queue: str = "default",
    kwargs_builder: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    description: str = "",
) -> None:
    """Register an asynchronous Celery task handler for an event_type."""
    _EVENT_REGISTRY[event_type] = EventRoute(
        task_name=task_name,
        queue=queue,
        kwargs_builder=kwargs_builder,
        is_noop=False,
        description=description,
    )


def register_noop(event_type: str, description: str = "") -> None:
    """Register an explicit acknowledged no-op for an event_type.

    Events with no asynchronous consumer (such as commitment lifecycle events)
    are acknowledged and marked dispatched without raising ValueError or retrying.
    """
    _EVENT_REGISTRY[event_type] = EventRoute(
        task_name=None,
        is_noop=True,
        description=description,
    )


def register_handler(
    event_type: str,
    handler: Callable[[Any, Any], None],
) -> None:
    """Register a custom handler callable `handler(celery_app, row)` for an event_type."""
    _EVENT_REGISTRY[event_type] = handler


def get_route(event_type: str) -> Optional[Union[EventRoute, Callable[[Any, Any], None]]]:
    """Retrieve the registered route or handler for an event_type."""
    return _EVENT_REGISTRY.get(event_type)


def dispatch_event(celery_app: Any, row: Any) -> None:
    """Dispatch an outbox row using the registered route.

    Raises ValueError if event_type is not registered, matching the outbox failure contract.
    """
    event_type: str = getattr(row, "event_type", "")
    payload: dict[str, Any] = getattr(row, "payload", {}) or {}

    route = get_route(event_type)
    if route is None:
        logger.warning(
            f"Dispatcher: unknown event_type '{event_type}' on outbox row {getattr(row, 'id', '')} — "
            "leaving pending until a handler is registered"
        )
        raise ValueError(f"No Celery handler for event_type '{event_type}'")

    if callable(route) and not isinstance(route, EventRoute):
        route(celery_app, row)
        return

    if isinstance(route, EventRoute):
        if route.is_noop:
            logger.debug(
                f"Dispatcher: event_type '{event_type}' acknowledged as no-op on outbox row {getattr(row, 'id', '')}"
            )
            return

        if route.task_name:
            kwargs = route.kwargs_builder(payload) if route.kwargs_builder else payload
            celery_app.send_task(
                route.task_name,
                kwargs=kwargs,
                queue=route.queue,
            )
            return

    raise ValueError(f"Invalid route configuration for event_type '{event_type}'")


# ---------------------------------------------------------------------------
# Default registrations preserving exact existing contracts
# ---------------------------------------------------------------------------

register_task(
    event_type="ingestion.transcript.process",
    task_name="jobs.tasks.process_transcript_ingestion",
    queue="ingestion",
    kwargs_builder=lambda p: {
        "job_id": p["job_id"],
        "workspace_id": p["workspace_id"],
        "transcript_text": p["transcript_text"],
        "customer_name": p.get("customer_name", "Customer"),
        "meeting_title": p.get("meeting_title", "Meeting"),
    },
    description="Processes uploaded transcripts to extract commitments",
)

register_task(
    event_type="ingestion.audio.process",
    task_name="jobs.tasks.process_audio_ingestion",
    queue="ingestion",
    kwargs_builder=lambda p: {
        "job_id": p["job_id"],
        "workspace_id": p["workspace_id"],
        "file_path": p["file_path"],
        "customer_name": p.get("customer_name", "Customer"),
        "meeting_title": p.get("meeting_title", "Meeting"),
    },
    description="Transcribes audio and extracts commitments",
)

register_task(
    event_type="risk.scan.request",
    task_name="jobs.tasks.scan_commitment_deadlines",
    queue="high_priority",
    kwargs_builder=lambda p: {},
    description="Scans commitments for approaching deadlines and overdue items",
)


def _build_notification_kwargs(p: dict[str, Any], event_type: str) -> dict[str, Any]:
    ws_id = p.get("workspace_id", "")
    channel = f"ws:{ws_id}:events" if ws_id else "global:events"
    ev_name = event_type.upper().replace(".", "_")
    return {"channel": channel, "event_type": ev_name, "payload": p}


register_handler(
    event_type="notification.deadline.overdue",
    handler=lambda celery_app, row: celery_app.send_task(
        "jobs.tasks.dispatch_notification_alert",
        kwargs=_build_notification_kwargs(row.payload or {}, row.event_type),
        queue="high_priority",
    ),
)

register_handler(
    event_type="notification.deadline.at_risk",
    handler=lambda celery_app, row: celery_app.send_task(
        "jobs.tasks.dispatch_notification_alert",
        kwargs=_build_notification_kwargs(row.payload or {}, row.event_type),
        queue="high_priority",
    ),
)

# Explicitly acknowledged commitment lifecycle events (no async Celery consumer today)
register_noop(
    event_type="commitment.created",
    description="Commitment record created in database transaction",
)
register_noop(
    event_type="commitment.updated",
    description="Commitment record updated in database transaction",
)
register_noop(
    event_type="commitment.confirmed",
    description="Commitment confirmed by user into active tracking",
)
