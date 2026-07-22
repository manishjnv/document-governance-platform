"""Conflict detector orchestration (Phase C2) -- LLM call is mocked; these
test the conversion to violations, the org gate, and failure degradation."""

from unittest.mock import AsyncMock

import pytest

from app.ai.orchestrator import ReviewOrchestrator

_FAKE_CONFLICTS = {
    "conflicts": [
        {
            "section_a": "5. Service Levels",
            "quote_a": "99.9% platform availability",
            "section_b": "12. Open Items",
            "quote_b": "availability target to be finalized",
            "explanation": "A committed availability target cannot also be unfinalized.",
            "severity": "major",
            "confidence": 0.8,
        },
        # Half a conflict (one quote missing) must be dropped, not persisted.
        {"section_a": "x", "quote_a": "only one side", "explanation": "?", "severity": "low"},
    ],
    "overall_confidence": 0.8,
}


def _orchestrator_with_mocked_detector(review_result):
    orchestrator = ReviewOrchestrator()
    detector = AsyncMock()
    detector.review = AsyncMock(return_value=review_result)
    orchestrator._conflict_detector = detector
    return orchestrator


@pytest.mark.asyncio
async def test_conflicts_become_typed_violations():
    orchestrator = _orchestrator_with_mocked_detector(_FAKE_CONFLICTS)
    violations = await orchestrator._run_conflict_scan("doc text", enabled_rule_ids=None)

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "CONFLICT-1"
    assert v.evidence_type == "conflict"
    assert "99.9%" in v.matched_text and "finalized" in v.matched_text
    assert v.severity.value == "major"


@pytest.mark.asyncio
async def test_conflict_scan_disabled_by_org_gate():
    orchestrator = _orchestrator_with_mocked_detector(_FAKE_CONFLICTS)
    violations = await orchestrator._run_conflict_scan("doc text", enabled_rule_ids={"SOW-001"})
    assert violations == []
    orchestrator._conflict_detector.review.assert_not_called()


@pytest.mark.asyncio
async def test_conflict_scan_failure_degrades_to_empty():
    orchestrator = ReviewOrchestrator()
    detector = AsyncMock()
    detector.review = AsyncMock(side_effect=RuntimeError("provider down"))
    orchestrator._conflict_detector = detector
    violations = await orchestrator._run_conflict_scan("doc text", enabled_rule_ids=None)
    assert violations == []


@pytest.mark.asyncio
async def test_empty_conflicts_is_normal():
    orchestrator = _orchestrator_with_mocked_detector({"conflicts": [], "overall_confidence": 0.9})
    assert await orchestrator._run_conflict_scan("doc text", enabled_rule_ids=None) == []
