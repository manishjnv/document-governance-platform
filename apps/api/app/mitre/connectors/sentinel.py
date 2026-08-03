"""Microsoft Sentinel connector (Phase 13a, plan §2.2).

Read-only pull of Sentinel analytics rules via the Azure Management API.
Both endpoints are FIXED Microsoft hosts — the customer supplies only
regex-validated identifiers, never a hostname. Auth is the Entra
client-credentials flow; the client secret exists only as a function
argument for the duration of the pull.

Output is a canonical template CSV (headers chosen from ingest.py's own
COLUMN_SYNONYMS) so the existing create path parses it like any upload.
"""

import csv
import io
import logging
import re
import urllib.parse

from ..ingest import MAX_USE_CASE_ROWS
from .base import ConnectorConfigError, ConnectorError
from .egress import EgressError, fetch_json  # noqa: F401 — EgressError re-exported for callers

logger = logging.getLogger(__name__)

ALLOWED_HOSTS = frozenset({"login.microsoftonline.com", "management.azure.com"})
API_VERSION = "2023-02-01"
MAX_PAGES = 50

_GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
# Azure resource-group naming rules: letters/digits/._-() but never starting
# or ending with a dot — dot-only values like ".." would otherwise splice a
# traversal token into the API path (2026-08-02 adversarial finding #2;
# low exploitability on a fixed host, tightened for defense-in-depth).
_RESOURCE_GROUP = re.compile(r"^(?!\.)[-\w\.\(\)]{1,90}(?<!\.)$")
_WORKSPACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{2,61}[A-Za-z0-9]$")

CONFIG_FIELDS = {
    "tenant_id": (_GUID, "a GUID"),
    "client_id": (_GUID, "a GUID"),
    "subscription_id": (_GUID, "a GUID"),
    "resource_group": (_RESOURCE_GROUP, "an Azure resource-group name"),
    "workspace": (_WORKSPACE, "a Log Analytics workspace name"),
}

_CSV_HEADERS = ["Rule Name", "Description", "Query", "MITRE ATT&CK", "Status", "Log Source"]

# Plan phase A7 — auto-import the workspace's onboarded data connectors so
# Sentinel customers can skip the manual Log Sources sheet. Deliberately
# reads Microsoft.SecurityInsights/dataConnectors (SAME resource provider,
# SAME host, SAME token/scope as the alertRules pull above) rather than the
# Log Analytics workspace "tables" API — the latter needs
# Microsoft.OperationalInsights/workspaces/tables/read, a permission the
# documented "Microsoft Sentinel Reader" role (see MITRE_SIEM_INTEGRATION_
# PLAN.md §2.1) does not grant; dataConnectors is fully covered by that
# same role, so this feature requires NO new customer-side permission.
# Kind values are Microsoft's own built-in Sentinel data-connector
# identifiers (Microsoft Learn: "Sentinel data connectors reference");
# mapped to source NAME STRINGS the module's existing log-source keyword
# bridge (ranking.py's _LOG_SOURCE_RULES) already recognizes, so this adds
# NO new taxonomy. A kind absent from this table is reported, never
# silently dropped (contract point 2).
_DATA_CONNECTOR_KIND_TO_SOURCE = {
    "AzureActiveDirectory": "Azure AD",
    "AzureActiveDirectoryIdentityProtection": "Azure AD",
    "MicrosoftDefenderAdvancedThreatProtection": "Microsoft Defender",
    "MicrosoftThreatProtection": "Microsoft Defender",
    "AzureSecurityCenter": "Azure Security Center",
    "MicrosoftCloudAppSecurity": "Microsoft Defender for Cloud Apps",
    "Office365": "Office 365",
    "OfficeATP": "Office 365",
    "AmazonWebServicesCloudTrail": "AWS CloudTrail",
    "AmazonWebServicesS3": "AWS CloudTrail",
    "SecurityEvents": "Windows Security Events",
    "WindowsSecurityEvents": "Windows Security Events",
    "WindowsFirewall": "Windows Firewall",
    "Dynamics365": "Dynamics 365",
    "DNS": "DNS logs",
    "CiscoASA": "Cisco ASA",
    "PaloAltoNetworks": "Palo Alto",
    "Fortinet": "Fortinet",
    "CheckPoint": "Check Point",
}
MAX_CONNECTORS = 500  # defensive cap — mirrors MAX_PAGES discipline


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ConnectorConfigError("config must be an object")
    normalized, problems = {}, []
    for field, (pattern, label) in CONFIG_FIELDS.items():
        value = str(config.get(field) or "").strip()
        if not value or not pattern.match(value):
            problems.append(f"{field} must be {label}")
        normalized[field] = value
    if problems:
        raise ConnectorConfigError("; ".join(problems))
    return normalized


def _get_token(config: dict, secret: str) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": secret,
            "scope": "https://management.azure.com/.default",
        }
    ).encode("ascii")
    status, payload = fetch_json(
        "login.microsoftonline.com",
        f"/{config['tenant_id']}/oauth2/v2.0/token",
        allowed_hosts=ALLOWED_HOSTS,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    token = payload.get("access_token")
    if status != 200 or not token:
        # deliberately static: upstream error bodies are not echoed
        raise ConnectorError(
            "Azure sign-in failed — check the tenant ID, client ID and client secret"
        )
    return str(token)


def _next_page_path(next_link: str) -> str:
    """Validate a $nextLink URL: must stay https on an allowlisted host."""
    parsed = urllib.parse.urlsplit(str(next_link))
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise EgressError("refusing to contact a host outside the connector allowlist")
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


def _rules_to_csv(rules: list) -> tuple:
    """Sentinel alertRules JSON -> (csv_bytes, warnings). Values are the
    customer's own SIEM data, round-tripped verbatim (same trust stance as
    an uploaded CSV); the XLSX export layer keeps its formula guard."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADERS)
    no_query = 0
    for rule in rules:
        props = rule.get("properties") or {}
        techniques = [
            str(t).strip().upper()
            for t in list(props.get("techniques") or []) + list(props.get("subTechniques") or [])
            if str(t).strip()
        ]
        query = str(props.get("query") or "")
        if not query:
            no_query += 1
        writer.writerow(
            [
                str(props.get("displayName") or rule.get("name") or "").strip(),
                str(props.get("description") or ""),
                query,
                ", ".join(dict.fromkeys(techniques)),
                "Enabled" if props.get("enabled") else "Disabled",
                f"Microsoft Sentinel · {rule.get('kind') or 'rule'}",
            ]
        )
    warnings = []
    if no_query:
        warnings.append(
            f"{no_query} Sentinel rules (Fusion/ML kinds) carry no query text — "
            "they are scored from name/description/tags only"
        )
    return buffer.getvalue().encode("utf-8"), warnings


def pull(config: dict, secret: str) -> dict:
    """Token → paginated alertRules → canonical CSV. Blocking."""
    token = _get_token(config, secret)
    auth_headers = {"Authorization": f"Bearer {token}"}
    path = (
        f"/subscriptions/{config['subscription_id']}"
        f"/resourceGroups/{config['resource_group']}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{config['workspace']}"
        f"/providers/Microsoft.SecurityInsights/alertRules"
        f"?api-version={API_VERSION}"
    )

    rules, warnings, pages = [], [], 0
    while path:
        pages += 1
        if pages > MAX_PAGES:
            warnings.append(
                f"stopped after {MAX_PAGES} pages of rules — the rest were not pulled"
            )
            break
        status, payload = fetch_json(
            "management.azure.com", path, allowed_hosts=ALLOWED_HOSTS, headers=auth_headers
        )
        if status == 401:
            raise ConnectorError("Azure rejected the access token — retry the pull")
        if status == 403:
            raise ConnectorError(
                "the service principal cannot read this workspace — it needs the "
                "'Microsoft Sentinel Reader' role on it"
            )
        if status == 404:
            raise ConnectorError(
                "workspace not found — check the subscription ID, resource group "
                "and workspace name"
            )
        if status != 200:
            raise ConnectorError(
                f"Azure returned an unexpected status ({status}) while listing rules"
            )
        page_rules = payload.get("value")
        if not isinstance(page_rules, list):
            raise ConnectorError("Azure returned an unexpected response while listing rules")
        rules.extend(page_rules)
        if len(rules) >= MAX_USE_CASE_ROWS:
            rules = rules[:MAX_USE_CASE_ROWS]
            warnings.append(
                f"the workspace has more than {MAX_USE_CASE_ROWS:,} rules — only the "
                f"first {MAX_USE_CASE_ROWS:,} were pulled"
            )
            break
        next_link = payload.get("nextLink")
        path = _next_page_path(next_link) if next_link else None

    if not rules:
        raise ConnectorError(
            "the workspace was reachable but contains no analytics rules — check "
            "the workspace reference (a 0-rule assessment would be misleading)"
        )

    csv_bytes, csv_warnings = _rules_to_csv(rules)
    derived_log_sources, unmapped_connectors, dc_warnings = _pull_data_connectors(
        config, auth_headers
    )
    return {
        "csv_bytes": csv_bytes,
        "rule_count": len(rules),
        "warnings": warnings + csv_warnings + dc_warnings,
        "stats": {"pages": pages, "platform": "sentinel"},
        "derived_log_sources": derived_log_sources,
        "unmapped_connectors": unmapped_connectors,
    }


def _pull_data_connectors(config: dict, auth_headers: dict) -> tuple:
    """Plan phase A7: best-effort read of the workspace's onboarded data
    connectors -> (log_sources, unmapped_kind_names, warnings). NEVER
    raises — an inventory-pull failure must not fail the assessment
    (contract point 4); on any error (network, unexpected shape, or a
    malformed/non-dict entry in the response) this degrades to
    ([], [], [one warning]), same as if the workbook simply wasn't
    provided. The whole body is one broad try/except (defense-in-depth
    beyond the specific exceptions anticipated below) precisely because
    it processes an untrusted external API response and this feature must
    never turn into an unhandled 500 that fails the whole assessment."""
    degrade_warning = [
        "could not auto-import log sources from Sentinel (data connector "
        "listing failed) — the Log Sources sheet can still be uploaded manually"
    ]
    try:
        path = (
            f"/subscriptions/{config['subscription_id']}"
            f"/resourceGroups/{config['resource_group']}"
            f"/providers/Microsoft.OperationalInsights/workspaces/{config['workspace']}"
            f"/providers/Microsoft.SecurityInsights/dataConnectors"
            f"?api-version={API_VERSION}"
        )
        status, payload = fetch_json(
            "management.azure.com", path, allowed_hosts=ALLOWED_HOSTS, headers=auth_headers
        )
        if status != 200:
            return [], [], degrade_warning
        connectors = payload.get("value")
        if not isinstance(connectors, list):
            return [], [], degrade_warning

        sources, unmapped, seen = [], [], set()
        for connector in connectors[:MAX_CONNECTORS]:
            if not isinstance(connector, dict):
                continue  # malformed entry -- skip, never crash
            kind = str(connector.get("kind") or "").strip()[:200]
            if not kind:
                continue
            source = _DATA_CONNECTOR_KIND_TO_SOURCE.get(kind)
            if source:
                if source not in seen:
                    seen.add(source)
                    sources.append(source)
            elif kind not in unmapped:
                unmapped.append(kind)
        return sources, unmapped, []
    except Exception as exc:  # noqa: BLE001 — see docstring: must never raise
        logger.warning(
            f"Sentinel data-connector auto-import degraded: {type(exc).__name__}"
        )
        return [], [], degrade_warning
