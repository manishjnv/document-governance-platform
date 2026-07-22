"""Broken internal-reference detector (app/rules/references.py, Phase C1)."""

import pytest

from app.rules.references import scan_references

_SECTIONS = {
    "1. Purpose": "Why we are here.",
    "5. Service Levels": "SLA text.",
    "5.2 Escalation": "Escalation text.",
    "17. Appendix A - Initial Log Sources": "Log source list.",
    "18. Appendix B - Example Resource Plan": "Resource table.",
}


def test_dangling_appendix_reference_fires():
    text = "Ownership is defined in the RACI matrix in Appendix C. See Appendix B for staffing."
    violations = scan_references(text, _SECTIONS)
    ids = {v.rule_id for v in violations}
    assert "REF-appendix-c" in ids
    v = next(v for v in violations if v.rule_id == "REF-appendix-c")
    assert v.evidence_type == "reference"
    assert "Appendix C" in v.matched_text
    assert v.severity.value == "major"


def test_existing_appendix_reference_is_silent():
    text = "See Appendix B for the resource plan, and Appendix A for log sources."
    assert scan_references(text, _SECTIONS) == []


def test_case_and_format_variants():
    # lowercase reference to an existing appendix: silent
    assert scan_references("see appendix a for details.", _SECTIONS) == []
    # lowercase reference to a missing exhibit: fires
    violations = scan_references("as described in exhibit d.", _SECTIONS)
    assert [v.rule_id for v in violations] == ["REF-exhibit-d"]


def test_section_references_verified_against_heading_numbers():
    assert scan_references("As stated in Section 5.2, escalation applies.", _SECTIONS) == []
    violations = scan_references("Refer to Section 9 for pricing.", _SECTIONS)
    assert [v.rule_id for v in violations] == ["REF-section-9"]


def test_statutory_section_citations_are_ignored():
    text = "The service must meet Section 508 accessibility requirements."
    assert scan_references(text, _SECTIONS) == []


def test_doc_without_numbered_headings_skips_section_checks():
    sections = {"Overview": "x", "Appendix A": "y"}
    assert scan_references("See Section 3 for details.", sections) == []


def test_duplicate_dangling_references_reported_once():
    text = "See Appendix C. As noted, Appendix C defines ownership. Appendix C again."
    violations = scan_references(text, _SECTIONS)
    assert len(violations) == 1


def test_empty_text_returns_empty():
    assert scan_references("", _SECTIONS) == []


@pytest.mark.asyncio
async def test_orchestrator_gates_reference_scan_on_ref_scan_id():
    from unittest.mock import AsyncMock

    from app.ai.orchestrator import ReviewOrchestrator

    orchestrator = ReviewOrchestrator()
    orchestrator.initialized = True
    for agent in orchestrator.agents:
        agent.initialize = AsyncMock()
        agent.review = AsyncMock(return_value={"findings": [], "overall_confidence": 0.9})

    text = "Ownership is defined in Appendix C."
    sections = {"1. Purpose": "x"}

    # Enabled (REF-SCAN present): dangling reference surfaces.
    result = await orchestrator.review(
        "doc-1", text, sections=sections, enabled_rule_ids={"REF-SCAN"}, enabled_agent_names=set()
    )
    assert any(v["rule_id"] == "REF-appendix-c" for v in result.rule_violations)
    ref = next(v for v in result.rule_violations if v["rule_id"] == "REF-appendix-c")
    assert ref["evidence_type"] == "reference"

    # Disabled (org turned it off): silent.
    result = await orchestrator.review(
        "doc-1", text, sections=sections, enabled_rule_ids=set(), enabled_agent_names=set()
    )
    assert not any(v["rule_id"].startswith("REF-") for v in result.rule_violations)
