from __future__ import annotations

import ipaddress
import socket
import time
from datetime import datetime, timezone
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .domain import PageSnapshot


class URLValidationError(ValueError):
    pass


class FetchError(RuntimeError):
    pass


def normalize_url(url: str) -> str:
    value = url.strip()
    if not value:
        raise URLValidationError("URL is empty.")
    if "://" not in value:
        value = "https://" + value
    return value


def _is_blocked_ip(ip_value: str) -> bool:
    ip = ipaddress.ip_address(ip_value)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str, *, allow_private: bool = False) -> str:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise URLValidationError("Only HTTP and HTTPS URLs are allowed.")
    if not parsed.hostname:
        raise URLValidationError("URL must include a host.")

    host = parsed.hostname.strip().lower()
    if not allow_private and host in {"localhost", "localhost.localdomain"}:
        raise URLValidationError("Localhost URLs are blocked.")

    try:
        if _is_blocked_ip(host):
            if not allow_private:
                raise URLValidationError("Private and local IP addresses are blocked.")
            return normalized
    except ValueError:
        pass

    if allow_private:
        return normalized

    try:
        addresses = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise URLValidationError(f"Could not resolve host: {host}") from exc

    for family, _, _, _, sockaddr in addresses:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        ip_value = sockaddr[0]
        if _is_blocked_ip(ip_value):
            raise URLValidationError("URL resolves to a private or local address.")

    return normalized


class SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow_private: bool):
        self.allow_private = allow_private
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        validate_public_url(newurl, allow_private=self.allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _charset_from_content_type(headers: Message) -> str:
    content_type = headers.get("Content-Type", "")
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip() or "utf-8"
    return "utf-8"


def fetch_url(
    url: str,
    *,
    timeout_seconds: int,
    max_bytes: int,
    allow_private: bool = False,
) -> PageSnapshot:
    safe_url = validate_public_url(url, allow_private=allow_private)
    request = Request(
        safe_url,
        headers={
            "User-Agent": (
                "InteractivePublicationExpert/0.1 "
                "(educational UX analysis prototype)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    opener = build_opener(SafeRedirectHandler(allow_private))
    started = time.perf_counter()

    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise FetchError(f"Response is larger than {max_bytes} bytes.")
            charset = _charset_from_content_type(response.headers)
            html = raw.decode(charset, errors="replace")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return PageSnapshot(
                requested_url=safe_url,
                final_url=response.geturl(),
                status_code=getattr(response, "status", None),
                content_type=response.headers.get("Content-Type", ""),
                html=html,
                elapsed_ms=elapsed_ms,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )
    except HTTPError as exc:
        raise FetchError(f"HTTP error {exc.code} while fetching URL.") from exc
    except URLError as exc:
        raise FetchError(f"Network error while fetching URL: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError("Timeout while fetching URL.") from exc
