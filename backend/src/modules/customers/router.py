"""Customers REST router with managed account profiles and commitment health scores."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user_optional
from modules.commitments.models import Commitment
from modules.customers.models import Customer
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerDTO(BaseModel):
    """Customer account profile matching frontend ACCOUNTS schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str  # on-track | at-risk | review | completed
    statusColor: str
    activePromises: int
    healthScore: int
    recentPromise: str
    dueDate: str
    owner: str


class CustomerCreateRequest(BaseModel):
    """Payload to add a new customer account."""

    name: str
    owner: Optional[str] = "Account Manager"
    recent_promise: Optional[str] = ""
    due_date: Optional[str] = ""




async def _seed_default_customers(db: AsyncSession, workspace_id: uuid.UUID):
    """Seed standard enterprise customer accounts if empty."""
    res = await db.execute(select(Customer).where(Customer.workspace_id == workspace_id).limit(1))
    if res.scalar_one_or_none():
        return

    seeds = [
        Customer(
            workspace_id=workspace_id,
            name="Aurora Tech Inc.",
            status="on-track",
            status_color="#10b981",
            active_promises=5,
            health_score=98,
            recent_promise="Deliver SOC2 Type II Report",
            due_date="Sep 18, 2026",
            owner="Sarah Lin",
            domains_json=["auroratech.io"],
        ),
        Customer(
            workspace_id=workspace_id,
            name="Maplewood Imports LLC",
            status="at-risk",
            status_color="#f59e0b",
            active_promises=3,
            health_score=71,
            recent_promise="Custom EDI Inventory Sync Gateway",
            due_date="Sep 21, 2026",
            owner="David Chen",
            domains_json=["maplewoodimports.com"],
        ),
        Customer(
            workspace_id=workspace_id,
            name="OceanView Enterprises Ltd.",
            status="review",
            status_color="#525252",
            active_promises=4,
            health_score=89,
            recent_promise="Single Sign-On SAML Multi-domain",
            due_date="Sep 28, 2026",
            owner="Alex Rivera",
            domains_json=["oceanview.co"],
        ),
        Customer(
            workspace_id=workspace_id,
            name="Northstar Labs",
            status="at-risk",
            status_color="#f59e0b",
            active_promises=2,
            health_score=68,
            recent_promise="Export compliance audit logs",
            due_date="Sep 22, 2026",
            owner="Daniel Stone",
            domains_json=["northstarlabs.com"],
        ),
    ]
    db.add_all(seeds)
    await db.commit()


@router.get("", response_model=list[CustomerDTO])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List customer accounts for the active workspace with live commitment health scores."""
    ws_id = await get_active_workspace_id(db, user)
    await _seed_default_customers(db, ws_id)

    res = await db.execute(select(Customer).where(Customer.workspace_id == ws_id))
    customers = res.scalars().all()

    # Query commitments to calculate dynamic promise counts & health
    comm_res = await db.execute(select(Commitment).where(Commitment.workspace_id == ws_id))
    commitments = comm_res.scalars().all()

    dto_list: list[CustomerDTO] = []
    for c in customers:
        c_name_clean = c.name.lower().strip()
        matching = [
            comm
            for comm in commitments
            if comm.customer_name.lower().strip() in c_name_clean
            or c_name_clean in comm.customer_name.lower().strip()
        ]

        if matching:
            active_count = sum(1 for comm in matching if comm.status != "delivered")
            at_risk_count = sum(1 for comm in matching if comm.status == "at-risk")
            if at_risk_count > 0:
                c_status = "at-risk"
                c_color = "#f59e0b"
                health = max(50, 90 - (at_risk_count * 20))
            elif active_count > 0:
                c_status = "on-track"
                c_color = "#10b981"
                health = 95
            else:
                c_status = "completed"
                c_color = "#10b981"
                health = 100

            recent = matching[-1].title
            due = matching[-1].promised_by or c.due_date
        else:
            c_status = c.status
            c_color = c.status_color
            active_count = c.active_promises
            health = c.health_score
            recent = c.recent_promise
            due = c.due_date

        dto_list.append(
            CustomerDTO(
                id=str(c.id),
                name=c.name,
                status=c_status,
                statusColor=c_color,
                activePromises=active_count,
                healthScore=health,
                recentPromise=recent,
                dueDate=due,
                owner=c.owner,
            )
        )

    return dto_list


@router.post("", response_model=CustomerDTO, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new customer account."""
    ws_id = await get_active_workspace_id(db, user)
    customer = Customer(
        workspace_id=ws_id,
        name=payload.name,
        owner=payload.owner or "Account Manager",
        recent_promise=payload.recent_promise or "Initial onboarding",
        due_date=payload.due_date or "Upcoming",
        status="on-track",
        status_color="#10b981",
        active_promises=1,
        health_score=100,
        domains_json=[],
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return CustomerDTO(
        id=str(customer.id),
        name=customer.name,
        status=customer.status,
        statusColor=customer.status_color,
        activePromises=customer.active_promises,
        healthScore=customer.health_score,
        recentPromise=customer.recent_promise,
        dueDate=customer.due_date,
        owner=customer.owner,
    )

