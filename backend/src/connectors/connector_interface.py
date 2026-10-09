"""Connector Interface & Exceptions Contract (Feature-Based Architecture).

FEATURE PURPOSE:
Defines the standard abstract contract and domain exceptions for all external
third-party integrations (Slack, Jira, Linear, Google Meet, Recall, Gmail, Calendar).

NAMING CONVENTION:
This module is named `connector_interface.py` to make its feature role obvious
to any engineer joining the codebase, replacing ambiguous generic names like `base.py`.
"""

from abc import ABC, abstractmethod
from typing import Any


class ConnectorError(Exception):
    """Base domain exception for all third-party connector failures."""


class ConnectorNotConfiguredError(ConnectorError):
    """Raised when an operation is attempted on an unconfigured connector (missing credentials)."""


class ConnectorAuthenticationError(ConnectorError):
    """Raised when third-party provider rejects credentials (401/403, expired token)."""


class ConnectorDeliveryError(ConnectorError):
    """Raised when third-party service fails, times out, or returns an error response."""


class BaseConnector(ABC):
    """Abstract interface contract implemented by all third-party provider connectors."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'google_meet', 'jira', 'linear', 'slack')."""
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
