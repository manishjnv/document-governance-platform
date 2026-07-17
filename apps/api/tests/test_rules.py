"""Unit tests for rule engine.

T-901-T-910: Unit & integration tests
"""

import pytest
from app.rules.engine import RuleExecutor, Rule, RuleSeverity, RuleViolation


@pytest.fixture
def executor():
    """Create rule executor for testing."""
    return RuleExecutor()


def test_section_presence_violation(executor):
    """T-902: Test section presence check detects missing sections."""
    rule = Rule(
        rule_id="TEST-001",
        name="Test Section Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="section_presence",
        params={"required_sections": ["Executive Summary"]},
        recommendation="Add executive summary",
    )

    executor.register_rule(rule)

    # Document missing section. _check_section_presence returns a single
    # Optional[RuleViolation] (see test_section_presence_pass below), not a
    # list -- matching every other _check_* method's contract with validate().
    violation = executor._check_section_presence(rule, {})
    assert violation is not None
    assert "missing section" in violation.evidence.lower()


def test_section_presence_pass(executor):
    """T-902: Test section presence check passes when section exists."""
    rule = Rule(
        rule_id="TEST-002",
        name="Test Section Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="section_presence",
        params={"required_sections": ["Executive Summary"]},
        recommendation="Add executive summary",
    )

    executor.register_rule(rule)

    # Document has section
    sections = {"Executive Summary": "This is an executive summary"}
    violations = executor._check_section_presence(rule, sections)
    assert violations is None


def test_word_count_violation(executor):
    """T-903: Test word count check detects insufficient content."""
    rule = Rule(
        rule_id="TEST-003",
        name="Test Word Count Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.MAJOR,
        check_type="word_count",
        params={"required_sections": ["Scope"], "min_words": 100},
        recommendation="Expand scope section",
    )

    executor.register_rule(rule)

    # Section with too few words
    sections = {"scope": "This is short"}
    violations = executor._check_word_count(rule, sections, "")
    assert violations is not None
    assert "only" in violations.evidence.lower() and "words" in violations.evidence.lower()


def test_keyword_check_pass(executor):
    """T-904: Test keyword check passes when keywords present."""
    rule = Rule(
        rule_id="TEST-004",
        name="Payment Terms Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="keyword",
        params={"keywords": ["net 30", "payment"]},
        recommendation="Add payment terms",
    )

    executor.register_rule(rule)

    doc_text = "Payment is due Net 30 from invoice date"
    violations = executor._check_keyword(rule, doc_text)
    assert violations is None


def test_keyword_check_violation(executor):
    """T-904: Test keyword check detects missing keywords."""
    rule = Rule(
        rule_id="TEST-005",
        name="Payment Terms Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="keyword",
        params={"keywords": ["net 30"]},
        recommendation="Add payment terms",
    )

    executor.register_rule(rule)

    doc_text = "This document has no payment terms specified"
    violations = executor._check_keyword(rule, doc_text)
    assert violations is not None
    assert "missing keyword" in violations.evidence.lower()


def test_regex_pattern_match(executor):
    """T-905: Test regex pattern check with matching pattern."""
    rule = Rule(
        rule_id="TEST-006",
        name="Date Pattern Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="regex",
        params={
            "pattern": r"\d{4}-\d{2}-\d{2}",
            "should_match": True,
        },
        recommendation="Add date in YYYY-MM-DD format",
    )

    executor.register_rule(rule)

    doc_text = "Project start date: 2024-01-15"
    violations = executor._check_regex(rule, doc_text)
    assert violations is None


def test_regex_pattern_violation(executor):
    """T-905: Test regex pattern check with missing pattern."""
    rule = Rule(
        rule_id="TEST-007",
        name="Date Pattern Rule",
        description="Test rule",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="regex",
        params={
            "pattern": r"\d{4}-\d{2}-\d{2}",
            "should_match": True,
        },
        recommendation="Add date in YYYY-MM-DD format",
    )

    executor.register_rule(rule)

    doc_text = "Project start date: January 15th"
    violations = executor._check_regex(rule, doc_text)
    assert violations is not None


@pytest.mark.asyncio
async def test_validate_document(executor):
    """T-906: Test full document validation against rules."""
    rule1 = Rule(
        rule_id="RULE-001",
        name="Section Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="section_presence",
        params={"required_sections": ["Scope", "Pricing"]},
        recommendation="Add sections",
    )

    rule2 = Rule(
        rule_id="RULE-002",
        name="Keyword Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.MAJOR,
        check_type="keyword",
        params={"keywords": ["net 30"]},
        recommendation="Add payment terms",
    )

    executor.register_rule(rule1)
    executor.register_rule(rule2)

    doc_text = "Scope: Project delivery. Pricing: Fixed at $10000. Payment: Net 30."
    sections = {
        "scope": "Project delivery",
        "pricing": "Fixed at $10000",
    }

    violations = await executor.validate(doc_text, "SOW", sections)

    # Should pass rule1 (sections exist) and rule2 (keyword exists)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_validate_document_with_violations(executor):
    """T-907: Test document validation detects violations.

    "match": "all" here because this rule genuinely means "both Scope AND
    Pricing sections required" (two distinct sections), unlike every real
    builtin rule's multi-item list which means "any one of these synonym
    headings" (default "any" as of the 2026-07-17 engine fix -- see
    _check_section_presence's docstring).
    """
    rule = Rule(
        rule_id="RULE-003",
        name="Scope Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="section_presence",
        params={"required_sections": ["Scope", "Pricing"], "match": "all"},
        recommendation="Add required sections",
    )

    executor.register_rule(rule)

    # Missing "Pricing" section
    doc_text = "Scope: Project delivery"
    sections = {"scope": "Project delivery"}

    violations = await executor.validate(doc_text, "SOW", sections)

    assert len(violations) == 1
    assert violations[0].rule_id == "RULE-003"
    assert violations[0].severity == RuleSeverity.CRITICAL


def test_rule_document_type_filtering(executor):
    """T-908: Test rules only apply to matching document types."""
    rule = Rule(
        rule_id="SOW-RULE",
        name="SOW Rule",
        description="Test",
        document_types=["SOW"],  # Only applies to SOW
        severity=RuleSeverity.MAJOR,
        check_type="keyword",
        params={"keywords": ["deliverables"]},
        recommendation="Add deliverables",
    )

    executor.register_rule(rule)

    # Must genuinely lack the keyword "deliverables" -- the original text
    # ironically contained it as a substring, so _check_keyword (correctly)
    # found no violation and this test failed on its own broken fixture.
    doc_text = "This is a proposal that lacks a concrete outputs section"
    sections = {}

    # Should not apply to Proposal type
    violations = executor._check_keyword(rule, doc_text)
    # The check itself runs, but wouldn't be selected by validate() for Proposal type
    assert violations is not None  # The check itself finds a violation


def test_rule_severity_levels(executor):
    """T-909: Test all severity levels are properly set."""
    for severity in ["critical", "major", "medium", "low", "info"]:
        rule = Rule(
            rule_id=f"RULE-{severity}",
            name=f"{severity.title()} Rule",
            description="Test",
            document_types=["SOW"],
            severity=RuleSeverity(severity),
            check_type="keyword",
            params={"keywords": ["test"]},
            recommendation="Test",
        )

        assert rule.severity.value == severity


def test_section_presence_synonym_any_one_alias_satisfies_by_default(executor):
    """Regression for the 2026-07-17 precision bug: a document using only
    ONE of several synonym headings (e.g. "Overview" instead of "Executive
    Summary") must NOT be flagged as missing the section -- the previous
    all-must-be-present behavior made SOW-001-style rules fire "missing
    section" on essentially every real document."""
    rule = Rule(
        rule_id="TEST-SYN-001",
        name="Synonym Section Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.MAJOR,
        check_type="section_presence",
        params={"required_sections": ["Executive Summary", "Overview", "Summary"]},
        recommendation="Add an overview section",
    )
    executor.register_rule(rule)

    # Document only has "Overview", not the other two aliases.
    violation = executor._check_section_presence(rule, {"Overview": "text"})
    assert violation is None


def test_keyword_synonym_any_one_keyword_satisfies_by_default(executor):
    """Same regression, keyword check: a document using only ONE of several
    synonym phrasings (e.g. "Net 60" instead of "Net 30") must not be
    flagged as missing payment terms."""
    rule = Rule(
        rule_id="TEST-SYN-002",
        name="Synonym Keyword Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="keyword",
        params={"keywords": ["net 30", "net 60", "net 90", "payment terms", "due upon", "invoice"]},
        recommendation="Add payment terms",
    )
    executor.register_rule(rule)

    violation = executor._check_keyword(rule, "Payment is due Net 60 from invoice date... wait, due upon receipt actually")
    # (deliberately only "net 60" and "due upon"/"invoice" overlap here to
    # prove partial coverage is enough, not exhaustive -- but even a single
    # match should already suffice)
    assert violation is None

    violation_single = executor._check_keyword(rule, "Payment is due Net 60 only, nothing else mentioned.")
    assert violation_single is None


def test_section_presence_match_all_still_requires_every_entry(executor):
    """Opt-in "all" mode (for genuinely distinct co-required sections, not
    synonyms) still requires every entry."""
    rule = Rule(
        rule_id="TEST-ALL-001",
        name="Distinct Sections Rule",
        description="Test",
        document_types=["SOW"],
        severity=RuleSeverity.CRITICAL,
        check_type="section_presence",
        params={"required_sections": ["Scope", "Pricing"], "match": "all"},
        recommendation="Add both sections",
    )
    executor.register_rule(rule)

    assert executor._check_section_presence(rule, {"scope": "x", "pricing": "y"}) is None
    assert executor._check_section_presence(rule, {"scope": "x"}) is not None


def test_rule_recommendation_guidance(executor):
    """T-910: Test rule recommendations are clear and actionable."""
    rule = Rule(
        rule_id="TEST-REC",
        name="Test Rule",
        description="Missing acceptance criteria",
        document_types=["SOW"],
        severity=RuleSeverity.MAJOR,
        check_type="keyword",
        params={"keywords": ["acceptance criteria"]},
        recommendation="Add clear acceptance criteria for each deliverable",
    )

    executor.register_rule(rule)

    assert len(rule.recommendation) > 10  # Recommendation should be helpful
    assert "acceptance criteria" in rule.recommendation.lower() or "deliverable" in rule.recommendation.lower()
