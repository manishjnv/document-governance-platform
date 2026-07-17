"""Tests for the ambiguous-language detector (app/rules/ambiguous_language.py).

docs/planning/4_AI_AGENT_SPECS.md "Cross-Cutting: Ambiguous Language
Detector". Deterministic regex scan, not an LLM -- so precision/recall/dedup
(Metrics 1.1/1.2/1.4) are computed exactly against a hand-built set, same
approach as tests/test_rfp_rules.py.
"""

from app.rules.ambiguous_language import _PHRASE_FAMILIES, scan_ambiguous_language
from app.rules.engine import RuleSeverity


def test_detects_every_phrase_family_at_least_once():
    """Metric 1.2 (recall): every phrase family in the spec's list must be
    individually detectable -- build one sentence per phrase and confirm
    each fires exactly once."""
    for phrase, _severity in _PHRASE_FAMILIES:
        doc = f"The vendor will handle this using {phrase} as described."
        violations = scan_ambiguous_language(doc)
        matched = [v for v in violations if phrase in v.evidence.lower()]
        assert matched, f"phrase family '{phrase}' was not detected"


def test_clean_document_produces_zero_false_positives():
    """Metric 1.1 (precision): a document containing none of the phrase
    families must return zero violations."""
    doc = (
        "The vendor will deliver the migration by 2026-09-30, with 99.9% "
        "uptime guaranteed and a fixed price of $50,000 payable Net 30."
    )
    assert scan_ambiguous_language(doc) == []


def test_dedup_per_sentence_two_phrases_same_sentence_collapse_to_one():
    """Spec: 'deduplicated per sentence' -- two flagged phrases in the same
    sentence must produce one violation, not two."""
    doc = "The vendor shall use commercially reasonable efforts and respond promptly to all requests."
    violations = scan_ambiguous_language(doc)
    assert len(violations) == 1


def test_no_false_merge_same_phrase_different_sentences_stays_distinct():
    """Metric 1.4 (dedup accuracy, 0 false merges): the SAME phrase appearing
    in two DIFFERENT sentences must produce two violations, not be
    incorrectly collapsed into one."""
    doc = (
        "Support requests will be handled promptly during business hours. "
        "Emergency escalations will also be addressed promptly by the on-call team."
    )
    violations = scan_ambiguous_language(doc)
    promptly_hits = [v for v in violations if "promptly" in v.evidence.lower()]
    assert len(promptly_hits) == 2
    assert promptly_hits[0].evidence != promptly_hits[1].evidence


def test_unresolved_placeholders_are_medium_severity():
    """TBD/TBC-style unresolved placeholders are more concrete/actionable
    than a vague adverb, so they're scored medium not low (see module
    docstring rationale)."""
    doc = "Final pricing: TBD."
    violations = scan_ambiguous_language(doc)
    assert len(violations) == 1
    assert violations[0].severity == RuleSeverity.MEDIUM


def test_evidence_and_recommendation_populated():
    doc = "Delivery scope may include, but is not limited to, ancillary services."
    violations = scan_ambiguous_language(doc)
    assert len(violations) == 1
    v = violations[0]
    assert v.evidence.strip()
    assert v.recommendation.strip()
    assert v.rule_id.startswith("AMBIG-")


def test_empty_document_returns_no_violations():
    assert scan_ambiguous_language("") == []
    assert scan_ambiguous_language(None) == []
