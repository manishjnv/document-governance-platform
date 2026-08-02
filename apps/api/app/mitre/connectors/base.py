"""SIEM connector dispatch + error contract (Phase 13a, plan §4).

A connector module exposes:
    validate_config(config: dict) -> dict      # normalized, or ConnectorConfigError
    pull(config: dict, secret: str) -> dict    # PullResult, or ConnectorError/EgressError

PullResult = {"csv_bytes": bytes, "rule_count": int, "warnings": [str],
              "stats": {...}} — csv_bytes is a canonical template CSV that
feeds the EXISTING create path (ingest.parse_use_case_file), so tag
validation, preview, caps and the stored artifact all come for free.

Secrets pass through as function arguments only: never stored, never
logged, never embedded in any error message. No LLM anywhere here
(coding-over-AI — mapping happens downstream in the tagging ladder).
"""


class ConnectorConfigError(Exception):
    """Bad/missing connection parameters — the caller's fault (HTTP 422)."""


class ConnectorError(Exception):
    """The pull itself failed upstream (auth, permissions, empty workspace,
    rate limits…) with an actionable, secret-free message (HTTP 502)."""


PLATFORMS = ("sentinel",)


def pull_rules(platform: str, config: dict, secret: str) -> dict:
    """Validate config and run the named connector. Blocking (called via
    run_in_threadpool from the router)."""
    if platform == "sentinel":
        from . import sentinel

        return sentinel.pull(sentinel.validate_config(config), secret)
    raise ConnectorConfigError(
        f"Unknown SIEM platform {str(platform)[:30]!r}. Supported: {', '.join(PLATFORMS)}"
    )
