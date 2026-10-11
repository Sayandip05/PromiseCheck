"""Risk sub-module Pydantic schemas."""

import uuid

from pydantic import BaseModel


class RiskAssessmentResponse(BaseModel):
    """Calculated delivery risk assessment for a commitment."""

    commitment_id: uuid.UUID
    commitment_title: str
    customer_name: str
    risk_level: str  # low, medium, high, overdue
    conflict_days: int = 0
    reason: str


class RiskEvaluationSummary(BaseModel):
    """Result summary of a workspace risk evaluation run."""

    evaluated_count: int
    at_risk_count: int
    overdue_count: int
    on_track_count: int
    timestamp: str
