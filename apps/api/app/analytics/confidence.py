"""Add confidence intervals to risk predictions.

T-2035: Confidence intervals on risk/completeness predictions
"""

import logging

logger = logging.getLogger(__name__)


def add_confidence_interval(risk_score: float, finding_count: int) -> dict:
    """
    Compute confidence bounds on a risk score based on evidence (finding count).

    ponytail: heuristic interval width, not a statistically derived confidence
    interval — a real one needs labeled outcome data (same gap as T-2031/T-2032's
    risk heuristic). Current approach: fewer findings → wider margin,
    more findings → tighter interval.

    Args:
        risk_score: Risk score from predict_document_risk (0-100)
        finding_count: Number of findings supporting the risk estimate

    Returns:
        {
            "risk_score": float,
            "lower_bound": float (0-100, clamped),
            "upper_bound": float (0-100, clamped),
            "confidence": "low" | "medium" | "high",
        }
    """
    # Heuristic: start with margin of 30 - (3 * finding_count)
    # E.g. 0 findings -> ±30, 5 findings -> ±15, 10+ findings -> ±0
    # Clamp to [0, 30]
    margin = max(0, min(30, 30 - finding_count * 3))

    lower = max(0.0, risk_score - margin)
    upper = min(100.0, risk_score + margin)

    # Confidence label based on finding count
    if finding_count < 3:
        confidence = "low"
    elif finding_count < 8:
        confidence = "medium"
    else:
        confidence = "high"

    logger.debug(
        f"Risk {risk_score}: {finding_count} findings → "
        f"[{lower:.1f}, {upper:.1f}] ({confidence})"
    )

    return {
        "risk_score": float(risk_score),
        "lower_bound": round(lower, 2),
        "upper_bound": round(upper, 2),
        "confidence": confidence,
    }
