"""T-3027 acceptance test: Celery task logic callable standalone, no
live Redis/Celery worker/DB required."""

import asyncio
from types import SimpleNamespace

from app.tasks.document_tasks import _build_report_content, generate_pdf_report_task


def _fake_review():
    return SimpleNamespace(
        doc_id="doc-1",
        overall_score=82.0,
        risk_score=15.0,
        score_completeness=90.0,
        score_clarity=80.0,
        score_consistency=None,
        score_commercial=None,
        score_delivery=None,
        score_operations=None,
        score_security=None,
        executive_summary="Looks good overall.",
    )


def _fake_doc():
    return SimpleNamespace(original_filename="spec.pdf", filename="spec.pdf")


def _fake_findings():
    return [
        SimpleNamespace(
            title="Missing SLA section",
            description="No SLA defined.",
            severity="major",
            recommendation="Add an SLA section.",
            evidence="Section 4 is empty.",
        )
    ]


def test_build_report_content_produces_html_and_pdf_bytes():
    html, pdf_bytes = asyncio.run(
        _build_report_content(_fake_review(), _fake_doc(), _fake_findings())
    )

    assert "spec.pdf" in html
    assert "Missing SLA section" in html
    assert isinstance(pdf_bytes, bytes)
    # Real PDF magic bytes -- catches the previous placeholder that just
    # returned the HTML string re-encoded and labeled a PDF (no PDF library
    # was ever installed to render one).
    assert pdf_bytes.startswith(b"%PDF-")


def test_build_report_content_keeps_a_zero_score_category():
    """Regression: a category legitimately scoring 0 (the worst case --
    critical findings everywhere) must still appear in the report. The
    original `if score_val:` check was falsy for 0 and silently dropped
    it, hiding the category a reviewer most needs to see."""
    review = _fake_review()
    review.score_security = 0.0

    html, _ = asyncio.run(_build_report_content(review, _fake_doc(), _fake_findings()))

    assert "security" in html.lower()


def test_generate_pdf_report_task_callable_directly_no_broker():
    """The @celery_app.task-decorated function stays a normal callable
    in-process -- calling it directly (not via .delay()) touches no
    Redis/Celery worker. A random review_id hits the test DB with one
    cheap SELECT and returns a "not found" result rather than raising."""
    assert hasattr(generate_pdf_report_task, "run")  # proves it's a real Celery Task

    result = generate_pdf_report_task("00000000-0000-0000-0000-000000000000")
    assert result == {"status": "failed", "error": "review not found"}
