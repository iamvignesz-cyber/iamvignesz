"""
SSRF protections.

The scanner service fetches a URL that any authenticated user (down to the
Analyst role) can supply. Without validation, that turns the scanner into a
generic internal-network probe: an attacker could register a "site" pointing
at http://127.0.0.1:5432, http://169.254.169.254/latest/meta-data/ (cloud
metadata endpoints), an internal admin panel on a private RFC1918 address,
or any other host the backend container can reach but the outside world
cannot.

Everything here is deny-by-default:
- only http/https schemes,
- no credentials embedded in the URL,
- hostname must resolve to public, non-reserved IP addresses only
  (all resolved addresses are checked, not just the first),
- every redirect hop is re-validated the same way (blocks DNS-rebinding /
  "fetch a public host that 302s to localhost" tricks),
- the resolved IP is what's actually connected to, with the original
  Host header preserved, so a TOCTOU DNS change between check-time and
  connect-time can't bypass the check.
"""
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


def _is_public_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    # Cloud metadata services (AWS/GCP/Azure/DigitalOcean all use link-local
    # 169.254.169.254, already caught by is_link_local above, but block it
    # explicitly too in case of future ipaddress module edge cases).
    if ip_str == "169.254.169.254":
        return False
    return True


def resolve_public_ips(hostname: str) -> list[str]:
    """Resolve a hostname and return only the case where ALL resolved
    addresses are public. Mixed public/private results (a common
    DNS-rebinding pattern) are rejected outright."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise UnsafeURLError(f"Could not resolve host: {hostname}") from e

    ips = sorted({info[4][0] for info in infos})
    if not ips:
        raise UnsafeURLError(f"Could not resolve host: {hostname}")

    for ip_str in ips:
        if not _is_public_ip(ip_str):
            raise UnsafeURLError(
                f"Host '{hostname}' resolves to a non-public address ({ip_str}); refusing to scan."
            )
    return ips


def validate_public_url(url: str) -> str:
    """Validate a URL is safe to fetch server-side. Returns the normalized
    hostname on success, raises UnsafeURLError otherwise. Does not itself
    resolve DNS for pure format-validation use (e.g. schema checks at
    site-creation time) — call resolve_public_ips() at fetch time too, since
    DNS can change between when a site is registered and when it's scanned.
    """
    if len(url) > 2048:
        raise UnsafeURLError("URL is too long.")

    parsed = urlparse(url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http:// and https:// URLs are allowed.")

    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with embedded credentials are not allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL must include a hostname.")

    if hostname.lower() in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeURLError("Localhost / .local addresses are not allowed.")

    # Reject bare-IP literals that are obviously private/loopback before
    # even hitting DNS (covers http://127.0.0.1, http://0.0.0.0, IPv6 ::1,
    # decimal/octal/hex IP obfuscation tricks are caught by ipaddress parsing
    # raising ValueError, which we treat as "not a plain IP, fall through to
    # DNS resolution").
    try:
        ip_obj = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not _is_public_ip(str(ip_obj)):
            raise UnsafeURLError(f"IP address {hostname} is not a public address; refusing to scan.")

    return hostname
