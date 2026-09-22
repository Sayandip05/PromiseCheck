"""SSRF (Server-Side Request Forgery) protection guard for outbound HTTP calls.

Any connector that makes outbound HTTP requests to user-supplied URLs must call
validate_no_ssrf(url) before dispatching the request. This prevents attackers
from using the server as a proxy to reach internal services, cloud metadata
endpoints, or RFC-1918 private networks.

Blocked ranges:
  - Loopback: 127.0.0.0/8, ::1
  - RFC-1918 private: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
  - Link-local: 169.254.0.0/16, fe80::/10
  - Cloud metadata: 169.254.169.254 (AWS/GCP/Azure/DO instance metadata)
  - Unspecified: 0.0.0.0/8
"""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status

from core.logging import get_logger

logger = get_logger("ssrf_guard")

# Blocked IP network ranges — RFC-1918, loopback, link-local, metadata
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback (IPv4)
    ipaddress.ip_network("::1/128"),             # Loopback (IPv6)
    ipaddress.ip_network("10.0.0.0/8"),          # RFC-1918 private
    ipaddress.ip_network("172.16.0.0/12"),       # RFC-1918 private
    ipaddress.ip_network("192.168.0.0/16"),      # RFC-1918 private
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / cloud metadata (AWS, GCP, Azure, DO)
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),           # Unspecified
    ipaddress.ip_network("fc00::/7"),            # IPv6 unique local (ULA)
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space (RFC 6598)
]

# High-risk metadata endpoints (belt-and-suspenders — covered by 169.254/16 but explicit)
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "169.254.169.254",
    "metadata.google.com",
    "instance-data.ec2.internal",
}


def _is_blocked_ip(ip_str: str) -> bool:
    """Return True if the resolved IP address falls in a blocked network range."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        return True  # Unparseable IP — block by default


def validate_no_ssrf(url: str) -> None:
    """Validate that a URL does not target private/internal infrastructure.

    Resolves the hostname to its IP address(es) and blocks any that fall into
    private, loopback, link-local, or cloud-metadata ranges.

    Raises HTTP 400 if the URL is unsafe. Call this before every outbound request
    that uses a user-supplied or dynamically-resolved URL.

    Args:
        url: The fully-qualified URL to validate before sending.

    Raises:
        HTTPException: 400 Bad Request if the URL resolves to a blocked IP.
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outbound URL must not be empty.",
        )

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outbound URL has no valid hostname.",
        )

    # Block well-known metadata hostnames directly
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        logger.warning(f"[SSRF BLOCKED] Metadata hostname blocked: {hostname}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outbound request to this URL is not permitted.",
        )

    # Resolve hostname to IP(s) and check against blocked networks
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        logger.warning(f"[SSRF GUARD] DNS resolution failed for '{hostname}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve hostname '{hostname}'.",
        )

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip = sockaddr[0]
        if _is_blocked_ip(ip):
            logger.warning(
                f"[SSRF BLOCKED] Outbound request to private/internal IP blocked: "
                f"hostname={hostname} resolved_ip={ip} url={url}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outbound request to this URL is not permitted (internal IP range).",
            )

    logger.debug(f"[SSRF GUARD] URL passed validation: {url}")
