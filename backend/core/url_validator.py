"""
URL Validator — SSRF protection.

Blocks:
  - Non-HTTP(S) schemes  (file://, ftp://, data://, …)
  - Private IPv4 ranges  (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)
  - IPv6 loopback/link-local
  - Bare hostnames with no TLD (e.g. "http://internal")
  - Reserved / special hostnames (localhost, metadata endpoints)

Usage
─────
    from core.url_validator import validate_url
    safe_url = validate_url(raw_url)   # raises ValueError on bad input
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

# ── Blocked hostnames ─────────────────────────────────────
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "metadata.google.internal",     # GCP metadata
        "169.254.169.254",              # AWS / Azure metadata (IP form)
        "fd00::ec2",                    # AWS IPv6 metadata
        "0.0.0.0",
    }
)

# ── Private IPv4 ranges ───────────────────────────────────
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / metadata
    ipaddress.ip_network("100.64.0.0/10"),    # shared address space
    ipaddress.ip_network("0.0.0.0/8"),
]


def _is_private_ip(host: str) -> bool:
    """Return True if `host` resolves to a private / reserved address."""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Not a bare IP — resolve it
        try:
            resolved = socket.gethostbyname(host)
            addr = ipaddress.ip_address(resolved)
        except (socket.gaierror, ValueError):
            # Can't resolve → treat as safe (Playwright will fail gracefully)
            return False

    if addr.is_loopback or addr.is_link_local or addr.is_private:
        return True
    for net in _PRIVATE_NETWORKS:
        if addr in net:
            return True
    return False


def validate_url(raw: str) -> str:
    """
    Validate and normalise a user-supplied URL for automation.

    Returns the cleaned URL string on success.
    Raises ValueError with a human-readable message on failure.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("URL must be a non-empty string.")

    raw = raw.strip()

    # Must start with http:// or https://
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Only http:// and https:// URLs are allowed. Got: '{parsed.scheme}://'."
        )

    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must include a hostname.")

    # Block known dangerous hostnames
    if host.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Hostname '{host}' is not allowed.")

    # Block bare single-label hostnames (no dot → likely internal)
    if "." not in host and not _looks_like_ip(host):
        raise ValueError(
            f"Hostname '{host}' looks like an internal name. Use a fully-qualified domain."
        )

    # Block private / loopback IPs
    if _is_private_ip(host):
        raise ValueError(
            f"Hostname '{host}' resolves to a private or reserved IP address."
        )

    return raw


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
