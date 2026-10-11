"""Tickets sub-module Pydantic schemas."""

from pydantic import BaseModel


class TicketSnapshot(BaseModel):
    """Normalized engineering issue record."""

    id: str
    tracker: str  # jira, linear, github
    key: str
    status: str
    target_date: str | None = None
    commitment_id: str | None = None
    commitment_title: str | None = None
