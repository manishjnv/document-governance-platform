"""Fix-verification diff (Phase C of Document Lifecycle plan): matches a
previous review's findings against a new review's findings by category
(+ section_ref where both are available) to determine which findings were
actually resolved vs. still present -- independent of any manual "Mark
Fixed" claim made between versions (that claim never overrides what the
re-review actually found)."""

from __future__ import annotations

from app.models.finding import Finding


def _findings_match(previous: Finding, new: Finding) -> bool:
    if previous.category != new.category:
        return False
    if previous.section_ref and new.section_ref:
        return previous.section_ref == new.section_ref
    return True


def diff_findings(
    previous_findings: list[Finding], new_findings: list[Finding]
) -> dict[str, list[Finding]]:
    """Pure comparison, no DB writes -- used both by trigger_review (to
    auto-verify the immediately previous version) and by the finding-diff
    endpoint (to let a user compare any two versions on demand)."""
    matched_new_ids = set()
    resolved: list[Finding] = []
    persisted: list[Finding] = []

    for previous in previous_findings:
        match = next((nf for nf in new_findings if _findings_match(previous, nf)), None)
        if match is not None:
            persisted.append(previous)
            matched_new_ids.add(match.finding_id)
        else:
            resolved.append(previous)

    new_only = [nf for nf in new_findings if nf.finding_id not in matched_new_ids]

    return {"resolved": resolved, "new": new_only, "persisted": persisted}


def apply_verification(
    previous_findings: list[Finding], diff: dict[str, list[Finding]], new_review_id
) -> None:
    """Side-effecting: updates status/notes on the PREVIOUS review's Finding
    rows in place (caller commits). A previous finding with no match in the
    new findings is marked resolved (verified) regardless of prior manual
    status; a previous finding that still matches is marked still-present
    and, if it had been manually claimed "resolved", that claim is reset to
    "open" -- the re-review's result always wins over the manual claim."""
    resolved_ids = {f.finding_id for f in diff["resolved"]}

    for finding in previous_findings:
        notes = dict(finding.notes or {})
        if finding.finding_id in resolved_ids:
            notes["resolution"] = "verified"
            notes["verified_by_review_id"] = str(new_review_id)
            finding.status = "resolved"
        else:
            notes["resolution"] = "still_present"
            notes["checked_by_review_id"] = str(new_review_id)
            if finding.status == "resolved":
                finding.status = "open"
        finding.notes = notes
