"""Unit contract tests for Celery background tasks, queue routes, and beat schedule.

CRITICAL Item #5:
- All task names, queues, routing keys, and periodic schedules are explicitly pinned.
- Worker durability settings (late acks, rejection on worker lost, TTL) are guaranteed.
"""

import pytest
from jobs.celery_app import celery_app

pytestmark = pytest.mark.unit


EXPECTED_TASK_NAMES = {
    "jobs.tasks.scan_commitment_deadlines",
    "jobs.tasks.dispatch_notification_alert",
    "jobs.tasks.process_transcript_ingestion",
    "jobs.tasks.process_audio_ingestion",
    "jobs.tasks.cleanup_expired_tokens",
}

EXPECTED_TASK_ROUTES = {
    "jobs.tasks.scan_commitment_deadlines": {"queue": "high_priority"},
    "jobs.tasks.dispatch_notification_alert": {"queue": "high_priority"},
    "jobs.tasks.process_transcript_ingestion": {"queue": "ingestion"},
    "jobs.tasks.process_audio_ingestion": {"queue": "ingestion"},
    "jobs.tasks.cleanup_expired_tokens": {"queue": "default"},
}

EXPECTED_BEAT_SCHEDULE = {
    "periodic-commitment-risk-scan": {
        "task": "jobs.tasks.scan_commitment_deadlines",
        "schedule": 3600.0,
    },
    "nightly-expired-token-cleanup": {
        "task": "jobs.tasks.cleanup_expired_tokens",
        "schedule": 86400.0,
    },
}


def test_celery_task_names_contract():
    """CRITICAL Item #5: All Celery task names match the explicit pinned contracts."""
    registered_tasks = set(celery_app.tasks.keys())
    missing_tasks = EXPECTED_TASK_NAMES - registered_tasks
    assert not missing_tasks, f"Missing registered Celery tasks: {missing_tasks}"

    for task_name in EXPECTED_TASK_NAMES:
        assert task_name in celery_app.tasks
        task_obj = celery_app.tasks[task_name]
        assert callable(task_obj), f"Task {task_name} must be callable"


def test_celery_task_routing_contract():
    """CRITICAL Item #5: Celery task routes match the explicit pinned dictionary."""
    routes = celery_app.conf.task_routes
    assert routes is not None, "Celery task_routes must be defined"

    for task_name, expected_route in EXPECTED_TASK_ROUTES.items():
        actual_route = routes.get(task_name)
        assert actual_route == expected_route, (
            f"Route mismatch for {task_name}: expected {expected_route}, got {actual_route}"
        )


def test_celery_queues_and_exchanges_contract():
    """Celery queue configuration defines all required priority queues with direct exchanges."""
    queue_names = {q.name for q in celery_app.conf.task_queues}
    expected_queues = {"high_priority", "default", "ingestion"}
    assert expected_queues.issubset(queue_names), (
        f"Missing queues: {expected_queues - queue_names}"
    )

    for q in celery_app.conf.task_queues:
        if q.name in expected_queues:
            assert q.routing_key == q.name, f"Queue {q.name} routing_key mismatch"


def test_celery_beat_schedule_contract():
    """CRITICAL Item #5: Celery Beat schedule equals the explicit expected schedule dictionary."""
    beat_schedule = celery_app.conf.beat_schedule
    assert beat_schedule is not None, "Celery beat_schedule must be defined"

    for schedule_name, expected_config in EXPECTED_BEAT_SCHEDULE.items():
        assert schedule_name in beat_schedule, f"Missing beat schedule entry: {schedule_name}"
        actual = beat_schedule[schedule_name]
        assert actual["task"] == expected_config["task"], (
            f"Beat task mismatch for {schedule_name}: expected {expected_config['task']}, got {actual['task']}"
        )
        assert actual["schedule"] == expected_config["schedule"], (
            f"Beat schedule interval mismatch for {schedule_name}: "
            f"expected {expected_config['schedule']}, got {actual['schedule']}"
        )


def test_celery_worker_durability_and_reliability_settings():
    """Worker configuration adheres to production durability requirements."""
    conf = celery_app.conf
    assert conf.task_acks_late is True, "task_acks_late must be True to prevent task loss on worker crash"
    assert conf.task_reject_on_worker_lost is True, "task_reject_on_worker_lost must be True for crash requeuing"
    assert conf.worker_prefetch_multiplier == 1, "worker_prefetch_multiplier must be 1 for fair scheduling"
    assert conf.task_serializer == "json", "task_serializer must be JSON"
    assert conf.result_expires == 86400, "result_expires must be 86400 (24h TTL)"
