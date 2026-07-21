"""Unit tests for ReportGenerator (app/scoring/report.py).

Covers the report redesign: branded header + doc stats, executive summary
findings-count/top-risks, per-category scorecard guidance, Document X-Ray,
findings tagged with section/page, HTML-escaping of untrusted content, and
that the PDF export produces real PDF bytes (not corrupted text).
"""

import pytest

from app.scoring.algorithm import CategoryScore, ScoringResult
from app.scoring.report import ReportGenerator


def _scoring_result():
    return ScoringResult(
        doc_id="doc-1",
        overall_score=42.0,
        risk_score=65.0,
        category_scores={
            "completeness": CategoryScore(
                category="completeness",
                score=40.0,
                max_points=100,
                points_earned=40,
                findings=[{"title": "Missing deliverables section"}],
                status="red",
            ),
            "security": CategoryScore(
                category="security",
                score=90.0,
                max_points=100,
                points_earned=90,
                findings=[],
                status="green",
            ),
        },
        summary="Weak document health.",
        next_steps=["Add missing sections and deliverable details"],
        risk_breakdown={"Legal": 80.0, "Scope": 55.0, "Commercial": 20.0},
    )


@pytest.mark.asyncio
async def test_report_includes_branding_and_doc_stats():
    html = await ReportGenerator().generate_html_report(
        "doc-1",
        "MSA_Final.docx",
        _scoring_result(),
        review_findings=[],
        doc_meta={"document_type": "SOW", "version": 2, "page_count": 12, "project_name": "Acme Rollout"},
        findings_count={"critical": 1, "major": 2, "medium": 0, "low": 0, "info": 0},
    )
    assert "ScopeWise" in html
    assert "EDGP" not in html
    assert "SOW" in html
    assert "Acme Rollout" in html
    assert "v2" in html


@pytest.mark.asyncio
async def test_executive_summary_has_findings_count_and_top_risks():
    html = await ReportGenerator().generate_html_report(
        "doc-1",
        "doc.docx",
        _scoring_result(),
        review_findings=[],
        findings_count={"critical": 1, "major": 2, "medium": 0, "low": 0, "info": 0},
    )
    assert "Top Risk Areas" in html
    assert "Legal" in html
    assert "Add missing sections and deliverable details" in html


@pytest.mark.asyncio
async def test_scorecard_has_per_category_guidance():
    html = await ReportGenerator().generate_html_report(
        "doc-1", "doc.docx", _scoring_result(), review_findings=[]
    )
    # red category (completeness) gets actionable guidance + finding count
    assert "Add missing sections and deliverable details" in html
    assert "1 related finding" in html
    # green category (security) gets an affirmative note, not a nudge
    assert "On track" in html


@pytest.mark.asyncio
async def test_document_xray_lists_sections_and_gaps():
    html = await ReportGenerator().generate_html_report(
        "doc-1",
        "doc.docx",
        _scoring_result(),
        review_findings=[],
        sections=[{"heading": "Payment Terms"}, {"heading": "Scope of Work"}],
        rule_gaps=[{"title": "Missing termination clause"}],
    )
    assert "Document X-Ray" in html
    assert "Payment Terms" in html
    assert "Missing termination clause" in html


@pytest.mark.asyncio
async def test_finding_shows_section_and_page_reference():
    html = await ReportGenerator().generate_html_report(
        "doc-1",
        "doc.docx",
        _scoring_result(),
        review_findings=[
            {
                "title": "Ambiguous acceptance criteria",
                "description": "The clause is vague.",
                "severity": "major",
                "section_ref": "Acceptance Criteria (p.7)",
            }
        ],
    )
    assert "Acceptance Criteria (p.7)" in html


@pytest.mark.asyncio
async def test_untrusted_finding_text_is_escaped():
    """Findings/filenames come from uploaded documents -- must not be able
    to inject markup into a report another org member later opens."""
    html = await ReportGenerator().generate_html_report(
        "doc-1",
        "<script>alert(1)</script>.docx",
        _scoring_result(),
        review_findings=[
            {"title": "<img src=x onerror=alert(1)>", "description": "d", "severity": "low"}
        ],
    )
    assert "<script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.asyncio
async def test_pdf_export_produces_real_pdf_bytes():
    """Regression guard: the endpoint used to base64/utf-8-mishandle these
    bytes downstream, corrupting the file. This only guards that
    generate_pdf_report itself returns a valid PDF; see test_reviews_report
    for the endpoint-level encoding fix."""
    html = await ReportGenerator().generate_html_report(
        "doc-1", "doc.docx", _scoring_result(), review_findings=[]
    )
    pdf_bytes = await ReportGenerator().generate_pdf_report(html, "doc.docx")
    assert pdf_bytes.startswith(b"%PDF")
