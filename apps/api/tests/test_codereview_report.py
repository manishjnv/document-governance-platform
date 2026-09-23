"""Minimal tests for the Code Security Review XLSX/PPTX builders. No DB
needed — `review` is a duck-typed SimpleNamespace per the module reference
§3 report shape.
"""

import types

from app.codereview.report_pptx import build_pptx_export
from app.codereview.report_xlsx import build_xlsx_export


def _fake_review():
    report = {
        "source_format": "findings",
        "tool": "vvaharness", "tool_version": "1.0",
        "repo_name": "acme/api", "git_sha": "deadbeef" * 5,
        "summary_text": "4 findings across 3 files.",
        "degraded": False, "degraded_reason": "",
        "assumptions": [],
        "counts": {
            "total": 4,
            "by_severity": {"critical": 1, "high": 1, "medium": 1, "low": 1, "info": 0},
            "by_vuln_class": {"SQL Injection": 2, "XSS": 1, "Hardcoded Secret": 1},
            "by_file": {"app/db.py": 2, "app/views.py": 2},
        },
        "findings": [
            {
                "idx": 1, "title": "=cmd|' /C calc'!A1", "severity": "critical",
                "vuln_class": "sqli", "vuln_class_label": "SQL Injection",
                "cwe": "CWE-89", "cvss_score": 9.8, "cvss_vector": "AV:N",
                "cvss_rating": "Critical", "file": "app/db.py",
                "line_start": 10, "line_end": 12, "confidence": 0.95, "votes": 3,
                "verdict": "TRUE_POSITIVE", "verdict_confidence": 90,
                "verdict_reason": "reproduced", "description": "Unsanitized query.",
                "impact": "Full DB read/write.", "exploit_scenario": "Attacker sends `' OR 1=1`.",
                "preconditions": ["network access"], "recommendation": "Use `SELECT ... FOR UPDATE` or parameterized queries.",
                "code_snippet": "cursor.execute(f\"SELECT * FROM t WHERE id={id}\")",
                "exploitability_notes": "", "verifier_reasoning": "",
                "offensive_priority": None, "offensive_reason": "",
                "source_ref": "request.args", "sink_ref": "cursor.execute",
                "duplicates": [{"file": "app/db2.py", "line_start": 20, "line_end": 22}],
            },
            {
                "idx": 2, "title": "Reflected XSS", "severity": "high",
                "vuln_class": "xss", "vuln_class_label": "XSS",
                "cwe": "CWE-79", "cvss_score": 7.1, "cvss_vector": None,
                "cvss_rating": "High", "file": "app/views.py",
                "line_start": 5, "line_end": 5, "confidence": 0.8, "votes": 2,
                "verdict": "FALSE_POSITIVE", "verdict_confidence": 60,
                "verdict_reason": "", "description": "d", "impact": "i",
                "exploit_scenario": "e", "preconditions": [], "recommendation": "r",
                "code_snippet": "", "exploitability_notes": "", "verifier_reasoning": "",
                "offensive_priority": None, "offensive_reason": "",
                "source_ref": None, "sink_ref": None, "duplicates": [],
            },
            {
                "idx": 3, "title": "Weak hash", "severity": "medium",
                "vuln_class": "crypto", "vuln_class_label": "Hardcoded Secret",
                "cwe": None, "cvss_score": 5.0, "cvss_vector": None,
                "cvss_rating": "Medium", "file": "app/auth.py",
                "line_start": 1, "line_end": 1, "confidence": 0.5, "votes": 1,
                "verdict": None, "verdict_confidence": None, "verdict_reason": "",
                "description": "d", "impact": "i", "exploit_scenario": "e",
                "preconditions": [], "recommendation": "r", "code_snippet": "",
                "exploitability_notes": "", "verifier_reasoning": "",
                "offensive_priority": None, "offensive_reason": "",
                "source_ref": None, "sink_ref": None, "duplicates": [],
            },
            {
                "idx": 4, "title": "Info leak", "severity": "low",
                "vuln_class": "info", "vuln_class_label": "SQL Injection",
                "cwe": None, "cvss_score": 2.0, "cvss_vector": None,
                "cvss_rating": "Low", "file": "app/db.py",
                "line_start": 30, "line_end": 30, "confidence": 0.3, "votes": 1,
                "verdict": None, "verdict_confidence": None, "verdict_reason": "",
                "description": "d", "impact": "i", "exploit_scenario": "e",
                "preconditions": [], "recommendation": "r", "code_snippet": "",
                "exploitability_notes": "", "verifier_reasoning": "",
                "offensive_priority": None, "offensive_reason": "",
                "source_ref": None, "sink_ref": None, "duplicates": [],
            },
        ],
        "chains": [
            {"title": "SQLi to RCE", "steps": [1, 2], "severity": "critical",
             "narrative": "Chain the SQL injection with the XSS to pivot to RCE."},
        ],
        "dropped_count": 0, "raw_findings_count": 4,
        "metrics": {"duration_sec": 120.5, "total_files_in_scope": 50,
                    "analyzed_files_unique": 48, "true_positive_count": 1,
                    "false_positive_count": 1, "total_tokens": 100000},
        "manifest": {"target_git_sha": "deadbeef", "duration_sec": 120.5,
                     "models": {"triage": {"id": "gpt-5", "provider": "openai"}},
                     "total_cost_usd": 1.23, "total_tokens": 100000},
    }
    return types.SimpleNamespace(
        name="Acme API Review", repo_label="acme/api", git_sha="deadbeef" * 5,
        source_format="findings", created_at="2026-09-11", report=report,
    )


def _fake_review_with_extras():
    """Same base report, plus run_extras and deep/fix on findings #1 (fixed,
    but broke a test) and #3 (needs review) — contract 2026-09-23."""
    review = _fake_review()
    report = review.report
    report["findings"][0]["deep"] = {
        "root_cause": "User input reaches the query builder unsanitized.",
        "gates": {"source": "request.args", "sink": "cursor.execute", "missing_control": "parameterization"},
        "remaining_risks": ["Same pattern may exist elsewhere in app/db.py"],
        "recommendations": ["Use parameterized queries everywhere"],
        "summary": "Confirmed SQL injection, patched.",
    }
    report["findings"][0]["fix"] = {
        "status": "fixed", "scanner_verdict": "Fixed", "policy_action": "accept",
        "policy_reason": "", "files": ["app/db.py"],
        "patch": "--- a/app/db.py\n+++ b/app/db.py\n@@ -1 +1 @@\n-old\n+new\n",
        "tests": "broke_tests", "tests_detail": "DbTest.test_query failed after this change",
    }
    report["findings"][2]["deep"] = {
        "root_cause": "Weak hash algorithm.", "gates": {"source": "", "sink": "", "missing_control": ""},
        "remaining_risks": [], "recommendations": ["Use bcrypt"], "summary": "Needs review.",
    }
    report["findings"][2]["fix"] = {
        "status": "needs_review", "scanner_verdict": "Needs Review", "policy_action": None,
        "policy_reason": "", "files": [], "patch": "", "tests": None, "tests_detail": "",
    }
    report["run_extras"] = {
        "mode": "fix", "deep_verified": 2, "total": 4,
        "fix_counts": {"fixed": 1, "needs_review": 1},
        "tests": {
            "build": "failure", "suites": 1, "cases": 10, "failures": 1, "errors": 0, "skipped": 0,
            "failing": [{"test": "DbTest.test_query", "message": "assertion failed"}],
            "not_run_modules": ["Reporting Module"],
        },
        "coverage": {
            "coverage_pct": 99.1, "files_in_scope": 50, "files_analyzed": 48, "chunks": 12,
            "health": ["No fatal scan errors", "All chunks processed"],
            "threat_model": "External attacker with network access to the API.",
        },
    }
    return review


def test_xlsx_run_extras_sheets_and_warning_row():
    from openpyxl import load_workbook

    review = _fake_review_with_extras()
    wb = load_workbook(io_bytes(build_xlsx_export(review)))
    assert "Fixes" in wb.sheetnames
    assert "Scan Coverage" in wb.sheetnames
    ws = wb["Findings Register"]
    headers = [c.value for c in ws[1]]
    assert "Fix status" in headers
    tests_col = headers.index("Tests after fix") + 1
    broke_cells = [
        ws.cell(row=r, column=tests_col).value
        for r in range(2, ws.max_row + 1)
    ]
    assert any("Fix broke a test" in str(v) for v in broke_cells)


def test_xlsx_without_run_extras_has_no_extra_sheets():
    review = _fake_review()
    wb_names = __import__("openpyxl").load_workbook(io_bytes(build_xlsx_export(review))).sheetnames
    assert "Fixes" not in wb_names
    assert "Scan Coverage" not in wb_names


def test_pptx_fix_status_slide():
    from pptx import Presentation

    review = _fake_review_with_extras()
    prs = Presentation(io_bytes(build_pptx_export(review)))
    all_text = "\n".join(
        shape.text_frame.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_text_frame
    ) + "\n".join(
        c.text for slide in prs.slides for sh in slide.shapes if sh.has_table
        for r in sh.table.rows for c in r.cells
    )
    assert "Fix status" in all_text
    assert "do not treat as fixed" in all_text


def test_xlsx_builds_and_guards_formula_titles():
    from openpyxl import load_workbook

    review = _fake_review()
    data = build_xlsx_export(review)
    wb = load_workbook(io_bytes(data))
    assert wb.sheetnames == ["Read Me", "Summary", "Findings Register", "Exploit Chains"]
    ws = wb["Findings Register"]
    title_col = [c.value for c in ws[1]].index("Title") + 1
    first_title = ws.cell(row=2, column=title_col).value
    assert first_title.startswith("'=")


def test_xlsx_deterministic():
    review = _fake_review()
    assert build_xlsx_export(review) == build_xlsx_export(review)


def test_pptx_builds_with_expected_slide_count_and_attribution():
    from pptx import Presentation

    review = _fake_review()
    data = build_pptx_export(review)
    prs = Presentation(io_bytes(data))
    assert len(prs.slides) >= 7
    closing_text = "\n".join(
        shape.text_frame.text
        for shape in prs.slides[-1].shapes
        if shape.has_text_frame
    )
    assert "Visa Vulnerability Agentic Harness" in closing_text


def test_pptx_deterministic_by_extracted_text():
    # python-pptx zips embed no wall-clock timestamps we write, but to be
    # safe (and per the task spec) compare extracted slide text rather
    # than raw bytes.
    from pptx import Presentation

    review = _fake_review()
    texts = []
    for data in (build_pptx_export(review), build_pptx_export(review)):
        prs = Presentation(io_bytes(data))
        texts.append([
            shape.text_frame.text
            for slide in prs.slides
            for shape in slide.shapes
            if shape.has_text_frame
        ])
    assert texts[0] == texts[1]


def io_bytes(data: bytes):
    import io

    return io.BytesIO(data)


def test_highlight_words_web_mirror_is_current():
    """highlight_words.json is the single source; the drawer's
    highlightWords.ts is generated from it. Regenerate with
    `python scripts/generate_highlight_words.py` when this fails."""
    import json
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo / "scripts"))
    from generate_highlight_words import SOURCE, TARGET, render  # noqa: E402

    words = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert TARGET.read_text(encoding="utf-8") == render(words)
    # every fragment must compile in Python too (the JS side is checked by tsc)
    import re
    for frag in words["risk"] + words["fix"]:
        re.compile(frag)


def test_sentences_keep_ellipsis_inside_code():
    """Slide 10 'Fix in one line' once rendered 'Use `SELECT ...' because the
    ellipsis in `SELECT ... FOR UPDATE` was split as a sentence end."""
    from app.codereview.report_xlsx import _sentences

    text = "Use `SELECT ... FOR UPDATE` or an atomic `F()` update. Then add a test."
    assert _sentences(text) == [
        "Use `SELECT ... FOR UPDATE` or an atomic `F()` update.",
        "Then add a test.",
    ]


def test_pptx_plan_table_has_no_raw_backticks():
    """Slide 'Remediation Plan' cells are plain text — backticks from the
    LLM's markdown must be stripped, and the ellipsis sentence kept whole."""
    from pptx import Presentation
    import io

    prs = Presentation(io.BytesIO(build_pptx_export(_fake_review())))
    cells = [
        c.text for s in prs.slides for sh in s.shapes if sh.has_table
        for r in sh.table.rows for c in r.cells
    ]
    hit = [c for c in cells if "SELECT ... FOR UPDATE" in c]
    assert hit and all("`" not in c for c in hit)

