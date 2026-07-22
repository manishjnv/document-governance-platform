"""Ambiguous-language detector.

docs/planning/4_AI_AGENT_SPECS.md "Cross-Cutting: Ambiguous Language
Detector" (added 2026-07-17). Rule-based (regex/keyword), not an LLM agent
-- runs once against the full document text, applies to every document
type. Returns RuleViolation objects so orchestrator.py can merge its
output directly into the same rule_violations list the LLM-free rule
engine produces (app/rules/engine.py), reusing the existing Finding-row
storage path in app/routers/reviews.py without any changes there.
"""

import re
from typing import Optional

from app.rules.engine import RuleSeverity, RuleViolation

# (phrase, severity). Unresolved placeholders are "medium" -- an actual
# missing decision point is more concrete/actionable than a vague adverb,
# which stays "low" per the spec's "not severity-critical on its own".
_PHRASE_FAMILIES: list[tuple[str, RuleSeverity]] = [
    # Vague effort/quality
    ("reasonable efforts", RuleSeverity.LOW),
    ("best effort", RuleSeverity.LOW),
    ("commercially reasonable", RuleSeverity.LOW),
    ("industry standard", RuleSeverity.LOW),
    # Unresolved placeholders
    ("tbd", RuleSeverity.MEDIUM),
    ("tbc", RuleSeverity.MEDIUM),
    ("to be determined", RuleSeverity.MEDIUM),
    ("to be confirmed", RuleSeverity.MEDIUM),
    # Open-ended scope
    ("including but not limited to", RuleSeverity.LOW),
    ("as needed", RuleSeverity.LOW),
    ("as appropriate", RuleSeverity.LOW),
    ("may include", RuleSeverity.LOW),
    ("etc.", RuleSeverity.LOW),
    ("and so on", RuleSeverity.LOW),
    # Unquantified terms
    ("promptly", RuleSeverity.LOW),
    ("in a timely manner", RuleSeverity.LOW),
    ("as soon as possible", RuleSeverity.LOW),
]

# Sentence splitter: break on ./!/? followed by whitespace, keep it simple
# -- this is a rule-based scan, not an NLP pipeline (ponytail: naive
# sentence boundary heuristic, misses abbreviations like "e.g." mid-sentence;
# upgrade to a real sentence tokenizer if false sentence-splits start
# corrupting matched_sentence evidence in practice).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _find_section(char_offset: int, document_text: str, sections: dict[str, str]) -> Optional[str]:
    """Best-effort: which section's content contains the char at this offset."""
    if not sections:
        return None
    for heading, content in sections.items():
        if content and content in document_text:
            start = document_text.index(content)
            if start <= char_offset < start + len(content):
                return heading
    return None


def scan_ambiguous_language(
    document_text: str, sections: Optional[dict[str, str]] = None
) -> list[RuleViolation]:
    """Scan full document text for weasel phrases.

    Returns one RuleViolation per distinct sentence (deduplicated -- a
    sentence containing two flagged phrases is reported once, keyed by the
    first phrase family matched in _PHRASE_FAMILIES order).
    """
    if not document_text:
        return []

    sections = sections or {}
    text_lower = document_text.lower()
    seen_sentences: set[str] = set()
    violations: list[RuleViolation] = []

    for phrase, severity in _PHRASE_FAMILIES:
        for match in re.finditer(re.escape(phrase), text_lower):
            char_offset = match.start()

            sentence_start = document_text.rfind(".", 0, char_offset) + 1
            sentence_end_match = _SENTENCE_SPLIT_RE.search(document_text, char_offset)
            sentence_end = sentence_end_match.start() if sentence_end_match else len(document_text)
            matched_sentence = document_text[sentence_start:sentence_end].strip()

            if not matched_sentence:
                matched_sentence = document_text[char_offset : char_offset + 120].strip()

            dedup_key = matched_sentence.lower()
            if dedup_key in seen_sentences:
                continue
            seen_sentences.add(dedup_key)

            section = _find_section(char_offset, document_text, sections)

            violations.append(
                RuleViolation(
                    rule_id=f"AMBIG-{phrase.replace(' ', '-').rstrip('.')}",
                    rule_name=f"Ambiguous language: '{phrase}'",
                    severity=severity,
                    description=(
                        f"Ambiguous/open-ended phrase '{phrase}' found"
                        + (f" in section '{section}'" if section else "")
                        + ". Context-dependent -- flagged for human triage, not necessarily a defect."
                    ),
                    evidence=matched_sentence,
                    evidence_type="location",
                    matched_text=matched_sentence,
                    recommendation=(
                        "Replace with a specific, quantified, or dated commitment "
                        "(e.g., a defined SLA, a named list instead of 'as needed', "
                        "or a concrete date instead of 'TBD')."
                    ),
                )
            )

    return violations
