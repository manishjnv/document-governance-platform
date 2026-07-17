"""Tests that the orchestrator actually wires the 2026-07-17 additions
(PMOReviewer, LegalReviewer, ambiguous-language scan, document_type
threading to agents) rather than just having the pieces exist in
isolation. Complements test_org_customization_wiring.py.
"""

from unittest.mock import AsyncMock

import pytest

from app.ai.orchestrator import ReviewOrchestrator


@pytest.mark.asyncio
async def test_all_six_agents_registered():
    orchestrator = ReviewOrchestrator()
    names = {a.name for a in orchestrator.agents}
    assert names == {
        "ScopeReviewer",
        "DeliveryReviewer",
        "CommercialReviewer",
        "SecurityReviewer",
        "PMOReviewer",
        "LegalReviewer",
    }


@pytest.mark.asyncio
async def test_document_type_is_passed_through_to_each_agent():
    orchestrator = ReviewOrchestrator()
    orchestrator.initialized = True

    received_document_types = {}

    def make_review(agent_name):
        async def _review(document_text, document_type="SOW"):
            received_document_types[agent_name] = document_type
            return {"findings": [], "overall_confidence": 0.9}

        return _review

    for agent in orchestrator.agents:
        agent.initialize = AsyncMock()
        agent.review = make_review(agent.name)

    await orchestrator.review(
        "doc-1", "some RFP text", document_type="RFP", enabled_rule_ids=set()
    )

    assert received_document_types == {name: "RFP" for name in received_document_types}
    assert set(received_document_types) == {a.name for a in orchestrator.agents}


@pytest.mark.asyncio
async def test_ambiguous_language_findings_land_in_rule_violations():
    orchestrator = ReviewOrchestrator()
    orchestrator.initialized = True

    for agent in orchestrator.agents:
        agent.initialize = AsyncMock()
        agent.review = AsyncMock(return_value={"findings": [], "overall_confidence": 0.9})

    doc_text = "Final pricing: TBD. Vendor will respond promptly to all requests."

    result = await orchestrator.review(
        "doc-1", doc_text, enabled_rule_ids=set(), enabled_agent_names=set()
    )

    # enabled_rule_ids=set() disables the built-in rule engine, but the
    # ambiguous-language scan is not gated by it -- it should still surface.
    ambig_ids = {v["rule_id"] for v in result.rule_violations if v["rule_id"].startswith("AMBIG-")}
    assert "AMBIG-tbd" in ambig_ids
    assert "AMBIG-promptly" in ambig_ids


@pytest.mark.asyncio
async def test_ambiguous_language_scan_handles_empty_text_without_crashing():
    """_run_ambiguous_language_scan must not raise on missing document text
    -- a doc with a failed parse (parsed_text=None) still goes through
    orchestrator.review() in app/routers/reviews.py (`doc.parsed_text or ""`),
    so the scan needs to degrade gracefully, not take down the whole review."""
    orchestrator = ReviewOrchestrator()
    violations = await orchestrator._run_ambiguous_language_scan("", {})
    assert violations == []


@pytest.mark.asyncio
async def test_ambiguous_language_scan_failure_does_not_break_review(monkeypatch):
    """_run_ambiguous_language_scan catches exceptions and returns []
    (matching _run_rule_engine's existing fallback contract) so a scanner
    bug can't take down the whole orchestrated review."""
    import app.rules.ambiguous_language as ambiguous_language_module

    def _boom(*args, **kwargs):
        raise RuntimeError("scanner exploded")

    monkeypatch.setattr(ambiguous_language_module, "scan_ambiguous_language", _boom)

    orchestrator = ReviewOrchestrator()
    violations = await orchestrator._run_ambiguous_language_scan("some text", {})
    assert violations == []
