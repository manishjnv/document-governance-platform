"""Deterministic document risk prediction based on findings."""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ponytail: heuristic risk score; swap for a trained model once T-2031's pipeline
# has real labeled outcome data. Severity weights are domain-derived, not learned.
SEVERITY_WEIGHTS = {
    "critical": 10,
    "major": 5,
    "medium": 2,
    "low": 1,
    "info": 0,
}


def predict_document_risk(findings: list[dict]) -> dict:
    """
    Predict document risk using a deterministic heuristic based on finding severity.

    Args:
        findings: List of finding dicts with 'severity' key

    Returns:
        {
            "risk_score": float (0-100),
            "risk_band": "low" | "medium" | "high" | "critical",
            "basis": "heuristic",
            "finding_count_by_severity": {"critical": 1, "major": 2, ...}
        }
    """
    if not findings:
        return {
            "risk_score": 0.0,
            "risk_band": "low",
            "basis": "heuristic",
            "finding_count_by_severity": {},
        }

    # Count findings by severity
    severity_counts = defaultdict(int)
    total_weight = 0

    for finding in findings:
        severity = finding.get("severity", "info").lower()
        severity_counts[severity] += 1
        weight = SEVERITY_WEIGHTS.get(severity, 0)
        total_weight += weight

    # Map weight to 0-100 scale
    # Maximum possible: e.g., 100 critical findings * 10 = 1000
    # We normalize to 100-point scale with ceiling at ~50-60 critical issues
    # Formula: min(100, (total_weight / 50) * 100)
    max_reasonable_weight = 50  # e.g., 5 critical + 5 major = 50 weight = risk_score 100
    risk_score = min(100.0, (total_weight / max_reasonable_weight) * 100.0)

    # Map to risk band
    if risk_score < 20:
        risk_band = "low"
    elif risk_score < 50:
        risk_band = "medium"
    elif risk_score < 80:
        risk_band = "high"
    else:
        risk_band = "critical"

    return {
        "risk_score": round(risk_score, 2),
        "risk_band": risk_band,
        "basis": "heuristic",
        "finding_count_by_severity": dict(severity_counts),
    }
