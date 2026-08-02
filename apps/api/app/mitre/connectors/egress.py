"""Guarded outbound HTTP for SIEM connectors (Phase 13a, plan §2.4).

This is the ONLY outbound-HTTP door for connector code. Security
properties, in order of importance:

- **Host allowlist**: every request names a host that must be in the
  caller's explicit allowlist (v1: fixed Microsoft domains — customers
  never supply a hostname at all).
- **Resolve-then-pin**: the hostname is resolved ONCE, EVERY resolved
  address is validated (public/global unicast only — RFC-1918,
  loopback, link-local incl. 169.254.169.254, CGNAT, reserved,
  multicast and their v6/v4-mapped equivalents all refused), and the
  TCP connection goes to the validated IP while TLS SNI + certificate
  verification still run against the original hostname. Rejecting at
  connect time, not parse time, closes the DNS-rebinding TOCTOU.
- **https/443 only** — scheme and port are not parameters.
- **Redirects are errors** (the Azure APIs never need them; a 3xx from
  a pinned host is suspicious by definition).
- **Caps**: connect/read timeouts, a total per-request deadline (slow
  drip counts as failure), 20MB response cap, bounded retries only for
  429/5xx with a capped Retry-After.
- **Secret-free errors**: EgressError messages are static/user-safe and
  never embed request bodies, headers, or upstream response text.

Stdlib only (http.client + ssl + socket) — a pinned socket is exactly
the control we need and no HTTP library dependency gets to re-resolve.
"""

import http.client
import ipaddress
import json
import logging
import math
import socket
import ssl
import time

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10          # seconds, TCP + TLS + per-socket-op
TOTAL_DEADLINE = 60           # seconds, whole request incl. body read
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_ATTEMPTS = 3              # retries only for 429/502/503/504
RETRY_AFTER_CAP = 10          # seconds we are willing to honor per wait
_CHUNK = 65536


class EgressError(Exception):
    """Transport-level failure with a user-safe, secret-free message."""


def _validated_ip(host: str) -> str:
    """Resolve `host` and return one publicly-routable IP, or raise.

    ALL resolved addresses must be global unicast — if even one is
    private/reserved, the host is refused outright (a rebinding name
    that mixes public and private answers must not win by racing)."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise EgressError(f"could not resolve {host} — check network/DNS")
    if not infos:
        raise EgressError(f"could not resolve {host} — check network/DNS")
    candidates = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            ip = mapped
        if ip.is_multicast or not ip.is_global:
            raise EgressError(
                f"{host} resolves to a non-public address — refusing to connect"
            )
        candidates.append(str(ip))
    ipv4 = [c for c in candidates if ":" not in c]
    return (ipv4 or candidates)[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection whose TCP socket goes to a pre-validated IP while
    SNI + certificate verification still use the real hostname."""

    def __init__(self, host: str, pinned_ip: str):
        super().__init__(host, 443, timeout=CONNECT_TIMEOUT)
        self._pinned_ip = pinned_ip
        self._pin_context = ssl.create_default_context()

    def connect(self):  # noqa: D102 — pinned override, see class docstring
        raw = socket.create_connection(
            (self._pinned_ip, 443), timeout=CONNECT_TIMEOUT
        )
        self.sock = self._pin_context.wrap_socket(raw, server_hostname=self.host)


def _read_capped(response, deadline: float) -> bytes:
    chunks, total = [], 0
    while True:
        if time.monotonic() > deadline:
            raise EgressError("the service responded too slowly — try again later")
        chunk = response.read(_CHUNK)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise EgressError("the service response was unreasonably large — aborted")
        chunks.append(chunk)


def fetch_json(
    host: str,
    path: str,
    *,
    allowed_hosts: frozenset,
    method: str = "GET",
    headers: dict = None,
    body: bytes = None,
) -> tuple:
    """One guarded HTTPS request. Returns (status_code, parsed_json_dict).

    Raises EgressError for: host not allowlisted, non-public resolution,
    network/TLS failure, redirect, oversize/slow response, unparseable
    JSON, or retries exhausted on 429/5xx. 4xx statuses are RETURNED
    (the connector maps them to actionable messages)."""
    host = str(host or "").strip().lower()
    if host not in allowed_hosts:
        # allowlists are hardcoded per connector; hitting this means a bug
        # or a hostile nextLink — never connect.
        raise EgressError("refusing to contact a host outside the connector allowlist")

    pinned_ip = _validated_ip(host)
    last_status = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        deadline = time.monotonic() + TOTAL_DEADLINE
        conn = _PinnedHTTPSConnection(host, pinned_ip)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            status = response.status
            if 300 <= status < 400:
                raise EgressError("the service sent an unexpected redirect — aborted")
            payload = _read_capped(response, deadline)
        except EgressError:
            raise
        except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
            logger.warning(f"egress to {host} failed (attempt {attempt}): {type(exc).__name__}")
            raise EgressError(f"could not reach {host} — network or TLS failure")
        finally:
            conn.close()

        if status in (429, 502, 503, 504) and attempt < MAX_ATTEMPTS:
            retry_after = response.getheader("Retry-After")
            try:
                # header is attacker-influenced: clamp to [0, cap] and refuse
                # NaN/inf — float("-5")/float("nan") parse fine but would
                # crash time.sleep (2026-08-02 adversarial finding #1)
                wait = float(retry_after)
                if not math.isfinite(wait):
                    raise ValueError
                wait = max(0.0, min(wait, RETRY_AFTER_CAP))
            except (TypeError, ValueError):
                wait = min(2 * attempt, RETRY_AFTER_CAP)
            last_status = status
            time.sleep(wait)
            continue

        try:
            parsed = json.loads(payload.decode("utf-8")) if payload else {}
        except (ValueError, UnicodeDecodeError):
            raise EgressError(f"{host} returned a response that is not valid JSON")
        if not isinstance(parsed, dict):
            raise EgressError(f"{host} returned an unexpected response shape")
        return status, parsed

    raise EgressError(
        f"{host} kept rate-limiting or failing (last status {last_status}) — try again later"
    )
