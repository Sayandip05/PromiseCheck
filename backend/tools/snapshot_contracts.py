#!/usr/bin/env python3
"""Contract Snapshot Tool (OpenAPI, Celery, Database Schema).

Provides --write and --check modes to enforce contract freeze during refactoring.
"""

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

# Ensure backend/src is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SRC_DIR = REPO_ROOT / "backend" / "src"
BASELINE_DIR = REPO_ROOT / "docs" / "baseline"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def collect_openapi() -> dict:
    from main import app
    return app.openapi()


def collect_celery() -> dict:
    from jobs.celery_app import celery_app
    user_tasks = sorted([k for k in celery_app.tasks.keys() if not k.startswith("celery.")])
    task_routes = dict(celery_app.conf.task_routes or {})
    beat_schedule = {}
    for k, v in (celery_app.conf.beat_schedule or {}).items():
        beat_schedule[k] = {
            "task": v.get("task"),
            "schedule": str(v.get("schedule")),
        }
    return {
        "tasks": user_tasks,
        "task_routes": task_routes,
        "beat_schedule": beat_schedule,
    }


def collect_database_schema() -> dict:
    from core.database import Base
    # Ensure all models are imported
    try:
        import modules.iam.models  # noqa
        import modules.commitments.models  # noqa
        import modules.commitments.tickets.models  # noqa
        import modules.customers.models  # noqa
        import modules.ingestion.models  # noqa
        import modules.notifications.models  # noqa
        import modules.retention.models  # noqa
        import modules.audit.models  # noqa
        import modules.integrations.models  # noqa
        import core.outbox.models  # noqa
    except ImportError:
        pass

    schema = {}
    for table_name, table in sorted(Base.metadata.tables.items()):
        cols = []
        for col in table.columns:
            cols.append({
                "name": col.name,
                "type": str(col.type),
                "nullable": bool(col.nullable),
                "primary_key": bool(col.primary_key),
            })
        schema[table_name] = {
            "columns": sorted(cols, key=lambda c: c["name"]),
        }
    return schema


def get_current_snapshots() -> dict[str, dict]:
    return {
        "openapi.json": collect_openapi(),
        "celery_contracts.json": collect_celery(),
        "database_schema.json": collect_database_schema(),
    }


def write_snapshots() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = get_current_snapshots()
    for filename, data in snapshots.items():
        file_path = BASELINE_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"[snapshot] Wrote {file_path}")


def check_snapshots() -> bool:
    if not BASELINE_DIR.exists():
        print(f"[snapshot ERROR] Baseline directory does not exist: {BASELINE_DIR}")
        return False

    snapshots = get_current_snapshots()
    has_diff = False

    for filename, current_data in snapshots.items():
        file_path = BASELINE_DIR / filename
        if not file_path.exists():
            print(f"[snapshot ERROR] Missing baseline snapshot: {file_path}")
            has_diff = True
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            baseline_raw = f.read()

        current_raw = json.dumps(current_data, indent=2, sort_keys=True) + "\n"

        if baseline_raw != current_raw:
            print(f"\n[snapshot DIFF DETECTED] {filename} changed:")
            diff = difflib.unified_diff(
                baseline_raw.splitlines(keepends=True),
                current_raw.splitlines(keepends=True),
                fromfile=f"baseline/{filename}",
                tofile=f"current/{filename}",
            )
            sys.stdout.writelines(diff)
            has_diff = True

    if has_diff:
        print("\n[snapshot FAILED] Contracts do not match baseline snapshots!")
        return False

    print("[snapshot PASSED] All contracts match baseline snapshots exactly.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Snapshot and verify contract freeze.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Write current contracts to docs/baseline/")
    group.add_argument("--check", action="store_true", help="Verify current contracts match docs/baseline/")

    args = parser.parse_args()

    if args.write:
        write_snapshots()
    elif args.check:
        if not check_snapshots():
            sys.exit(1)


if __name__ == "__main__":
    main()
