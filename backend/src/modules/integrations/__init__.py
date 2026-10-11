"""Integrations domain module public interface."""

from modules.integrations.service import (
    IntegrationService,
    get_valid_google_token_for_workspace,
)

__all__ = [
    "IntegrationService",
    "get_valid_google_token_for_workspace",
]
