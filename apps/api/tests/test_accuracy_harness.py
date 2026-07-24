"""The accuracy harness (scripts/accuracy_harness.py) must count a
keyword-matching finding toward its ground-truth row and report the rest as
beyond-GT."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "accuracy_harness",
    Path(__file__).resolve().parents[2] / "scripts" / "accuracy_harness.py",
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def test_matching_finding_satisfies_row_and_unmatched_is_reported():
    findings = [
        {"title": "Missing Raci", "description": "No RACI matrix is defined."},
        {"title": "Something Else", "description": "Totally unrelated to any row."},
    ]
    result = harness.score(findings)

    by_id = {r["gt_id"]: r for r in result["rows"]}
    assert by_id["SOW-011"]["matched"] is True
    assert result["gt_hit"] >= 1
    assert result["findings_total"] == 2
    assert result["findings_beyond_gt"] == ["Something Else"]


def test_empty_findings_scores_zero():
    result = harness.score([])
    assert result["gt_hit"] == 0
    assert result["recall_strict"] == 0.0
