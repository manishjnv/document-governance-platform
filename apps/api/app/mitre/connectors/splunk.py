"""Splunk connector (plan §6 follow-up, built 2026-08-18).

Read-only pull of saved searches via the Splunk REST API
(`GET /servicesNS/-/{app}/saved/searches`). This is the first connector
where the customer supplies a hostname (Sentinel's endpoints are fixed
Microsoft domains) — exactly the case MITRE_SIEM_INTEGRATION_PLAN.md §6
anticipated for the egress guard's deny set. Defenses, in order:

- **Strict host shape**: a bare lowercase FQDN only — no scheme, port,
  path, userinfo or wildcard; the value is used verbatim as the per-call
  egress allowlist entry.
- **Port limited to 8089/443**: 8089 is Splunk's management port (the
  REST API default, incl. Splunk Cloud); 443 covers proxied setups.
- **Shared egress guard** (`egress.fetch_json`): resolve-then-pin with
  the public-IP-only deny set, TLS verification against the hostname,
  redirects rejected, response/time caps — this is what actually stops
  SSRF/rebinding for a customer-supplied name.

Auth is a Splunk authentication token (Settings → Tokens), sent as a
Bearer header; it exists only as a function argument for the duration of
the pull. Output is the canonical template CSV (same contract as
sentinel.py) so the existing create path parses it like any upload.
MITRE tags come from the ES correlation-search annotations field when
present; untagged rules flow into the existing tagging ladder downstream.

NOTE: shipped ahead of a reachable customer Splunk environment — the
code path is complete and unit-tested against faked transports; first
live use just needs a real host + token (and, for Splunk Cloud, the
ScopeWise egress IP allowlisted on the stack's management port).
"""

import csv
import io
import json
import re
import urllib.parse

from ..ingest import MAX_USE_CASE_ROWS
from .base import ConnectorConfigError, ConnectorError
from .egress import fetch_json

# bare FQDN, per-label rules (no leading/trailing hyphen), dot required —
# single-label names (intranet hosts) are refused up front; the egress
# deny set remains the real enforcement for whatever resolves.
_HOST = re.compile(
    r"^(?=.{4,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"
    r"(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)
# app goes into the URL path: never starting/ending with a dot so ".."
# can't splice a traversal token (same posture as sentinel's
# resource-group fix, 2026-08-02 adversarial finding #2).
_APP = re.compile(r"^(?!\.)[A-Za-z0-9_.\-]{1,100}(?<!\.)$")
ALLOWED_PORTS = (8089, 443)

PAGE_SIZE = 100
MAX_PAGES = 50  # x PAGE_SIZE = MAX_USE_CASE_ROWS

_CSV_HEADERS = ["Rule Name", "Description", "Query", "MITRE ATT&CK", "Status", "Log Source"]


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ConnectorConfigError("config must be an object")
    problems = []
    host = str(config.get("host") or "").strip().lower().rstrip(".")
    if not _HOST.match(host):
        problems.append(
            "host must be a bare DNS name like acme.splunkcloud.com "
            "(no scheme, port or path)"
        )
    try:
        port = int(config.get("port") or 8089)
    except (TypeError, ValueError):
        port = -1
    if port not in ALLOWED_PORTS:
        problems.append("port must be 8089 (Splunk management port) or 443")
    app = str(config.get("app") or "-").strip()
    if app != "-" and not _APP.match(app):
        problems.append("app must be a Splunk app name (letters, digits, _ . -)")
    if problems:
        raise ConnectorConfigError("; ".join(problems))
    return {"host": host, "port": port, "app": app}


def _technique_ids(raw) -> list:
    """ES correlation-search annotations JSON -> ATT&CK technique IDs
    (regex fallback for malformed JSON — seen in real Splunk exports).
    IDs pass through verbatim; build_mappings/resolve() validates them
    downstream exactly like customer-supplied tags."""
    if not raw:
        return []
    try:
        ids = [str(t).strip().upper() for t in json.loads(raw).get("mitre_attack") or []]
        ids = [t for t in ids if t]
    except Exception:
        ids = []
    if not ids:
        ids = re.findall(r"T\d{4}(?:\.\d{3})?", str(raw))
    return list(dict.fromkeys(ids))


def _entries_to_csv(entries: list) -> tuple:
    """Splunk saved-search entries -> (csv_bytes, warnings). Values are the
    customer's own SIEM data, round-tripped verbatim (same trust stance as
    an uploaded CSV); the XLSX export layer keeps its formula guard."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADERS)
    no_query = 0
    for entry in entries:
        content = entry.get("content") or {}
        acl = entry.get("acl") or {}
        query = str(content.get("search") or "")
        if not query:
            no_query += 1
        disabled = str(content.get("disabled")).strip().lower() in ("1", "true")
        writer.writerow(
            [
                str(entry.get("name") or "").strip(),
                str(content.get("description") or ""),
                query,
                ", ".join(_technique_ids(content.get("action.correlationsearch.annotations"))),
                "Disabled" if disabled else "Enabled",
                f"Splunk · {acl.get('app') or 'saved search'}",
            ]
        )
    warnings = []
    if no_query:
        warnings.append(
            f"{no_query} saved searches carry no query text — they are scored "
            "from name/description/tags only"
        )
    return buffer.getvalue().encode("utf-8"), warnings


def pull(config: dict, secret: str) -> dict:
    """Paginated saved-searches listing → canonical CSV. Blocking."""
    host = config["host"]
    allowed = frozenset({host})
    headers = {"Authorization": f"Bearer {secret}"}
    base_path = f"/servicesNS/-/{urllib.parse.quote(config['app'], safe='')}/saved/searches"

    entries, warnings, pages, offset = [], [], 0, 0
    while True:
        pages += 1
        if pages > MAX_PAGES:
            warnings.append(
                f"stopped after {MAX_PAGES} pages of saved searches — the rest "
                "were not pulled"
            )
            break
        status, payload = fetch_json(
            host,
            f"{base_path}?output_mode=json&count={PAGE_SIZE}&offset={offset}",
            allowed_hosts=allowed,
            headers=headers,
            port=config["port"],
        )
        if status == 401:
            raise ConnectorError(
                "Splunk rejected the token — check it is valid and not expired"
            )
        if status == 403:
            raise ConnectorError(
                "the token's role cannot list saved searches — it needs read "
                "access to them"
            )
        if status == 404:
            raise ConnectorError(
                "saved-searches endpoint not found — check the app name"
            )
        if status != 200:
            raise ConnectorError(
                f"Splunk returned an unexpected status ({status}) while listing "
                "saved searches"
            )
        page_entries = payload.get("entry")
        if not isinstance(page_entries, list):
            raise ConnectorError(
                "Splunk returned an unexpected response while listing saved searches"
            )
        entries.extend(page_entries)
        if len(entries) >= MAX_USE_CASE_ROWS:
            entries = entries[:MAX_USE_CASE_ROWS]
            warnings.append(
                f"the instance has more than {MAX_USE_CASE_ROWS:,} saved searches "
                f"— only the first {MAX_USE_CASE_ROWS:,} were pulled"
            )
            break
        total = (payload.get("paging") or {}).get("total")
        offset += len(page_entries)
        if not page_entries or not isinstance(total, int) or offset >= total:
            break

    if not entries:
        raise ConnectorError(
            "Splunk was reachable but returned no saved searches — check the "
            "app scope (a 0-rule assessment would be misleading)"
        )

    csv_bytes, csv_warnings = _entries_to_csv(entries)
    return {
        "csv_bytes": csv_bytes,
        "rule_count": len(entries),
        "warnings": warnings + csv_warnings,
        "stats": {"pages": pages, "platform": "splunk"},
        # contract: always present; Splunk has no data-connector inventory
        # equivalent worth auto-importing in v1 (index names live in the
        # SPL itself and feed the downstream log-source keyword bridge).
        "derived_log_sources": [],
        "unmapped_connectors": [],
    }
