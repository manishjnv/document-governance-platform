"""Unit checks that per-org customization (app/admin/customization.py) is
actually enforced by the rule engine, scoring algorithm, and AI orchestrator,
not just persisted. See PHASE_2_WAVE2_SUMMARY.md's "Next steps" -- this
closes that gap for app/routers/reviews.py::trigger_review.
"""

from unittest.mock import AsyncMock

import pytest

from app.ai.orchestrator import ReviewOrchestrator
from app.rules.engine import Rule, RuleExecutor, RuleSeverity
from app.scoring.algorithm import DocumentScorer


@pytest.mark.asyncio
async def test_rule_executor_enabled_rule_ids_filters_rules():
    executor = RuleExecutor()
    executor.register_rule(
        Rule(
            rule_id="R1", name="Requires Foo", description="d", document_types=["*"],
            severity=RuleSeverity.CRITICAL, check_type="keyword",
            params={"keywords": ["foo"]}, recommendation="add foo",
        )
    )
    executor.register_rule(
        Rule(
            rule_id="R2", name="Requires Bar", description="d", document_types=["*"],
            severity=RuleSeverity.CRITICAL, check_type="keyword",
            params={"keywords": ["bar"]}, recommendation="add bar",
        )
    )
    text = "neither keyword present"

    unrestricted = await executor.validate(text, "SOW")
    assert {v.rule_id for v in unrestricted} == {"R1", "R2"}

    only_r1 = await executor.validate(text, "SOW", enabled_rule_ids={"R1"})
    assert {v.rule_id for v in only_r1} == {"R1"}

    none_enabled = await executor.validate(text, "SOW", enabled_rule_ids=set())
    assert none_enabled == []


@pytest.mark.asyncio
async def test_document_scorer_weight_overrides_change_overall_score():
    default_scorer = DocumentScorer()
    overridden_scorer = DocumentScorer(weight_overrides={"security": 1.0, "completeness": 0.0})

    findings = []
    violations = []

    default_result = await default_scorer.score_document("doc-1", findings, violations)
    overridden_result = await overridden_scorer.score_document("doc-1", findings, violations)

    assert overridden_scorer.weights["security"] == 1.0
    assert default_scorer.weights == DocumentScorer.WEIGHTS
    # No findings/violations -> every category scores 100, so overall_score
    # is just 100 * sum(weights) -- proves _calculate_overall_score actually
    # reads the per-instance override, not the class-level WEIGHTS default.
    assert default_result.overall_score == pytest.approx(100 * sum(DocumentScorer.WEIGHTS.values()))
    assert overridden_result.overall_score == pytest.approx(100 * sum(overridden_scorer.weights.values()))
    assert overridden_result.overall_score != default_result.overall_score


@pytest.mark.asyncio
async def test_orchestrator_enabled_agent_names_filters_agents():
    orchestrator = ReviewOrchestrator()
    orchestrator.initialized = True  # skip real Anthropic client init

    for agent in orchestrator.agents:
        agent.initialize = AsyncMock()
        agent.review = AsyncMock(return_value={"findings": [], "overall_confidence": 0.9})

    all_names = {a.name for a in orchestrator.agents}
    keep_one = {next(iter(all_names))}

    result = await orchestrator.review(
        "doc-1", "some text", enabled_agent_names=keep_one, enabled_rule_ids=set()
    )

    assert {r.agent_name for r in result.results} == keep_one
    assert result.rule_violations == []
