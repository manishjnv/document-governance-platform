"""Tests that the orchestrator actually wires the 2026-07-17 additions
(PMOReviewer, LegalReviewer, ambiguous-language scan, document_type
threading to agents) rather than just having the pieces exist in
isolation. Complements test_org_customization_wiring.py.
"""

from unittest.mock import AsyncMock

import pytest

from app.ai.orchestrator import ReviewOrchestrator, ReviewResult


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

    # Typed evidence (migration 027): the ambiguous-language scan quotes the
    # offending sentence, so it must carry location evidence + matched_text.
    ambig = next(v for v in result.rule_violations if v["rule_id"] == "AMBIG-tbd")
    assert ambig["evidence_type"] == "location"
    assert "TBD" in ambig["matched_text"]


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


class TestAgentTimeoutRetry:
    """2026-07-20: a live smoke test found a different agent randomly
    hitting the 60s ceiling on each of 2 runs against real OpenRouter
    output -- response-latency variance, not a per-agent problem. One
    retry at a longer window should recover a transient timeout instead
    of losing that agent's findings entirely."""

    @pytest.mark.asyncio
    async def test_recovers_on_first_attempt_timeout(self, monkeypatch):
        import asyncio

        orchestrator = ReviewOrchestrator()
        agent = AsyncMock()
        agent.name = "FlakyReviewer"

        calls = {"count": 0}

        async def flaky_review(document_text, document_type="SOW"):
            calls["count"] += 1
            if calls["count"] == 1:
                await asyncio.sleep(10)  # will be cut short by a patched timeout
            return {"findings": [], "overall_confidence": 0.8}

        agent.review = flaky_review
        monkeypatch.setattr(orchestrator, "_AGENT_TIMEOUTS_SECONDS", (0.05, 5.0))

        result = await orchestrator._run_agent(agent, "some text", "SOW")

        assert result.error is None
        assert calls["count"] == 2
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_reports_timeout_error_after_all_retries_exhausted(self, monkeypatch):
        import asyncio

        orchestrator = ReviewOrchestrator()
        agent = AsyncMock()
        agent.name = "AlwaysSlowReviewer"

        async def always_slow_review(document_text, document_type="SOW"):
            await asyncio.sleep(10)

        agent.review = always_slow_review
        monkeypatch.setattr(orchestrator, "_AGENT_TIMEOUTS_SECONDS", (0.05, 0.05))

        result = await orchestrator._run_agent(agent, "some text", "SOW")

        assert result.error == "timeout"
        assert result.confidence == 0.0


def _result(agent_name, findings):
    return ReviewResult(
        agent_name=agent_name, findings={"findings": findings}, confidence=0.9, duration_seconds=1.0
    )


class TestFindingDeduplication:
    """Metric 1.4: same issue reported by multiple agents merges into one
    finding, with combined evidence and the higher confidence kept.
    Distinct issues (including ones from the same agent) must never merge."""

    def test_cross_agent_duplicate_is_merged(self):
        orchestrator = ReviewOrchestrator()
        shared_evidence = "Vendor shall not be liable for damages exceeding fees paid in the prior 12 months."
        results = [
            _result(
                "CommercialReviewer",
                [
                    {
                        "type": "missing_liability_cap",
                        "severity": "major",
                        "description": "Liability cap is present but narrow.",
                        "evidence": shared_evidence,
                        "recommendation": "Confirm cap amount is acceptable.",
                        "confidence": 0.7,
                    }
                ],
            ),
            _result(
                "LegalReviewer",
                [
                    {
                        "type": "liability_limitation",
                        "severity": "critical",
                        "description": "Liability limitation clause found, review carve-outs.",
                        "evidence": shared_evidence,
                        "recommendation": "Check carve-out list.",
                        "confidence": 0.85,
                    }
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)

        assert len(merged["findings"]) == 1
        finding = merged["findings"][0]
        assert finding["confidence"] == 0.85
        assert finding["severity"] == "critical"
        assert finding["source_agent"] == "CommercialReviewer, LegalReviewer"

    def test_distinct_findings_are_not_merged(self):
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "ScopeReviewer",
                [
                    {
                        "type": "missing_criteria",
                        "severity": "medium",
                        "description": "No acceptance criteria for deliverable 2.",
                        "evidence": "Deliverable 2: ongoing support services as needed by client.",
                        "recommendation": "Add measurable acceptance criteria.",
                        "confidence": 0.6,
                    }
                ],
            ),
            _result(
                "SecurityReviewer",
                [
                    {
                        "type": "missing_data_handling",
                        "severity": "major",
                        "description": "No data handling or access control language present.",
                        "evidence": "All work will be performed remotely by vendor staff.",
                        "recommendation": "Add data handling and access control requirements.",
                        "confidence": 0.75,
                    }
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)

        assert len(merged["findings"]) == 2

    def test_same_agent_findings_are_never_merged(self):
        """Two findings from the SAME agent quoting the same evidence stay
        separate -- that's a candidate prompt/parsing bug worth surfacing,
        not cross-agent corroboration to collapse."""
        orchestrator = ReviewOrchestrator()
        evidence = "Payment terms: net 30 days from invoice date, no late fee specified."
        results = [
            _result(
                "CommercialReviewer",
                [
                    {
                        "type": "missing_late_fee",
                        "severity": "medium",
                        "description": "No late payment fee specified.",
                        "evidence": evidence,
                        "recommendation": "Add a late fee clause.",
                        "confidence": 0.6,
                    },
                    {
                        "type": "payment_term_ambiguous",
                        "severity": "low",
                        "description": "Payment terms could be clearer.",
                        "evidence": evidence,
                        "recommendation": "Clarify payment terms.",
                        "confidence": 0.5,
                    },
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)

        assert len(merged["findings"]) == 2

    def test_self_negating_finding_is_dropped_before_persistence(self):
        """2026-07-22 baseline FP: SecurityReviewer emitted "Missing
        Accessibility Standard" whose own description said the requirement
        is not applicable. Such findings must be filtered at ingestion."""
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "SecurityReviewer",
                [
                    {
                        "type": "missing_accessibility",
                        "severity": "low",
                        "description": "Accessibility standard (Section 508) is not applicable to this SOW as there is no public-facing deliverable.",
                        "evidence": "No public-facing deliverable described.",
                        "recommendation": "None needed.",
                        "confidence": 0.6,
                    },
                    {
                        "type": "missing_breach_notification",
                        "severity": "major",
                        "description": "No breach notification timeline is defined.",
                        "evidence": "Security section covers monitoring only, no incident notification clause.",
                        "recommendation": "Add a 72-hour breach notification requirement.",
                        "confidence": 0.7,
                    },
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)

        assert len(merged["findings"]) == 1
        assert merged["findings"][0]["type"] == "missing_breach_notification"

    def test_negated_compliance_finding_is_kept(self):
        """"is not compliant" is a real problem, not a self-negation --
        the filter must not over-match."""
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "SecurityReviewer",
                [
                    {
                        "type": "compliance_gap",
                        "severity": "critical",
                        "description": "The data-handling clause is not compliant with the stated ISO 27001 requirement.",
                        "evidence": "Data may be stored in vendor-selected regions without restriction.",
                        "recommendation": "Constrain storage regions.",
                        "confidence": 0.8,
                    }
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)
        assert len(merged["findings"]) == 1

    @pytest.mark.parametrize(
        "description",
        [
            # Hedged compliance question = real gap finding, must survive.
            "The SOW does not state whether the vendor is compliant with ISO 27001.",
            # Clean-bill clause followed by a contrast carrying a real issue.
            "No issues found in section 3 but section 4 lacks a termination clause.",
        ],
    )
    def test_hedged_or_contrasted_findings_survive_the_filter(self, description):
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "LegalReviewer",
                [
                    {
                        "type": "gap",
                        "severity": "major",
                        "description": description,
                        "evidence": "Relevant section text long enough to matter here.",
                        "recommendation": "Address the gap.",
                        "confidence": 0.7,
                    }
                ],
            ),
        ]
        merged = orchestrator._merge_findings(results)
        assert len(merged["findings"]) == 1, f"wrongly dropped: {description!r}"

    def test_unhedged_clean_bill_is_dropped(self):
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "SecurityReviewer",
                [
                    {
                        "type": "compliance_check",
                        "severity": "low",
                        "description": "The document is fully compliant with the stated ISO 27001 requirement.",
                        "evidence": "Compliance clause quoted verbatim from section 9.",
                        "recommendation": "None.",
                        "confidence": 0.9,
                    }
                ],
            ),
        ]
        merged = orchestrator._merge_findings(results)
        assert merged["findings"] == []

    def test_short_or_missing_evidence_is_never_merged(self):
        """Findings with no evidence, or evidence too short to compare
        reliably, must never be merged -- avoids false merges on generic
        short phrases (the launch criteria's 0-false-merge requirement)."""
        orchestrator = ReviewOrchestrator()
        results = [
            _result(
                "ScopeReviewer",
                [
                    {
                        "type": "vague_language",
                        "severity": "low",
                        "description": "Uses vague language.",
                        "evidence": "TBD",
                        "recommendation": "Clarify.",
                        "confidence": 0.5,
                    }
                ],
            ),
            _result(
                "PMOReviewer",
                [
                    {
                        "type": "vague_language",
                        "severity": "low",
                        "description": "Also vague.",
                        "evidence": "TBD",
                        "recommendation": "Clarify.",
                        "confidence": 0.55,
                    }
                ],
            ),
            _result(
                "LegalReviewer",
                [
                    {
                        "type": "no_governing_law",
                        "severity": "medium",
                        "description": "No governing law clause found.",
                        "evidence": None,
                        "recommendation": "Add a governing law clause.",
                        "confidence": 0.65,
                    }
                ],
            ),
        ]

        merged = orchestrator._merge_findings(results)

        assert len(merged["findings"]) == 3
