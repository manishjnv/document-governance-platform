"""Accuracy harness: score a review's findings against the 29-row ground
truth for SOC_SOW_Testing.docx (docs/sample/SOW_Sample/
SOW_Review_Training_Guideline.md).

Usage:
    python scripts/accuracy_harness.py <findings.json> [--quiet]

<findings.json> is the output of a review run -- any file with a top-level
{"findings": [...]} list whose entries carry title/description/evidence
text (the rerun_review.py helper and GET /api/v1/reviews/{id}/results both
produce this shape). File type of the reviewed document doesn't matter
(DOCX/PDF/DOC all produce the same findings shape).

Matching is keyword/regex per ground-truth row -- a deterministic
approximation of the human semantic matching used for the dated entries in
docs/planning/ACCURACY_BASELINE_2026_07_22.md. It can under- or over-count
individual rows; treat the output as a fast regression TREND signal between
prompt/rule changes, and re-do a human pass before publishing a number.
"""

import json
import re
import sys

# Each row: (gt_id, short label, [regex alternatives -- any match on a
# finding's combined text satisfies the row]). Patterns are derived from the
# findings that satisfied each row in the 2026-07-22/23 human-scored passes.
GROUND_TRUTH = [
    ("SOW-001", "Objectives not measurable", [r"success metric", r"measurab"]),
    ("SOW-002", "Infra inventory incomplete", [r"environment inventory", r"incomplete environment", r"critical business application"]),
    ("SOW-003", "SOC activities not detailed", [r"scope of work must be clearly defined", r"operational detail"]),
    ("SOW-004", "Threat Intelligence lacks detail", [r"threat intel"]),
    ("SOW-005", "Threat hunting methodology missing", [r"threat hunt"]),
    ("SOW-006", "IR lifecycle undefined", [r"incident response", r"800-61", r"ir lifecycle"]),
    ("SOW-007", "Deliverables lack acceptance criteria", [r"acceptance criteria", r"material objection"]),
    ("SOW-008", "Report contents undefined", [r"report (format|content|structure)"]),
    ("SOW-009", "Only acknowledgement SLA defined", [r"resolution[- ]time", r"no resolution", r"resolution commitment"]),
    ("SOW-010", "Service hours / time zone missing", [r"support hours", r"service hours", r"coverage hours", r"time zone"]),
    ("SOW-011", "Ownership unclear (RACI)", [r"raci"]),
    ("SOW-012", "Escalation matrix missing", [r"escalation"]),
    ("SOW-013", "Assumptions generic", [r"customer obligation", r"unstated assumption", r"assumptions? (are|is)? ?(too )?(generic|vague)"]),
    ("SOW-014", "Log onboarding assumptions missing", [r"log[- ]source", r"log onboarding"]),
    ("SOW-015", "Out-of-scope incomplete", [r"exclusion", r"out[- ]of[- ]scope"]),
    ("SOW-016", "Transition lacks timeline", [r"transition[^.]*(timeline|date|dates|no end|duration)", r"(timeline|dates?)[^.]*transition"]),
    ("SOW-017", "Commercial terms incomplete", [r"fee amount", r"no fee", r"currency", r"invoic"]),
    ("SOW-018", "CR pricing undefined", [r"rate card", r"change request[^.]*(pric|cost|rate)", r"(pric|cost)[^.]*change request"]),
    ("SOW-019", "Ambiguous contractual wording", [r"reasonable efforts", r"vague language", r"ambiguous (language|wording|term)"]),
    ("SOW-020", "Open-items prioritization undefined", [r"open item"]),
    ("SOW-021", "Risks lack owners/mitigations", [r"risk register", r"risk[^.]*(owner|mitigation)"]),
    ("SOW-022", "Acceptance clause too generic", [r"acceptance"]),
    ("SOW-023", "Confidentiality too generic", [r"confidential"]),
    ("SOW-024", "Change approval workflow missing", [r"change (authority|approval|management)"]),
    ("SOW-025", "Log inventory lacks ownership", [r"owner (column|missing)", r"no owner", r"inventory[^.]*owner", r"owner[^.]*inventory"]),
    ("SOW-026", "Log volume not documented", [r"volume", r"gb/day", r"\beps\b"]),
    ("SOW-027", "Shift allocation missing", [r"shift", r"coverage model", r"24x7[^.]*coverage", r"coverage[^.]*24x7"]),
    ("SOW-028", "FTE allocation missing", [r"\bfte\b", r"headcount", r"staffing"]),
    ("SOW-029", "Contract metadata incomplete", [r"signature", r"signing date", r"signature date"]),
]


def finding_text(finding: dict) -> str:
    return " ".join(
        str(finding.get(k) or "")
        for k in ("title", "description", "evidence", "matched_text", "recommendation")
    ).lower()


def score(findings: list[dict]) -> dict:
    texts = [(f, finding_text(f)) for f in findings]
    rows = []
    matched_finding_ids: set[int] = set()
    for gt_id, label, patterns in GROUND_TRUTH:
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        hits = [
            f for i, (f, text) in enumerate(texts)
            if any(c.search(text) for c in compiled) and (matched_finding_ids.add(i) or True)
        ]
        rows.append({"gt_id": gt_id, "label": label, "matched": len(hits) > 0,
                     "matched_titles": sorted({str(f.get("title") or "?")[:60] for f in hits})[:3]})
    unmatched = [f for i, (f, _) in enumerate(texts) if i not in matched_finding_ids]
    hit_count = sum(1 for r in rows if r["matched"])
    return {
        "rows": rows,
        "recall_strict": hit_count / len(GROUND_TRUTH),
        "gt_hit": hit_count,
        "gt_total": len(GROUND_TRUTH),
        "findings_total": len(findings),
        "findings_matching_gt": len(matched_finding_ids),
        "findings_beyond_gt": [str(f.get("title") or "?")[:70] for f in unmatched],
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    quiet = "--quiet" in sys.argv
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    result = score(data["findings"])

    if not quiet:
        for r in result["rows"]:
            mark = "PASS" if r["matched"] else "MISS"
            titles = ("  <- " + "; ".join(r["matched_titles"])) if r["matched_titles"] else ""
            print(f"{mark}  {r['gt_id']}  {r['label']}{titles}")
        print()
    print(
        f"Strict recall (keyword-matched): {result['gt_hit']}/{result['gt_total']}"
        f" = {result['recall_strict']:.1%}"
    )
    print(
        f"Findings: {result['findings_total']} total, "
        f"{result['findings_matching_gt']} matched a GT row, "
        f"{len(result['findings_beyond_gt'])} beyond GT scope (review by hand for precision)"
    )
    if not quiet and result["findings_beyond_gt"]:
        print("\nBeyond-GT findings (not FPs by default -- eyeball them):")
        for t in result["findings_beyond_gt"]:
            print(f"  - {t}")


if __name__ == "__main__":
    main()
