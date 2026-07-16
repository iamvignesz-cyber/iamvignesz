"""
Real, non-AI vulnerability checks. These are deterministic HTTP/TLS inspections —
NOT dressed up as AI. AI is used separately (services/ai.py) only to summarize
and prioritize what this scanner finds, per the BYOK rule.

SSRF hardening: the scanner fetches a URL supplied by an authenticated user
(analyst+ role), so it is treated as untrusted input. See app/core/net_security.py
for the validation rules. Fetches are pinned to a pre-validated IP address
(rather than letting the HTTP client re-resolve DNS at connect time) to close
the DNS-rebinding TOCTOU window, and every redirect hop is re-validated before
being followed.
"""
import hashlib
import ssl
import socket
import asyncio
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import settings
from app.core.net_security import UnsafeURLError, resolve_public_ips, validate_public_url

SECURITY_HEADERS = [
    "content-security-policy",
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]


def _pinned_url(url: str, ip: str) -> str:
    """Rewrite a URL's host to a specific IP while leaving scheme/port/path
    intact, so the HTTP client connects to an address we've already vetted
    instead of re-resolving DNS (which an attacker could change between
    our check and the actual connection)."""
    parsed = urlparse(url)
    port_part = f":{parsed.port}" if parsed.port else ""
    host_part = f"[{ip}]" if ":" in ip else ip  # bracket IPv6 literals
    netloc = f"{host_part}{port_part}"
    return urlunparse(parsed._replace(netloc=netloc))


async def _safe_get(url: str, max_hops: int = None) -> httpx.Response:
    """Fetch a URL with SSRF protections: validates + resolves the host,
    connects to the pinned IP with the correct SNI/Host, caps response size,
    and re-validates every redirect target before following it."""
    max_hops = settings.SCAN_MAX_REDIRECTS if max_hops is None else max_hops
    current_url = url
    last_response = None

    timeout = httpx.Timeout(
        settings.SCAN_TOTAL_TIMEOUT_SECONDS, connect=settings.SCAN_CONNECT_TIMEOUT_SECONDS
    )

    for _ in range(max_hops + 1):
        # current_url always carries the *real* hostname (never the pinned
        # IP) so that Host headers, SNI, and relative-redirect resolution
        # stay correct across hops.
        hostname = validate_public_url(current_url)
        ips = await asyncio.to_thread(resolve_public_ips, hostname)
        pinned = _pinned_url(current_url, ips[0])

        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, verify=True) as client:
            request = client.build_request("GET", pinned, headers={"Host": hostname})
            # Preserve TLS SNI / cert validation against the real hostname even
            # though we're connecting by IP.
            request.extensions["sni_hostname"] = hostname
            response = await client.send(request, stream=True)
            try:
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > settings.SCAN_MAX_RESPONSE_BYTES:
                        raise ValueError("Response exceeded maximum allowed size for scanning.")
            finally:
                await response.aclose()
            response._content = body  # populate .content/.text after manual streaming

        last_response = response
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                break
            # Resolve relative redirects against the logical (real-hostname)
            # URL, not the pinned IP URL, then loop back to re-validate the
            # new target from scratch before following it.
            current_url = str(httpx.URL(current_url).join(location))
            continue
        break

    if last_response is None:
        raise UnsafeURLError("No response received.")
    return last_response


def check_headers(headers: httpx.Headers) -> dict:
    lower_headers = {k.lower(): v for k, v in headers.items()}
    findings = {}
    for h in SECURITY_HEADERS:
        findings[h] = {"present": h in lower_headers, "value": lower_headers.get(h)}
    # Cookie security
    set_cookie = lower_headers.get("set-cookie", "")
    findings["cookie_secure"] = "secure" in set_cookie.lower()
    findings["cookie_httponly"] = "httponly" in set_cookie.lower()
    return findings


def check_cors(headers: httpx.Headers) -> dict:
    acao = headers.get("access-control-allow-origin")
    return {"access_control_allow_origin": acao, "wildcard_risk": acao == "*"}


def check_ssl_expiry(hostname: str, ip: str) -> dict:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip, 443), timeout=settings.SCAN_CONNECT_TIMEOUT_SECONDS) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days_left = (not_after - datetime.utcnow()).days
        return {"valid": True, "expires": not_after.isoformat(), "days_left": days_left}
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def run_full_scan(url: str) -> dict:
    result = {"url": url, "scanned_at": datetime.utcnow().isoformat()}

    try:
        hostname = validate_public_url(url)
    except UnsafeURLError as e:
        result["fetch_error"] = str(e)
        result["ssl"] = {"valid": False, "error": "Scan blocked before fetch."}
        return result

    parsed = urlparse(url)

    try:
        resp = await _safe_get(url)
        result["status_code"] = resp.status_code
        result["headers"] = check_headers(resp.headers)
        result["cors"] = check_cors(resp.headers)
        result["html_hash"] = hashlib.sha256(resp.content).hexdigest()
        result["content_length"] = len(resp.content)
    except (UnsafeURLError, httpx.HTTPError, ValueError) as e:
        result["fetch_error"] = str(e)

    if parsed.scheme == "https":
        try:
            ips = await asyncio.to_thread(resolve_public_ips, hostname)
            result["ssl"] = await asyncio.to_thread(check_ssl_expiry, hostname, ips[0])
        except UnsafeURLError as e:
            result["ssl"] = {"valid": False, "error": str(e)}
    else:
        result["ssl"] = {"valid": False, "error": "Not served over HTTPS"}

    return result


def score_from_scan(scan: dict) -> int:
    """Simple deterministic point-based scoring — transparent, not a black box."""
    score = 100
    headers = scan.get("headers", {})
    for h in SECURITY_HEADERS:
        if not headers.get(h, {}).get("present"):
            score -= 8
    if scan.get("cors", {}).get("wildcard_risk"):
        score -= 15
    ssl_info = scan.get("ssl", {})
    if not ssl_info.get("valid"):
        score -= 20
    elif ssl_info.get("days_left", 999) < 14:
        score -= 10
    if not headers.get("cookie_secure"):
        score -= 5
    if not headers.get("cookie_httponly"):
        score -= 5
    return max(score, 0)
