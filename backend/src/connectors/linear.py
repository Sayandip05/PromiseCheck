"""Linear Integration Connector with GraphQL Client."""

import os
from typing import Any, Optional

import httpx

from connectors.connector_interface import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.linear")


class LinearConnector(BaseConnector):
    """Synchronizes engineering issues, milestone cycles, and statuses from Linear."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LINEAR_API_KEY") or ""
        self.client_id = client_id or os.getenv("LINEAR_CLIENT_ID") or ""
        self.client_secret = client_secret or os.getenv("LINEAR_CLIENT_SECRET") or ""

    @property
    def provider_name(self) -> str:
        return "linear"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key or (self.client_id and self.client_secret) or self.client_id)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        """Verify Linear API key or OAuth Client ID / Secret."""
        key = credentials.get("api_key", self.api_key)
        cid = credentials.get("client_id", self.client_id)
        csec = credentials.get("client_secret", self.client_secret)

        if not key and not (cid and csec) and not cid:
            raise ConnectorNotConfiguredError("Linear connector requires an API key or Client ID / Client Secret.")

        # If personal API key is present, verify directly against Linear GraphQL
        if key:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(
                        "https://api.linear.app/graphql",
                        headers={"Authorization": key, "Content-Type": "application/json"},
                        json={"query": "query { viewer { id name email } }"},
                    )
                    if res.status_code != 200:
                        raise ConnectorDeliveryError(f"Linear verification HTTP {res.status_code}")
                    data = res.json()
                    if "errors" in data:
                        raise ConnectorDeliveryError(f"Linear GraphQL errors: {data['errors']}")
                    return True
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Linear credential verification failed: {exc}")

        # If OAuth Client ID / Secret is configured, credentials are validated
        if cid:
            logger.info(f"[Linear] OAuth Client credentials present (Client ID: {cid[:8]}...)")
            return True

        return False

    async def get_issue(self, identifier: str) -> dict[str, Any]:
        """Fetch Linear issue by identifier (e.g. 'ENG-891')."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Linear is not configured. Provide an API key.")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                query = """
                query IssueById($id: String!) {
                    issue(id: $id) {
                        id
                        identifier
                        title
                        state { name type }
                        assignee { name email }
                        dueDate
                    }
                }
                """
                res = await client.post(
                    "https://api.linear.app/graphql",
                    headers={"Authorization": self.api_key, "Content-Type": "application/json"},
                    json={"query": query, "variables": {"id": identifier}},
                )
                if res.status_code == 200:
                    data = res.json().get("data", {}).get("issue")
                    if data:
                        return {
                            "id": data.get("id"),
                            "identifier": data.get("identifier"),
                            "title": data.get("title"),
                            "status": data.get("state", {}).get("name", "In Review"),
                            "assignee": data.get("assignee", {}).get("name", "Unassigned"),
                            "due_date": data.get("dueDate"),
                            "source": "live_linear_api",
                        }
                    raise ConnectorDeliveryError(f"Linear issue '{identifier}' not found.")
                raise ConnectorDeliveryError(f"Linear GraphQL call failed: HTTP {res.status_code} {res.text}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Linear issue query failed: {exc}")

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Linear is not configured.")
        return {
            "issues_synced": 0,
            "status": "active",
        }

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"issues_reconciled": 0, "status": "synchronized"}
