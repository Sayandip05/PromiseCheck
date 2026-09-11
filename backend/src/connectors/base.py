"""Base connector contract for external third-party integrations."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstract interface implemented by all third-party provider connectors."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'google_meet', 'jira', 'linear')."""
        pass

    @abstractmethod
    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate connection credentials against the remote provider API."""
        pass

    @abstractmethod
    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        """Perform initial historical sync of authorized resources."""
        pass

    @abstractmethod
    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        """Reconcile local state with remote provider to catch missed events."""
        pass
