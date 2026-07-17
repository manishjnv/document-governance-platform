"""Analytics & reporting endpoints.

T-2006 (document analytics), T-2007 (review metrics), T-2008 (performance
dashboard), T-2016 (custom report builder), T-2018 (report templates),
T-2020 (report archive & history).

Owns every /api/v1/analytics/* path except /trends, which
app.routers.insights_extra already registered in Wave 1 (see main.py) --
this router's paths (documents/, reviews/metrics, dashboard, reports*)
don't collide with it.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.aggregator import get_document_analytics
from app.analytics.dashboard import get_performance_dashboard, get_review_metrics
from app.analytics.reports import (
    REPORT_TEMPLATES,
    build_custom_report,
    get_archived_report,
    list_report_archive,
    save_report_to_archive,
)
from app.core.cache import cached
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class CustomReportRequest(BaseModel):
    """POST /reports body. Either `metrics` or `template` must be given;
    `template`, when present, overrides `metrics` with the template's list."""

    metrics: list[str] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    template: Optional[str] = None


@router.get("/documents/{doc_id}")
@cached(ttl_seconds=60)
async def document_analytics(
    doc_id: UUID,
    response: Response,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2006: view_count, unique_viewer_count, and latest review outcome
    for one document. T-3005: cached 60s per doc_id+org."""
    doc = await db.scalar(
        select(Document).where(
            Document.doc_id == doc_id,
            Document.org_id == current_user.org_id,
            Document.deleted_at.is_(None),
        )
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return await get_document_analytics(db, current_user.org_id, doc_id)


@router.get("/reviews/metrics")
@cached(ttl_seconds=300)
async def review_metrics(
    response: Response,
    category: Optional[str] = None,
    months: int = Query(6, ge=1, le=36),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2007: average review scores by category, grouped by month.
    T-3005: cached 5min per org+category+months (aggregates over all reviews)."""
    return await get_review_metrics(db, current_user.org_id, category=category, months=months)


@router.get("/dashboard")
@cached(ttl_seconds=300)
async def performance_dashboard(
    response: Response,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2008: org-wide performance summary in one payload.
    T-3005: cached 5min per org (aggregates over every doc/review)."""
    return await get_performance_dashboard(db, current_user.org_id)


@router.get("/reports/templates")
async def report_templates() -> dict:
    """T-2018: available report templates and the metric keys each includes."""
    return REPORT_TEMPLATES


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CustomReportRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2016: build a custom (or template-based) report and archive it."""
    metrics = body.metrics
    report_type = "custom"
    if body.template:
        if body.template not in REPORT_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown template '{body.template}'. Valid: {list(REPORT_TEMPLATES)}",
            )
        metrics = REPORT_TEMPLATES[body.template]
        report_type = body.template

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'metrics' or 'template'",
        )

    report = await build_custom_report(
        db, current_user.org_id, metrics, date_from=body.date_from, date_to=body.date_to
    )

    report_id = await save_report_to_archive(
        db,
        current_user.org_id,
        current_user.user_id,
        report_type=report_type,
        format="json",
        content=json.dumps(report, default=str),
    )

    return {"report_id": str(report_id), **report}


@router.get("/reports")
async def report_archive_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """T-2020: this org's archived reports, newest first."""
    return await list_report_archive(db, current_user.org_id, skip=skip, limit=limit)


@router.get("/reports/{report_id}")
async def report_archive_detail(
    report_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2020: one archived report's full content, org-scoped."""
    report = await get_archived_report(db, current_user.org_id, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report
