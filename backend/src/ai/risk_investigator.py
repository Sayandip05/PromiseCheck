"""Autonomous Commitment Risk Investigation Agent (Feature-Based Architecture).

FEATURE PURPOSE:
Provides a bounded, tool-using agent that investigates customer commitment risk,
cross-references external tracker tickets (Jira, Linear) and produces a
structured finding plus a recommended mitigation step before SLA breaches occur.

The agent is deliberately dependency-injected: the caller (modules layer) brings
the commitment context and an optional ticket-lookup callable.  This keeps the
``ai`` layer free of database imports while still allowing the agent to perform
real, bounded tool calls.

NAMING CONVENTION:
This module is named `risk_investigator.py` to immediately state the business feature
it performs, replacing generic names like `investigator.py`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Awaitable, Callable

from ai.client import AIClient
from ai.prompts import INVESTIGATION_AGENT_PROMPT_V1
from core.logging import get_logger

logger = get_logger("risk_investigator")

# A ticket lookup receives (provider, provider_ticket_key) and returns a
# normalized ticket snapshot.  Injected by the modules layer so the agent does
# not depend on connectors/database internals directly.
TicketLookup = Callable[[str, str], Awaitable[dict[str, Any]]]

_CLOSED_TICKET_STATUSES = {"done", "closed", "completed", "released", "resolved"}
_BLOCKED_TICKET_STATUSES = {"blocked", "impeded", "on hold", "on-hold", "stalled"}


class InvestigationAgent:
    """Bounded tool-using agent that checks Jira/Linear dates and drafts customer updates."""

    def __init__(self, max_tool_calls: int = 6, client: AIClient | None = None) -> None:
        self.max_tool_calls = max(1, int(max_tool_calls))
        self.client = client or AIClient()

    async def investigate_commitment(
        self,
        commitment_id: str,
        *,
        context: dict[str, Any] | None = None,
        ticket_lookup: TicketLookup | None = None,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """Run a bounded investigation and return a structured risk finding.

        Tool budget is shared across every step.  A step is only counted when it
        actually executes a tool (loading context, querying a tracker, running
        the deterministic evaluation, or asking the LLM for a recommendation).
        The agent always returns a dictionary; provider failures become findings
        rather than unhandled exceptions so callers can surface partial results.
        """
        used = 0
        findings: list[dict[str, Any]] = []
        evidence: dict[str, Any] = {}

        # ── Tool 1: commitment context ────────────────────────────────────────
        if context:
            used += 1
            evidence["commitment"] = {
                "title": context.get("title"),
                "customer": context.get("customer"),
                "status": context.get("status"),
                "due_date": context.get("due_date"),
                "promised_by": context.get("promised_by"),
            }
        else:
            findings.append(
                {
                    "code": "commitment_context_unavailable",
                    "severity": "unknown",
                    "detail": "No commitment context was supplied to the investigator.",
                }
            )

        # ── Tool 2: tracker ticket lookup ─────────────────────────────────────
        ticket: dict[str, Any] | None = None
        ticket_ref = self._ticket_ref(context)
        if context and ticket_ref and ticket_lookup and used < self.max_tool_calls:
            used += 1
            provider, key = ticket_ref
            try:
                ticket = await ticket_lookup(provider, key)
                evidence["ticket"] = ticket
            except Exception as exc:  # provider/network errors are findings
                logger.warning(
                    "Investigation ticket lookup failed for %s/%s: %s", provider, key, exc
                )
                findings.append(
                    {
                        "code": "ticket_lookup_failed",
                        "severity": "unknown",
                        "detail": f"Could not read tracker ticket {provider}/{key}: {exc}",
                    }
                )

        # ── Tool 3: deterministic risk evaluation ─────────────────────────────
        deterministic: dict[str, Any] = {
            "risk_level": "unknown",
            "findings": [],
            "recommended_step": "Connect the commitment source and tracker to investigate.",
        }
        if context and used < self.max_tool_calls:
            used += 1
            deterministic = self._evaluate(context, ticket)
            findings.extend(deterministic["findings"])

        # ── Tool 4: optional AI synthesis ─────────────────────────────────────
        recommendation = deterministic["recommended_step"]
        recommendation_source = "rules"
        if context and use_ai and used < self.max_tool_calls:
            used += 1
            ai_recommendation = await self._synthesize(
                commitment_id=commitment_id,
                context=context,
                ticket=ticket,
                findings=findings,
            )
            if ai_recommendation:
                recommendation = ai_recommendation
                recommendation_source = "ai"

        risk_level = deterministic["risk_level"]
        if not context:
            status = "insufficient_context"
        elif any(f.get("severity") == "critical" for f in findings):
            status = "completed"
            risk_level = "critical"
        else:
            status = "completed"

        return {
            "status": status,
            "commitment_id": commitment_id,
            "tool_calls_used": used,
            "max_tool_calls": self.max_tool_calls,
            "risk_level": risk_level,
            "findings": findings,
            "evidence": evidence,
            "recommended_step": recommendation,
            "recommendation_source": recommendation_source,
            "investigated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal tools ────────────────────────────────────────────────────────

    @staticmethod
    def _ticket_ref(context: dict[str, Any] | None) -> tuple[str, str] | None:
        if not context:
            return None
        key = context.get("ticket_key") or context.get("ticket_id")
        if not key:
            tickets = (context.get("engineering_evidence") or {}).get("tickets") or []
            if tickets and isinstance(tickets[0], dict):
                key = tickets[0].get("key")
                provider = tickets[0].get("tracker") or context.get("ticket_provider")
                if key:
                    return str(provider or "jira").lower(), str(key)
            return None
        provider = context.get("ticket_provider") or "jira"
        return str(provider).lower(), str(key)

    @staticmethod
    def _parse_due(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _evaluate(
        self,
        context: dict[str, Any],
        ticket: dict[str, Any] | None,
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        level = "low"

        now = datetime.now(timezone.utc)
        due = self._parse_due(context.get("due_date"))
        status = str(context.get("status") or "").lower()

        if status in {"overdue", "blocked"}:
            level = "critical" if status == "blocked" else "high"
            findings.append(
                {
                    "code": f"commitment_{status}",
                    "severity": level,
                    "detail": f"Commitment status is '{status}'.",
                }
            )

        if due is not None:
            days_remaining = (due - now).days
            if days_remaining < 0:
                level = "critical"
                findings.append(
                    {
                        "code": "deadline_passed",
                        "severity": "critical",
                        "detail": f"Delivery target passed {abs(days_remaining)} day(s) ago.",
                    }
                )
            elif days_remaining <= 3:
                level = "high" if level != "critical" else level
                findings.append(
                    {
                        "code": "deadline_imminent",
                        "severity": "high",
                        "detail": f"Delivery target is in {days_remaining} day(s).",
                    }
                )

        conflict_days = int(context.get("conflict_days") or 0)
        if conflict_days > 0:
            level = "critical" if conflict_days > 5 else "high"
            findings.append(
                {
                    "code": "timeline_conflict",
                    "severity": "high" if conflict_days <= 5 else "critical",
                    "detail": f"Tracker and commitment dates conflict by {conflict_days} day(s).",
                }
            )

        if ticket:
            ticket_status = str(ticket.get("status") or "").strip().lower()
            if ticket_status in _BLOCKED_TICKET_STATUSES:
                level = "critical"
                findings.append(
                    {
                        "code": "ticket_blocked",
                        "severity": "critical",
                        "detail": f"Linked tracker ticket is '{ticket_status}'.",
                    }
                )
            elif ticket_status in _CLOSED_TICKET_STATUSES:
                findings.append(
                    {
                        "code": "ticket_complete",
                        "severity": "info",
                        "detail": "Linked tracker ticket is complete; verify delivery evidence.",
                    }
                )
            else:
                ticket_due = self._parse_due(ticket.get("target_date") or ticket.get("targetDate"))
                if due is not None and ticket_due is not None and ticket_due > due:
                    drift = (ticket_due - due).days
                    level = "high" if level != "critical" else level
                    findings.append(
                        {
                            "code": "ticket_target_after_commitment",
                            "severity": "high",
                            "detail": (
                                f"Tracker target date is {drift} day(s) after the "
                                "customer commitment milestone."
                            ),
                        }
                    )

        if level == "low" and not findings:
            findings.append(
                {
                    "code": "no_conflict_detected",
                    "severity": "info",
                    "detail": "No due-date, status, or tracker conflict was detected.",
                }
            )

        recommended = self._recommend(level, findings, context)
        return {
            "risk_level": level,
            "findings": findings,
            "recommended_step": recommended,
        }

    @staticmethod
    def _recommend(level: str, findings: list[dict[str, Any]], context: dict[str, Any]) -> str:
        customer = context.get("customer") or "the customer"
        title = context.get("title") or "the commitment"
        codes = {f["code"] for f in findings}
        if "ticket_blocked" in codes:
            return (
                f"Escalate the blocked tracker ticket for '{title}' and send {customer} a "
                "proactive update with a revised, approved date."
            )
        if "deadline_passed" in codes or "commitment_overdue" in codes:
            return (
                f"Send {customer} an immediate recovery update for '{title}' with verified "
                "evidence or a revised commitment date."
            )
        if "deadline_imminent" in codes or "ticket_target_after_commitment" in codes:
            return (
                f"Confirm the tracker milestone for '{title}' today and pre-draft a status "
                f"update for {customer}."
            )
        if level in {"high", "critical"}:
            return f"Review '{title}' with the delivery owner and prepare a mitigation plan."
        return f"No action required; continue monitoring '{title}'."

    async def _synthesize(
        self,
        *,
        commitment_id: str,
        context: dict[str, Any],
        ticket: dict[str, Any] | None,
        findings: list[dict[str, Any]],
    ) -> str | None:
        """Ask the LLM for a concise mitigation step, tolerating AI outages."""
        prompt = (
            f"{INVESTIGATION_AGENT_PROMPT_V1}\n\n"
            f"Commitment: {context.get('title')} for {context.get('customer')}\n"
            f"Status: {context.get('status')}\n"
            f"Due: {context.get('due_date') or context.get('promised_by')}\n"
            f"Ticket: {ticket}\n"
            f"Findings: {findings}\n"
            f"Commitment id: {commitment_id}\n"
            "Return one concrete next step in at most two sentences."
        )
        try:
            text = await self.client.generate(prompt)
        except Exception as exc:
            logger.info("Investigation AI synthesis unavailable: %s", exc)
            return None
        text = (text or "").strip()
        return text or None


__all__ = ["InvestigationAgent", "TicketLookup"]
