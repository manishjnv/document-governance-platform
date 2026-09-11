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
                "preconditions": ["network access"], "recommendation": "Use parameterized queries.",
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
