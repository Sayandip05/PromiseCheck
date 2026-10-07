"""Legacy compatibility module for Commitment Risk Investigation Agent.

FEATURE NOTICE:
This module has been renamed to `ai.risk_investigator` to provide unambiguous,
feature-based naming for engineers and clarify that it investigates commitment delivery risks.

Please import directly from `ai.risk_investigator` in all new code.
"""

from ai.risk_investigator import InvestigationAgent

__all__ = ["InvestigationAgent"]
