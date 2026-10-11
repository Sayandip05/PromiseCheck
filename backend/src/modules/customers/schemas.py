"""Customers domain Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


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
