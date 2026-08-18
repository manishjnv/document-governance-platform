"""SIEM connector dispatch + error contract (Phase 13a, plan §4).

A connector module exposes:
    validate_config(config: dict) -> dict      # normalized, or ConnectorConfigError
    pull(config: dict, secret: str) -> dict    # PullResult, or ConnectorError/EgressError

PullResult = {"csv_bytes": bytes, "rule_count": int, "warnings": [str],
              "stats": {...}, "derived_log_sources": [str],
              "unmapped_connectors": [str]} — csv_bytes is a canonical
template CSV that feeds the EXISTING create path
(ingest.parse_use_case_file), so tag validation, preview, caps and the
stored artifact all come for free. derived_log_sources/unmapped_connectors
(plan phase A7) are the Sentinel connector's best-effort auto-import of
the workspace's onboarded data connectors — always present (possibly
empty), never raise on their own failure.

Secrets pass through as function arguments only: never stored, never
logged, never embedded in any error message. No LLM anywhere here
(coding-over-AI — mapping happens downstream in the tagging ladder).
"""


class ConnectorConfigError(Exception):
    """Bad/missing connection parameters — the caller's fault (HTTP 422)."""


class ConnectorError(Exception):
    """The pull itself failed upstream (auth, permissions, empty workspace,
    rate limits…) with an actionable, secret-free message (HTTP 502)."""


PLATFORMS = ("sentinel", "splunk")

# (short name for auto-generated titles, full vendor name for prose)
PLATFORM_LABELS = {
    "sentinel": ("Sentinel", "Microsoft Sentinel"),
    "splunk": ("Splunk", "Splunk"),
}


def _module(platform: str):
    if platform == "sentinel":
        from . import sentinel

        return sentinel
    if platform == "splunk":
        from . import splunk

        return splunk
    raise ConnectorConfigError(
        f"Unknown SIEM platform {str(platform)[:30]!r}. Supported: {', '.join(PLATFORMS)}"
    )


def validate_config(platform: str, config: dict) -> dict:
    """Validate/normalize config without pulling (saved-connection CRUD)."""
    return _module(platform).validate_config(config)


def pull_rules(platform: str, config: dict, secret: str) -> dict:
    """Validate config and run the named connector. Blocking (called via
    run_in_threadpool from the router)."""
    module = _module(platform)
    return module.pull(module.validate_config(config), secret)
