"""Legacy compatibility module for third-party connector interface.

FEATURE NOTICE:
This module has been renamed to `connectors.connector_interface` to provide
unambiguous, feature-based naming for engineers and avoid generic code-centric terms like 'base'.

Please import directly from `connectors.connector_interface` in all new code.
"""

from connectors.connector_interface import (
    BaseConnector,
    ConnectorAuthenticationError,
    ConnectorDeliveryError,
    ConnectorError,
    ConnectorNotConfiguredError,
)

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "ConnectorNotConfiguredError",
    "ConnectorAuthenticationError",
    "ConnectorDeliveryError",
]
