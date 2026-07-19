"""Tests for fix-verification diff (Phase C of Document Lifecycle plan):
resolved/still-present matching by category (+section_ref), and that a
manual "Mark Fixed" claim never overrides what the re-review finds.
"""

from app.insights.fix_verification import apply_verification, diff_findings
from app.models.finding import Finding


def _finding(category, section_ref=None, status="open"):
    return Finding(
        org_id="00000000-0000-0000-0000-000000000000",
        review_id="00000000-0000-0000-0000-000000000000",
        finding_source="rule",
        rule_id="R1",
        category=category,
        title=category,
        description="d",
        section_ref=section_ref,
        severity="major",
        recommendation="r",
        status=status,
    )


class TestDiffFindings:
    def test_unmatched_previous_finding_is_resolved(self):
        previous = [_finding("missing_liability_cap")]
        diff = diff_findings(previous, [])
        assert diff["resolved"] == previous
        assert diff["persisted"] == []
        assert diff["new"] == []

    def test_matched_by_category_is_persisted(self):
        previous = [_finding("missing_liability_cap")]
        new = [_finding("missing_liability_cap")]
        diff = diff_findings(previous, new)
        assert diff["persisted"] == previous
        assert diff["resolved"] == []

    def test_section_ref_mismatch_with_both_set_does_not_match(self):
        previous = [_finding("missing_liability_cap", section_ref="Section 4")]
        new = [_finding("missing_liability_cap", section_ref="Section 9")]
        diff = diff_findings(previous, new)
        assert diff["resolved"] == previous
        assert diff["persisted"] == []

    def test_unmatched_new_finding_is_new(self):
        new = [_finding("undefined_sla")]
        diff = diff_findings([], new)
        assert diff["new"] == new


class TestApplyVerification:
    def test_resolved_finding_marked_verified(self):
        previous = [_finding("missing_liability_cap", status="open")]
        diff = diff_findings(previous, [])
        apply_verification(previous, diff, new_review_id="review-2")

        assert previous[0].status == "resolved"
        assert previous[0].notes["resolution"] == "verified"
        assert previous[0].notes["verified_by_review_id"] == "review-2"

    def test_manual_fixed_claim_overridden_when_still_present(self):
        """A finding manually marked 'resolved' by a user, but the re-review
        still finds it -- the manual claim must NOT survive."""
        previous = [_finding("missing_liability_cap", status="resolved")]
        new = [_finding("missing_liability_cap")]
        diff = diff_findings(previous, new)
        apply_verification(previous, diff, new_review_id="review-2")

        assert previous[0].status == "open"
        assert previous[0].notes["resolution"] == "still_present"

    def test_open_finding_still_present_stays_open(self):
        previous = [_finding("missing_liability_cap", status="open")]
        new = [_finding("missing_liability_cap")]
        diff = diff_findings(previous, new)
        apply_verification(previous, diff, new_review_id="review-2")

        assert previous[0].status == "open"
        assert previous[0].notes["resolution"] == "still_present"
