"""Customers module router and schemas."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerResponse(BaseModel):
    """Customer account profile."""

    id: uuid.UUID
    name: str
    domains: list[str] = []
    created_at: datetime


@router.get("", response_model=list[CustomerResponse])
async def list_customers():
    """List managed customer accounts."""
    return []
