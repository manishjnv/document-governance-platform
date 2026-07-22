"""Broken internal-reference detector (GUIDELINE_FEASIBILITY_PLAN Phase C1).

Deterministic, not an LLM agent. Scans document text for internal references
("see Appendix C", "as defined in Section 5.2", "per Exhibit B") and verifies
the target actually exists among the parsed headings. Each dangling reference
becomes a RuleViolation with evidence_type='reference' and the referring
sentence as matched_text, merged into the same rule_violations list as the
rule engine and ambiguous-language scan (app/ai/orchestrator.py).

Org-disableable via the pseudo rule id REF-SCAN (app/admin/customization.py
adds it to VALID_RULE_IDS so the existing per-org enable/disable plumbing
covers it).
"""

import re
from typing import Optional

from app.rules.engine import RuleSeverity, RuleViolation, _normalize_heading

REF_SCAN_RULE_ID = "REF-SCAN"

# ponytail: "Table N" references are deliberately NOT checked -- the parser
# doesn't label tables, so table existence can't be verified without false
# alarms. Add if the parser ever captures table captions.
_LETTERED = r"[A-Z](?![A-Za-z])|\d+"
_REF_PATTERN = re.compile(
    r"\b(Appendix|Annex|Exhibit|Schedule)\s+(" + _LETTERED + r")"
    r"|\b(Section)\s+(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _referring_sentence(text: str, offset: int) -> str:
    start = text.rfind(".", 0, offset) + 1
    end_match = _SENTENCE_SPLIT_RE.search(text, offset)
    end = end_match.start() if end_match else len(text)
    sentence = text[start:end].strip()
    return sentence or text[offset : offset + 120].strip()


def scan_references(
    document_text: str, sections: Optional[dict[str, str]] = None
) -> list[RuleViolation]:
    """One violation per distinct dangling reference target."""
    if not document_text:
        return []

    sections = sections or {}
    headings_norm = [_normalize_heading(h) for h in sections.keys()]
    headings_raw = [h.strip().lower() for h in sections.keys()]

    # Section numbers defined by heading numbering prefixes ("5. Service
    # Levels" defines section 5; "5.2 Something" defines 5.2 and 5).
    defined_section_numbers: set[str] = set()
    for h in sections.keys():
        m = re.match(r"\s*(\d+(?:\.\d+)*)[\.\)]?\s", h)
        if m:
            num = m.group(1)
            defined_section_numbers.add(num)
            while "." in num:  # 5.2.1 also defines 5.2 and 5 as prefixes
                num = num.rsplit(".", 1)[0]
                defined_section_numbers.add(num)

    violations: list[RuleViolation] = []
    seen_targets: set[str] = set()

    for m in _REF_PATTERN.finditer(document_text):
        if m.group(1):  # Appendix/Annex/Exhibit/Schedule <letter-or-number>
            kind, ident = m.group(1), m.group(2)
            label = f"{kind.lower()} {ident.lower()}"
            # Word-boundary, not substring: "appendix a" must not resolve
            # against a heading for "Appendix AB" (adversarial review
            # 2026-07-23 -- same bug class engine._alias_in_headings fixed).
            label_pattern = re.compile(r"(?<![\w-])" + re.escape(label) + r"(?![\w-])")
            exists = any(
                label_pattern.search(h) for h in (*headings_norm, *headings_raw)
            )
        else:  # Section <number>
            kind, ident = m.group(3), m.group(4)
            # Statutory citations ("Section 508", "Section 1798.100") are
            # external law, not internal references -- a real SOW never has
            # 100+ internal sections.
            if int(ident.split(".")[0]) >= 100:
                continue
            label = f"section {ident}"
            exists = ident in defined_section_numbers
            # A doc with NO numbered headings at all can't be checked for
            # section references -- skip instead of flagging everything.
            if not defined_section_numbers:
                continue

        if exists or label in seen_targets:
            continue
        seen_targets.add(label)

        sentence = _referring_sentence(document_text, m.start())
        display = f"{kind.title()} {ident.upper() if m.group(1) else ident}"
        violations.append(
            RuleViolation(
                rule_id=f"REF-{kind.lower()}-{ident.lower()}",
                rule_name=f"Broken reference: {display}",
                severity=RuleSeverity.MAJOR,
                description=(
                    f"The document references {display}, but no such "
                    "section/attachment exists in the document. A reader following "
                    "this reference finds nothing -- either the target was never "
                    "attached or the reference is stale."
                ),
                evidence=sentence,
                recommendation=(
                    f"Attach or add {display}, or correct/remove the stale reference."
                ),
                evidence_type="reference",
                matched_text=sentence,
            )
        )

    return violations
