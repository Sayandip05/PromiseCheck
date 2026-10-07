"""CLI script to seed demo data into a workspace for local development and demos.

Usage:
    python -m scripts.seed_demo_workspace
    python -m scripts.seed_demo_workspace --workspace-id <UUID>
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Add backend/src to PYTHONPATH if executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from modules.customers.models import Customer
from modules.commitments.models import Commitment
from modules.audit.models import AuditEvent
from modules.workspaces.models import Workspace, WorkspaceMember, Role
from modules.identity.models import User
from core.security import hash_password


DEMO_CUSTOMERS = [
    {"name": "Acme Corp", "status": "on-track", "status_color": "#10b981", "active_promises": 3, "health_score": 92, "recent_promise": "SOC2 Audit", "due_date": "Oct 15, 2026", "owner": "Sarah Connor", "domains_json": ["acme.corp"]},
    {"name": "Stark Tech", "status": "on-track", "status_color": "#10b981", "active_promises": 2, "health_score": 88, "recent_promise": "SAML SSO", "due_date": "Oct 25, 2026", "owner": "Tony Stark", "domains_json": ["stark.tech"]},
    {"name": "Wayne Enterprises", "status": "on-track", "status_color": "#10b981", "active_promises": 1, "health_score": 95, "recent_promise": "Webhook API", "due_date": "Delivered", "owner": "Bruce Wayne", "domains_json": ["wayne.com"]},
    {"name": "Cyberdyne Systems", "status": "at-risk", "status_color": "#f59e0b", "active_promises": 2, "health_score": 74, "recent_promise": "Latency SLA", "due_date": "Nov 01, 2026", "owner": "Miles Bennett", "domains_json": ["cyberdyne.io"]},
    {"name": "Umbrella Health", "status": "on-track", "status_color": "#10b981", "active_promises": 1, "health_score": 81, "recent_promise": "S3 Pipeline", "due_date": "Oct 20, 2026", "owner": "Albert Wesker", "domains_json": ["umbrella.health"]},
]


DEMO_COMMITMENTS = [
    {
        "title": "Deliver SOC2 Type II Compliance Reports",
        "customer": "Acme Corp",
        "owner_name": "Sarah Connor",
        "owner_email": "sarah@example.com",
        "category": "needs-attention",
        "status": "at-risk",
        "status_label": "At risk",
        "days_delta": 4,
        "is_confirmed": True,
        "risk_level": "medium",
        "risk_reason": "Auditor evidence collection behind schedule by 2 days",
    },
    {
        "title": "Enable SAML 2.0 SSO with Okta Integration",
        "customer": "Stark Tech",
        "owner_name": "Tony Stark",
        "owner_email": "tony@example.com",
        "category": "in-progress",
        "status": "active",
        "status_label": "Active",
        "days_delta": 14,
        "is_confirmed": True,
        "risk_level": "low",
        "risk_reason": "Engineering sprint PR open and reviewed",
    },
    {
        "title": "Custom Webhook Integrations for Billing Events",
        "customer": "Wayne Enterprises",
        "owner_name": "Bruce Wayne",
        "owner_email": "bruce@example.com",
        "category": "delivered",
        "status": "delivered",
        "status_label": "Delivered",
        "days_delta": -5,
        "is_confirmed": True,
        "risk_level": "low",
        "risk_reason": "Verified live in production",
    },
    {
        "title": "Real-time Latency SLA under 100ms",
        "customer": "Cyberdyne Systems",
        "owner_name": "Miles Bennett",
        "owner_email": "miles@example.com",
        "category": "awaiting-review",
        "status": "awaiting-review",
        "status_label": "Awaiting review",
        "days_delta": 21,
        "is_confirmed": False,
        "risk_level": "high",
        "risk_reason": "Pending architecture review with infrastructure team",
    },
    {
        "title": "Automated S3 Data Export Pipeline",
        "customer": "Umbrella Health",
        "owner_name": "Albert Wesker",
        "owner_email": "albert@example.com",
        "category": "in-progress",
        "status": "active",
        "status_label": "Active",
        "days_delta": 10,
        "is_confirmed": True,
        "risk_level": "low",
        "risk_reason": "Terraform and worker pipeline configured in staging",
    },
]


async def seed_demo(workspace_id_str: str | None = None, user_email: str = "demo@promisecheck.io") -> None:
    async with AsyncSessionLocal() as session:
        # 1. Resolve or create user
        user = (
            await session.execute(select(User).where(User.email == user_email))
        ).scalar_one_or_none()
        if not user:
            user = User(
                email=user_email,
                full_name="Demo User",
                password_hash=hash_password("DemoPassword123!"),
                is_active=True,
            )
            session.add(user)
            await session.flush()

            print(f"[Seed] Created demo user: {user.email} (password: DemoPassword123!)")

        # 2. Resolve or create workspace
        if workspace_id_str:
            ws_id = uuid.UUID(workspace_id_str)
            ws = (
                await session.execute(select(Workspace).where(Workspace.id == ws_id))
            ).scalar_one_or_none()
            if not ws:
                ws = Workspace(id=ws_id, name="Demo Workspace", slug="demo-workspace")
                session.add(ws)
                await session.flush()
        else:
            # Check user memberships
            membership = (
                await session.execute(
                    select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
                )
            ).scalars().first()
            if membership:
                ws_id = membership.workspace_id
                ws = (
                    await session.execute(select(Workspace).where(Workspace.id == ws_id))
                ).scalar_one_or_none()
            else:
                ws = Workspace(name="Demo Workspace", slug="demo-workspace")
                session.add(ws)
                await session.flush()
                ws_id = ws.id


        # Ensure user is member
        member = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if not member:
            session.add(
                WorkspaceMember(workspace_id=ws_id, user_id=user.id, role=Role.ADMIN)
            )
            await session.flush()

        print(f"[Seed] Active workspace: {ws.name} ({ws_id})")

        # 3. Seed Customers
        existing_cust_count = (
            await session.execute(
                select(Customer).where(Customer.workspace_id == ws_id)
            )
        ).scalars().all()

        if not existing_cust_count:
            for c_data in DEMO_CUSTOMERS:
                cust = Customer(
                    workspace_id=ws_id,

                    name=c_data["name"],
                    status=c_data["status"],
                    status_color=c_data["status_color"],
                    active_promises=c_data["active_promises"],
                    health_score=c_data["health_score"],
                    recent_promise=c_data["recent_promise"],
                    due_date=c_data["due_date"],
                    owner=c_data["owner"],
                    domains_json=c_data["domains_json"],
                )
                session.add(cust)

            print(f"[Seed] Created {len(DEMO_CUSTOMERS)} demo customers.")

        # 4. Seed Commitments
        existing_comm_count = (
            await session.execute(
                select(Commitment).where(Commitment.workspace_id == ws_id)
            )
        ).scalars().all()

        today = date.today()
        now_utc = datetime.now(timezone.utc)

        if not existing_comm_count:
            for item in DEMO_COMMITMENTS:
                promised_date = today + timedelta(days=item["days_delta"])
                due_datetime = now_utc + timedelta(days=item["days_delta"])
                comm = Commitment(
                    workspace_id=ws_id,
                    title=item["title"],
                    customer_name=item["customer"],
                    owner_name=item["owner_name"],
                    owner_email=item["owner_email"],
                    status=item["status"],
                    status_label=item["status_label"],
                    category=item["category"],
                    promised_by=promised_date.strftime("%B %d, %Y"),
                    promised_date=promised_date,
                    due_date=due_datetime,
                    is_confirmed=item["is_confirmed"],
                    has_conflict=(item["risk_level"] == "high"),
                    conflict_days=2 if item["risk_level"] == "high" else 0,
                    risk_json={
                        "level": item["risk_level"],
                        "reason": item["risk_reason"],
                        "conflictDays": 2 if item["risk_level"] == "high" else 0,
                    },
                    original_promise_json={
                        "quote": f"We will ensure {item['title']} is finalized on time.",
                        "sourceTitle": f"Executive Quarterly Review with {item['customer']}",
                        "timestamp": (now_utc - timedelta(days=3)).strftime("%Y-%m-%d %H:%M UTC"),
                    },
                    engineering_evidence_json={
                        "prs": [{"id": "PR-104", "title": "Implement core capability", "status": "merged"}],
                        "tickets": [{"key": "ENG-402", "status": "In Progress"}],
                    },
                )
                session.add(comm)
            print(f"[Seed] Created {len(DEMO_COMMITMENTS)} demo commitments.")

        # 5. Seed Audit Event
        session.add(
            AuditEvent(
                workspace_id=ws_id,
                actor_id=user.id,
                action="DEMO_DATA_SEEDED",
                target_type="workspace",
                target_id=str(ws_id),
                description="Demo commitments and customers seeded via CLI script.",
                payload={"total_customers": len(DEMO_CUSTOMERS), "total_commitments": len(DEMO_COMMITMENTS)},
            )
        )

        await session.commit()
        print(f"[Seed] Successfully populated workspace {ws_id} with enterprise demo dataset.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for PromiseCheck")
    parser.add_argument("--workspace-id", help="Workspace UUID to seed (optional)")
    parser.add_argument("--email", default="demo@promisecheck.io", help="Demo user email")
    args = parser.parse_args()

    asyncio.run(seed_demo(args.workspace_id, args.email))
