"""Customers REST router with managed account profiles and commitment health scores."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from modules.commitments.models import Commitment
from modules.customers.models import Customer
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id
from sqlalchemy import func

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


@router.get("", response_model=list[CustomerDTO])
async def list_customers(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Items per page. Maximum 100.",
    ),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List customer accounts for the active workspace with live commitment health scores and pagination."""
    ws_id = await get_active_workspace_id(db, user)

    # Count total customers for the active workspace
    count_res = await db.execute(
        select(func.count(Customer.id)).where(Customer.workspace_id == ws_id)
    )
    total = count_res.scalar_one()

    # Bounded query using LIMIT + OFFSET
    res = await db.execute(
        select(Customer)
        .where(Customer.workspace_id == ws_id)
        .order_by(Customer.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    customers = res.scalars().all()

    if response:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        response.headers["X-Has-Next"] = "true" if (page * page_size) < total else "false"

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
    user: User = Depends(get_current_user),
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


@router.get("/{customer_id}", response_model=CustomerDTO)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve an individual customer account profile with workspace authorization."""
    ws_id = await get_active_workspace_id(db, user)
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    # Tenant authorization check: prevent IDOR access across workspaces
    if customer.workspace_id != ws_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this customer account.",
        )

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


