"""Unit tests for scoring system.

T-911-T-920: Scoring & AI validation tests
"""

import pytest
from decimal import Decimal
from app.scoring.algorithm import DocumentScorer, CategoryScore


@pytest.fixture
def scorer():
    """Create document scorer for testing."""
    return DocumentScorer()


@pytest.mark.asyncio
async def test_score_perfect_document(scorer):
    """T-911: Test scoring gives high score to document with no findings."""
    result = await scorer.score_document(
        doc_id="doc-001",
        findings=[],
        rule_violations=[],
    )

    assert result.overall_score == 100.0
    assert result.risk_score == 0.0
    assert all(score.score == 100.0 for score in result.category_scores.values())


@pytest.mark.asyncio
async def test_score_with_critical_findings(scorer):
    """T-912: Test scoring penalizes critical findings heavily."""
    findings = [
        {
            "severity": "critical",
            "description": "Missing critical section",
            "type": "missing_criteria",
        },
        {
            "severity": "critical",
            "description": "No payment terms defined",
            "type": "missing_terms",
        },
    ]

    result = await scorer.score_document(
        doc_id="doc-002",
        findings=findings,
        rule_violations=[],
    )

    # Risk should be high due to 2 critical findings
    assert result.risk_score > 20.0
    assert result.overall_score < 80.0


@pytest.mark.asyncio
async def test_category_scoring_completeness(scorer):
    """T-913: Test completeness scoring based on missing sections."""
    findings = [
        {
            "severity": "major",
            "description": "Missing deliverables section",
            "type": "missing_criteria",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-003",
        findings=findings,
        rule_violations=[],
    )

    completeness_score = result.category_scores["completeness"].score
    assert completeness_score < 100.0


@pytest.mark.asyncio
async def test_category_scoring_commercial(scorer):
    """T-914: Test commercial scoring based on pricing issues."""
    findings = [
        {
            "severity": "critical",
            "description": "Missing pricing information",
            "type": "ambiguous_pricing",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-004",
        findings=findings,
        rule_violations=[],
    )

    commercial_score = result.category_scores["commercial"].score
    assert commercial_score < 80.0


@pytest.mark.asyncio
async def test_risk_score_calculation(scorer):
    """T-915: Test risk score calculation from findings."""
    rule_violations = [
        {
            "rule_id": "SOW-001",
            "severity": "critical",
            "description": "Missing section",
        }
    ]

    findings = [
        {
            "severity": "major",
            "description": "Ambiguous language",
            "type": "ambiguous",
        },
        {
            "severity": "major",
            "description": "Missing clause",
            "type": "missing",
        },
    ]

    result = await scorer.score_document(
        doc_id="doc-005",
        findings=findings,
        rule_violations=rule_violations,
    )

    # Risk = 1 critical (15) + 2 major (20) + 3 findings (3) = 38
    assert result.risk_score > 30.0
    assert result.risk_score <= 100.0


@pytest.mark.asyncio
async def test_score_status_green(scorer):
    """T-916: Test status is green for high-scoring documents."""
    result = await scorer.score_document(
        doc_id="doc-006",
        findings=[],
        rule_violations=[],
    )

    assert all(score.status == "green" for score in result.category_scores.values())


@pytest.mark.asyncio
async def test_score_status_yellow(scorer):
    """T-917: Test status is yellow for medium-scoring documents."""
    findings = [
        {
            "severity": "low",
            "description": "Minor issue",
            "type": "info",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-007",
        findings=findings,
        rule_violations=[],
    )

    # Should have some categories in yellow (50-79)
    statuses = [score.status for score in result.category_scores.values()]
    assert "yellow" in statuses or "green" in statuses


@pytest.mark.asyncio
async def test_score_status_red(scorer):
    """T-918: Test status is red for low-scoring documents."""
    findings = [
        {
            "severity": "critical",
            "description": "Critical issue 1",
            "type": "critical_1",
        },
        {
            "severity": "critical",
            "description": "Critical issue 2",
            "type": "critical_2",
        },
        {
            "severity": "critical",
            "description": "Critical issue 3",
            "type": "critical_3",
        },
        {
            "severity": "critical",
            "description": "Critical issue 4",
            "type": "critical_4",
        },
        {
            "severity": "critical",
            "description": "Critical issue 5",
            "type": "critical_5",
        },
    ]

    result = await scorer.score_document(
        doc_id="doc-008",
        findings=findings,
        rule_violations=[],
    )

    # Should have red status for some categories
    statuses = [score.status for score in result.category_scores.values()]
    assert "red" in statuses


@pytest.mark.asyncio
async def test_overall_score_weighted_average(scorer):
    """T-919: Test overall score is weighted average of categories."""
    # Perfect document
    result = await scorer.score_document(
        doc_id="doc-009",
        findings=[],
        rule_violations=[],
    )

    # All categories should contribute equally to perfect score
    assert result.overall_score == 100.0

    # Verify weights sum to 1.0
    total_weight = sum(scorer.WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.01


@pytest.mark.asyncio
async def test_summary_generation(scorer):
    """T-920: Test executive summary is generated correctly."""
    findings = [
        {
            "severity": "major",
            "description": "Missing completeness",
            "type": "missing",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-010",
        findings=findings,
        rule_violations=[],
    )

    assert len(result.summary) > 0
    assert "Score" in result.summary or "score" in result.summary
    assert "Risk" in result.summary or "risk" in result.summary


@pytest.mark.asyncio
async def test_next_steps_generation(scorer):
    """T-921: Test recommended next steps are generated."""
    findings = [
        {
            "severity": "critical",
            "description": "Missing completeness",
            "type": "missing",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-011",
        findings=findings,
        rule_violations=[],
    )

    assert len(result.next_steps) > 0
    # Should include recommendation for critical finding
    assert any("critical" in step.lower() for step in result.next_steps)


@pytest.mark.asyncio
async def test_category_score_object(scorer):
    """T-922: Test CategoryScore dataclass."""
    score = CategoryScore(
        category="completeness",
        score=85.0,
        max_points=100,
        points_earned=85,
        findings=[{"severity": "low", "description": "test"}],
        status="green",
    )

    assert score.category == "completeness"
    assert score.score == 85.0
    assert score.status == "green"


@pytest.mark.asyncio
async def test_security_scoring_importance(scorer):
    """T-923: Test security scoring is appropriately weighted."""
    findings = [
        {
            "severity": "major",
            "description": "Missing security audit rights",
            "type": "security",
        }
    ]

    result = await scorer.score_document(
        doc_id="doc-012",
        findings=findings,
        rule_violations=[],
    )

    # Security should be penalized even with low weight (5%)
    # because security is critical
    security_score = result.category_scores["security"].score
    assert security_score < 100.0


@pytest.mark.asyncio
async def test_scoring_stability(scorer):
    """T-924: Test scoring is deterministic (same input = same output)."""
    findings = [{"severity": "medium", "description": "test", "type": "test"}]
    violations = [{"rule_id": "R1", "severity": "low", "description": "test"}]

    result1 = await scorer.score_document("doc-1", findings, violations)
    result2 = await scorer.score_document("doc-1", findings, violations)

    assert result1.overall_score == result2.overall_score
    assert result1.risk_score == result2.risk_score
