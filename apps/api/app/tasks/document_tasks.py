"""Document background jobs (T-3027).

Document parsing (app/parser.py) runs synchronously inside
POST /api/v1/documents/upload (app/routers/documents.py) because the
response body returns parsed_text/parsed_sections/page_count in the same
request — existing tests assert on that. Moving it behind .delay() would
change the response contract, so that call site is left untouched.

PDF report generation (app/scoring/report.py's ReportGenerator) has no
async path at all today: GET /api/v1/reviews/{id}/report?format=pdf
(app/routers/reviews.py) builds it synchronously on every request and
that endpoint is also left untouched (tests assert on its response).
generate_pdf_report_task below is a genuinely new, currently-missing job:
build + store a review's PDF report out-of-band, e.g. from a scheduled
job or a "generate my report" button that doesn't want to block on it.
"""

import asyncio
import logging
from uuid import UUID

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _build_report_content(review, doc, findings: list) -> tuple[str, bytes]:
    """Pure report-building logic: review/doc/findings in, (html, pdf) out.

    No DB access here — kept separate from _generate_pdf_report_async so it
    can be unit tested without a live database.
    """
    from app.scoring import ReportGenerator
    from app.scoring.algorithm import CategoryScore, ScoringResult

    category_scores = {}
    for category in [
        "completeness", "clarity", "consistency", "commercial",
        "delivery", "operations", "security",
    ]:
        score_val = getattr(review, f"score_{category}", None)
        # `is not None`, not truthy -- see app/routers/reviews.py's identical
        # fix: a category legitimately scoring 0 must not be dropped.
        if score_val is not None:
            category_scores[category] = CategoryScore(
                category=category,
                score=float(score_val),
                max_points=100,
                points_earned=int(score_val),
                findings=[],
                status="green" if score_val >= 80 else ("yellow" if score_val >= 50 else "red"),
            )

    scoring_result = ScoringResult(
        doc_id=str(review.doc_id),
        overall_score=float(review.overall_score) if review.overall_score else 0.0,
        risk_score=float(review.risk_score) if review.risk_score else 0.0,
        category_scores=category_scores,
        summary=review.executive_summary or "Review complete.",
        next_steps=[],
    )

    findings_list = [
        {
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
        }
        for f in findings
    ]

    generator = ReportGenerator()
    html_report = await generator.generate_html_report(
        str(review.doc_id),
        doc.original_filename or doc.filename,
        scoring_result,
        findings_list,
    )
    pdf_bytes = await generator.generate_pdf_report(html_report, doc.filename)
    return html_report, pdf_bytes


async def _generate_pdf_report_async(review_id: str) -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.models.document import Document
    from app.models.finding import Finding
    from app.models.review import Review
    from app.storage import get_storage_instance

    # asyncio.run() (in generate_pdf_report_task below) spins up a brand-new
    # event loop on every call. The app-wide engine in app/db/session.py is
    # bound to whatever loop first touched it, so reusing it here breaks
    # ("attached to a different loop") the second time this task runs in
    # the same process. A short-lived engine, disposed before returning,
    # keeps this task's DB connections scoped to this call's own loop.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            review = (
                await db.execute(select(Review).where(Review.review_id == UUID(review_id)))
            ).scalar_one_or_none()
            if not review:
                return {"status": "failed", "error": "review not found"}

            doc = (
                await db.execute(select(Document).where(Document.doc_id == review.doc_id))
            ).scalar_one_or_none()
            if not doc:
                return {"status": "failed", "error": "document not found"}

            findings = (
                await db.execute(
                    select(Finding).where(
                        (Finding.review_id == review.review_id) & (Finding.deleted_at.is_(None))
                    )
                )
            ).scalars().all()

            _html, pdf_bytes = await _build_report_content(review, doc, findings)

            storage = await get_storage_instance()
            storage_path = f"org/{review.org_id}/reports/{review.review_id}.pdf"
            await storage.upload(storage_path, pdf_bytes)

            return {"status": "success", "storage_path": storage_path, "review_id": review_id}
    finally:
        await engine.dispose()


@celery_app.task(name="tasks.generate_pdf_report")
def generate_pdf_report_task(review_id: str) -> dict:
    """Build and store a review's PDF report out-of-band.

    Trigger with generate_pdf_report_task.delay(review_id) from a worker,
    or call directly (see tests/test_tasks.py) — Celery tasks stay callable
    as plain functions in-process.
    """
    return asyncio.run(_generate_pdf_report_async(review_id))
