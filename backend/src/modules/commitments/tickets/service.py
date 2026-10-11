"""Engineering domain service for tracker issues, Jira/Linear syncing, and PR mapping."""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.connector_interface import ConnectorDeliveryError, ConnectorNotConfiguredError
from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from modules.commitments.service import CommitmentService
from modules.integrations.service import IntegrationService


class EngineeringService:
    """Encapsulates engineering ticket mapping, remote status queries, and issue verification."""

    @staticmethod
    async def list_linked_tickets(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """List linked engineering tracker tickets from active commitments."""
        commitments = await CommitmentService.list_all_workspace_commitments(db, workspace_id)
        tickets: list[dict[str, Any]] = []
        for c in commitments:
            evidence = c.engineering_evidence_json or {}
            for t in evidence.get("tickets", []):
                tickets.append({
                    "id": f"{t.get('tracker', 'jira')}-{t.get('key', 'ENG-1')}",
                    "tracker": t.get("tracker", "jira"),
                    "key": t.get("key", "UNKNOWN"),
                    "status": t.get("status", "In Progress"),
                    "target_date": t.get("targetDate"),
                    "commitment_id": str(c.id),
                    "commitment_title": c.title,
                })
        return tickets

    @staticmethod
    async def get_remote_ticket_status(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        tracker: str,
        key: str,
    ) -> dict[str, Any]:
        """Directly query remote Jira or Linear status with fail-fast validation."""
        cfg = await IntegrationService.get_decrypted_config(db, workspace_id, tracker.lower())

        try:
            if tracker.lower() == "jira":
                jira = JiraConnector(
                    domain=cfg.get("domain"),
                    email=cfg.get("email"),
                    api_token=cfg.get("api_token") or cfg.get("api_key"),
                )
                return await jira.get_ticket(key)
            elif tracker.lower() == "linear":
                linear = LinearConnector(
                    api_key=cfg.get("api_key"),
                )
                return await linear.get_issue(key)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported engineering tracker: {tracker}")
        except ConnectorNotConfiguredError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except ConnectorDeliveryError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
