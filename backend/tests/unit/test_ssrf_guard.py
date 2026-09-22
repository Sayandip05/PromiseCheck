"""Unit tests for SSRF protection guard in outbound connectors."""

from unittest.mock import patch
import pytest
from fastapi import HTTPException

from connectors.external_mcp import ExternalMCPConnector
from connectors.ssrf_guard import _is_blocked_ip, validate_no_ssrf


def test_blocked_ip_ranges():
    """Verify internal and metadata IPs are flagged as blocked."""
    assert _is_blocked_ip("127.0.0.1") is True
    assert _is_blocked_ip("10.0.0.1") is True
    assert _is_blocked_ip("192.168.1.1") is True
    assert _is_blocked_ip("172.16.0.1") is True
    assert _is_blocked_ip("169.254.169.254") is True
    assert _is_blocked_ip("::1") is True
    assert _is_blocked_ip("invalid-ip") is True

    # Public IPs should not be blocked
    assert _is_blocked_ip("8.8.8.8") is False
    assert _is_blocked_ip("1.1.1.1") is False


def test_validate_no_ssrf_rejects_private_ips():
    """Verify validate_no_ssrf raises 400 for loopback and internal IPs."""
    with pytest.raises(HTTPException) as exc_127:
        validate_no_ssrf("http://127.0.0.1:8000/api")
    assert exc_127.value.status_code == 400

    with pytest.raises(HTTPException) as exc_localhost:
        validate_no_ssrf("http://localhost:8000/api")
    assert exc_localhost.value.status_code == 400

    with pytest.raises(HTTPException) as exc_meta:
        validate_no_ssrf("http://169.254.169.254/latest/meta-data")
    assert exc_meta.value.status_code == 400


def test_validate_no_ssrf_rejects_empty_or_malformed():
    """Verify validate_no_ssrf raises 400 for invalid URLs."""
    with pytest.raises(HTTPException):
        validate_no_ssrf("")

    with pytest.raises(HTTPException):
        validate_no_ssrf("   ")

    with pytest.raises(HTTPException):
        validate_no_ssrf("not-a-valid-url")


def test_validate_no_ssrf_allows_public_ip():
    """Verify validate_no_ssrf passes for valid public IP or resolvable hostname."""
    with patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Mock DNS resolution to public IP 93.184.216.34 (example.com)
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        # Should not raise
        validate_no_ssrf("https://api.example.com/mcp")


@pytest.mark.asyncio
async def test_external_mcp_blocks_ssrf_attempt():
    """Verify ExternalMCPConnector prevents SSRF attempts before sending requests."""
    mcp = ExternalMCPConnector(endpoint_url="http://127.0.0.1:9090")
    with pytest.raises(HTTPException) as exc:
        await mcp.call_tool("create_commitment", {})
    assert exc.value.status_code == 400
    assert "not permitted" in exc.value.detail or "blocked" in exc.value.detail.lower()
