"""Customers REST router with managed account profiles and commitment health scores."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.iam.dependencies import get_current_user
from modules.customers.service import CustomerService
from modules.iam.models import User
from modules.iam.service import get_active_workspace_id

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
    dto_list, total = await CustomerService.list_customers_with_metrics(
        db=db,
        workspace_id=ws_id,
        page=page,
        page_size=page_size,
    )

    if response:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        response.headers["X-Has-Next"] = "true" if (page * page_size) < total else "false"

    return [CustomerDTO(**d) for d in dto_list]


@router.post("", response_model=CustomerDTO, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new customer account."""
    ws_id = await get_active_workspace_id(db, user)
    customer = await CustomerService.create_customer(
        db=db,
        workspace_id=ws_id,
        name=payload.name,
        owner=payload.owner,
        recent_promise=payload.recent_promise,
        due_date=payload.due_date,
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


@router.get("/{customer_id}", response_model=CustomerDTO)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve an individual customer account profile with workspace authorization."""
    ws_id = await get_active_workspace_id(db, user)
    customer = await CustomerService.get_customer_by_id(db, customer_id, ws_id)
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
