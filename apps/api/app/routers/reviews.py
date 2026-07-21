"""Review management API endpoints.

T-510: Rule management API
T-509: Store review results in database
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import ReviewOrchestrator
from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.schemas.auth import TokenData
from app.scoring.algorithm import DocumentScorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _risk_area(finding: Finding) -> str:
    """Same axis a finding contributes to in the Risk by Area breakdown
    (DocumentScorer._calculate_risk_breakdown) -- lets the UI tag each
    finding with the area it's already counted under."""
    if finding.finding_source == "rule":
        return "Compliance"
    return DocumentScorer.AXIS_BY_AGENT.get(finding.agent_name or "", "Other")


async def _verify_against_previous_version(db: AsyncSession, doc: Document, review: Review) -> None:
    """Phase C (Document Lifecycle plan): if `doc` has an earlier version in
    the same document_group_id with a completed review, diff that review's
    findings against `review`'s (just-added, not yet committed -- flushed
    here so they're queryable) findings and update the previous findings'
    resolved/still-present status accordingly. No-op if there's no earlier
    version or it has no completed review."""
    from sqlalchemy import select

    from app.insights.fix_verification import apply_verification, diff_findings

    prev_doc_result = await db.execute(
        select(Document)
        .where(
            (Document.document_group_id == doc.document_group_id)
            & (Document.org_id == doc.org_id)
            & (Document.version < doc.version)
            & (Document.deleted_at.is_(None))
        )
        .order_by(Document.version.desc())
    )
    prev_doc = prev_doc_result.scalars().first()
    if prev_doc is None:
        return

    prev_review_result = await db.execute(
        select(Review)
        .where(
            (Review.doc_id == prev_doc.doc_id)
            & (Review.status == "completed")
            & (Review.deleted_at.is_(None))
        )
        .order_by(Review.created_at.desc())
    )
    prev_review = prev_review_result.scalars().first()
    if prev_review is None:
        return

    prev_findings_result = await db.execute(
        select(Finding).where(
            (Finding.review_id == prev_review.review_id) & (Finding.deleted_at.is_(None))
        )
    )
    previous_findings = list(prev_findings_result.scalars().all())
    if not previous_findings:
        return

    await db.flush()
    new_findings_result = await db.execute(
        select(Finding).where(
            (Finding.review_id == review.review_id) & (Finding.deleted_at.is_(None))
        )
    )
    new_findings = list(new_findings_result.scalars().all())

    diff = diff_findings(previous_findings, new_findings)
    apply_verification(previous_findings, diff, review.review_id)


def _locate_finding(evidence, document_text, sections):
    """Best-effort: which section/page a finding's evidence text falls in.

    Matches the finding's `evidence` (agents are prompted to quote clause
    language directly) against the document's parsed_sections content, same
    substring-position approach as app/rules/ambiguous_language.py's
    _find_section. Findings without evidence, or where the evidence text
    doesn't match verbatim, simply get no location -- not every agent
    quotes evidence as strictly as Legal/PMO do.
    """
    if not evidence or not document_text or not sections:
        return None

    # Agents are prompted to "quote exactly" but often drop/add a trailing
    # period or the surrounding quote marks (e.g. quoting `"apply"` for
    # text that actually reads `"apply."` -- period inside the quote).
    # Strip both before matching instead of requiring byte-exact equality.
    normalized = evidence.strip().strip("\"'“”").rstrip(".,;: ")
    if not normalized:
        return None

    idx = document_text.find(normalized)
    if idx == -1:
        return None

    for section in sections:
        content = section.get("content") or ""
        if not content:
            continue
        start = document_text.find(content)
        if start == -1:
            continue
        if start <= idx < start + len(content):
            heading = section.get("heading") or "Unknown section"
            page = section.get("page_number")
            return f"{heading} (p.{page})" if page else heading

    return None

# Global orchestrator instance
_orchestrator: ReviewOrchestrator | None = None


async def get_orchestrator() -> ReviewOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ReviewOrchestrator()
        await _orchestrator.initialize()
    return _orchestrator


@router.post(
    "/{doc_id}/trigger",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger document review",
)
async def trigger_review(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger AI review for a document.

    Runs all agents (ScopeReviewer, DeliveryReviewer, etc.) in parallel
    and stores findings in the database.
    """
    from datetime import datetime
    from sqlalchemy import select

    # Get document
    result = await db.execute(
        select(Document).where(
            (Document.doc_id == doc_id) & (Document.deleted_at.is_(None))
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Verify org access
    await verify_org_access(str(doc.org_id), current_user)

    # Create review record
    from uuid import uuid4

    review_id = uuid4()
    review = Review(
        review_id=review_id,
        org_id=doc.org_id,
        doc_id=doc_id,
        triggered_by_user_id=UUID(str(current_user.user_id)),
        status="pending",
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    # T-510: Run review in background
    # (In production, this would be an async task via Celery/Redis)
    try:
        review.status = "running"
        await db.commit()

        orchestrator = await get_orchestrator()

        # Get document sections if parsed
        sections = {}
        if doc.parsed_sections:
            for section in doc.parsed_sections:
                sections[section.get("heading", "").lower()] = section.get("content", "")

        # T-2091/T-2092/T-2093: apply this org's rule/agent/scoring customization
        # (app/admin/customization.py) -- previously persisted but never enforced.
        from app.admin.customization import (
            get_agent_config,
            get_risk_weights,
            get_rule_config,
            get_scoring_weights,
        )

        rule_config = await get_rule_config(db, doc.org_id)
        agent_config = await get_agent_config(db, doc.org_id)
        scoring_weights = await get_scoring_weights(db, doc.org_id)
        risk_weights = await get_risk_weights(db, doc.org_id)
        enabled_rule_ids = {rule_id for rule_id, enabled in rule_config.items() if enabled}
        enabled_agent_names = {name for name, enabled in agent_config.items() if enabled}

        # Run orchestrated review
        orchestrated_result = await orchestrator.review(
            str(doc_id),
            doc.parsed_text or "",
            document_type=doc.document_type or "SOW",
            sections=sections,
            enabled_agent_names=enabled_agent_names,
            enabled_rule_ids=enabled_rule_ids,
        )

        # Store results in database
        review.status = "completed"
        review.completed_at = datetime.utcnow()
        review.overall_score = orchestrated_result.overall_confidence * 100
        review.processing_time_seconds = int(orchestrated_result.total_duration_seconds)

        # T-618: Calculate scores using scoring algorithm
        from app.scoring import DocumentScorer

        scorer = DocumentScorer(weight_overrides=scoring_weights, risk_weight_overrides=risk_weights)

        # Collect all findings for scoring (already flattened by
        # orchestrator._merge_findings -- agent_info["findings"] per-agent is
        # the raw agent JSON dict, not a list; using that here was the bug).
        all_findings = orchestrated_result.merged_findings.get("findings", [])

        scoring_result = await scorer.score_document(
            str(doc_id),
            all_findings,
            orchestrated_result.rule_violations,
        )

        # Store raw findings
        import json

        review.executive_summary = scoring_result.summary
        review.overall_score = scoring_result.overall_score
        review.risk_score = scoring_result.risk_score
        review.risk_breakdown = scoring_result.risk_breakdown

        # Store category scores
        for category, score_obj in scoring_result.category_scores.items():
            col = f"score_{category}"
            if hasattr(review, col):
                setattr(review, col, score_obj.score)

        # Count findings by severity
        critical_count = 0
        major_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0

        # Store individual findings (already flattened by
        # orchestrator._merge_findings, source_agent tagged per item --
        # iterating agent_info["findings"] directly was the bug: that's the
        # raw per-agent JSON dict, not a list, so it yielded dict KEYS as
        # strings instead of finding objects)
        for finding_data in orchestrated_result.merged_findings.get("findings", []):
            finding_type = finding_data.get("type", "unknown")
            finding = Finding(
                finding_id=uuid4(),
                org_id=doc.org_id,
                review_id=review_id,
                finding_source="agent",
                agent_name=finding_data.get("source_agent", "unknown"),
                category=finding_type,
                # Derived from `type` (e.g. "missing_liability_cap" -> "Missing
                # Liability Cap"), not copied from `description` -- title used
                # to be description[:255], so every finding card showed the
                # same text twice (title, then "Description" repeating it).
                title=finding_type.replace("_", " ").title()[:255],
                description=finding_data.get("description", ""),
                evidence=finding_data.get("evidence"),
                section_ref=_locate_finding(
                    finding_data.get("evidence"), doc.parsed_text, doc.parsed_sections or []
                ),
                severity=finding_data.get("severity", "medium"),
                confidence=int((finding_data.get("confidence", 0.5) * 100)),
                recommendation=finding_data.get("recommendation", ""),
            )

            db.add(finding)

            # Count by severity
            severity = finding_data.get("severity", "medium").lower()
            if severity == "critical":
                critical_count += 1
            elif severity == "major":
                major_count += 1
            elif severity == "medium":
                medium_count += 1
            elif severity == "low":
                low_count += 1
            else:
                info_count += 1

        # Store rule violations as findings
        for violation in orchestrated_result.rule_violations:
            finding = Finding(
                finding_id=uuid4(),
                org_id=doc.org_id,
                review_id=review_id,
                finding_source="rule",
                rule_id=violation.get("rule_id"),
                category=violation.get("rule_name", "Rule Violation")[:100],
                title=violation.get("rule_name", "")[:255],
                description=violation.get("description", ""),
                evidence=violation.get("evidence"),
                section_ref=_locate_finding(
                    violation.get("evidence"), doc.parsed_text, doc.parsed_sections or []
                ),
                severity=violation.get("severity", "medium"),
                confidence=100,
                recommendation=violation.get("recommendation", ""),
            )

            db.add(finding)

            # Count by severity
            severity = violation.get("severity", "medium").lower()
            if severity == "critical":
                critical_count += 1
            elif severity == "major":
                major_count += 1
            elif severity == "medium":
                medium_count += 1
            elif severity == "low":
                low_count += 1
            else:
                info_count += 1

        review.critical_finding_count = critical_count
        review.major_finding_count = major_count
        review.medium_finding_count = medium_count
        review.low_finding_count = low_count
        review.info_finding_count = info_count

        # Phase C (Document Lifecycle plan): if this document has an earlier
        # version with a completed review, verify that version's findings
        # against what this re-review actually found.
        await _verify_against_previous_version(db, doc, review)

        # T-2041: audit trail
        await log_action(
            db,
            org_id=review.org_id,
            user_id=review.triggered_by_user_id,
            action="review.completed",
            resource_type="review",
            resource_id=review_id,
            details={
                "overall_score": float(review.overall_score)
                if review.overall_score is not None
                else None
            },
        )

        await db.commit()

        # T-3019: this org's cached analytics/dashboard/metrics are stale now
        await invalidate_cache(f"cache:*:{review.org_id}:*")

        logger.info(
            f"Review {review_id} completed for doc {doc_id}: "
            f"{critical_count} critical, {major_count} major, {medium_count} medium findings"
        )

        return {
            "review_id": str(review_id),
            "status": "completed",
            "findings_count": {
                "critical": critical_count,
                "major": major_count,
                "medium": medium_count,
                "low": low_count,
                "info": info_count,
            },
        }

    except Exception as e:
        logger.exception(f"Review failed for doc {doc_id}: {e}")
        review.status = "failed"
        review.error_message = str(e)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review processing failed",
        )


@router.get(
    "/{review_id}",
    summary="Get review results",
)
async def get_review(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review results and findings."""
    from sqlalchemy import select

    result = await db.execute(
        select(Review).where(
            (Review.review_id == review_id) & (Review.deleted_at.is_(None))
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    # Verify org access
    await verify_org_access(str(review.org_id), current_user)

    # Get all findings
    findings_result = await db.execute(
        select(Finding).where(
            (Finding.review_id == review_id) & (Finding.deleted_at.is_(None))
        )
    )
    findings = findings_result.scalars().all()

    return {
        "review_id": str(review.review_id),
        "doc_id": str(review.doc_id),
        "status": review.status,
        "overall_score": float(review.overall_score) if review.overall_score is not None else None,
        "risk_score": float(review.risk_score) if review.risk_score is not None else None,
        "risk_breakdown": review.risk_breakdown,
        "processing_time_seconds": review.processing_time_seconds,
        "findings_count": {
            "critical": review.critical_finding_count,
            "major": review.major_finding_count,
            "medium": review.medium_finding_count,
            "low": review.low_finding_count,
            "info": review.info_finding_count,
        },
        "findings": [
            {
                "finding_id": str(f.finding_id),
                "finding_source": f.finding_source,
                "agent_name": f.agent_name,
                "rule_id": f.rule_id,
                "category": f.category,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence,
                "section_ref": f.section_ref,
                "severity": f.severity,
                "confidence": int(f.confidence),
                "recommendation": f.recommendation,
                "status": f.status,
                "risk_area": _risk_area(f),
            }
            for f in findings
        ],
    }


@router.get(
    "/{review_id}/report",
    summary="Generate report",
)
async def generate_report(
    review_id: UUID,
    format: str = "html",
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate report for a review.

    T-615: Generate and download report
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Review).where(
            (Review.review_id == review_id) & (Review.deleted_at.is_(None))
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    # Verify org access
    await verify_org_access(str(review.org_id), current_user)

    # Get document
    doc_result = await db.execute(
        select(Document).where(Document.doc_id == review.doc_id)
    )
    doc = doc_result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Get findings
    findings_result = await db.execute(
        select(Finding).where(
            (Finding.review_id == review_id) & (Finding.deleted_at.is_(None))
        )
    )
    findings = findings_result.scalars().all()

    # Build scoring result from stored data
    from app.scoring.algorithm import CategoryScore, DocumentScorer, ScoringResult

    findings_dicts = [
        {
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "category": f.category,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
            "source_agent": f.agent_name,
        }
        for f in findings
    ]

    # Recompute against the real findings so category_scores[c].findings and
    # next_steps are populated (previously always [] here -- the endpoint
    # only rebuilt bare CategoryScore numbers from stored columns) -- but
    # keep the *displayed* score/status from the stored review columns
    # below, so numbers stay pinned to what the review actually scored.
    recomputed = await DocumentScorer().score_document(str(review.doc_id), findings_dicts, [])

    category_scores = {}
    for category in ["completeness", "clarity", "consistency", "commercial", "delivery", "operations", "security"]:
        col = f"score_{category}"
        score_val = getattr(review, col, None)
        # `is not None`, not truthy: a category legitimately scoring 0 (the
        # worst case -- critical findings everywhere) is falsy and was being
        # silently dropped from the report/heatmap, hiding exactly the
        # category a reviewer most needs to see.
        if score_val is not None:
            recomputed_cat = recomputed.category_scores.get(category)
            category_scores[category] = CategoryScore(
                category=category,
                score=float(score_val),
                max_points=100,
                points_earned=int(score_val),
                findings=recomputed_cat.findings if recomputed_cat else [],
                status="green" if score_val >= 80 else ("yellow" if score_val >= 50 else "red"),
            )

    scoring_result = ScoringResult(
        doc_id=str(review.doc_id),
        overall_score=float(review.overall_score) if review.overall_score is not None else 0.0,
        risk_score=float(review.risk_score) if review.risk_score is not None else 0.0,
        category_scores=category_scores,
        summary=review.executive_summary or "Review complete.",
        next_steps=recomputed.next_steps,
        risk_breakdown=review.risk_breakdown or {},
    )

    # Generate report
    from app.scoring import ReportGenerator

    generator = ReportGenerator()

    findings_list = [
        {
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
            "section_ref": f.section_ref,
        }
        for f in findings
    ]

    doc_meta = {
        "document_type": doc.document_type,
        "version": doc.version,
        "page_count": doc.page_count,
        "project_name": doc.project_name,
        "reviewed_at": review.completed_at.strftime("%Y-%m-%d") if review.completed_at else None,
    }
    findings_count = {
        "critical": review.critical_finding_count,
        "major": review.major_finding_count,
        "medium": review.medium_finding_count,
        "low": review.low_finding_count,
        "info": review.info_finding_count,
    }
    rule_gaps = [
        {"title": f.title, "description": f.description}
        for f in findings
        if f.finding_source == "rule"
    ]

    html_report = await generator.generate_html_report(
        str(review.doc_id),
        doc.original_filename or doc.filename,
        scoring_result,
        findings_list,
        doc_meta=doc_meta,
        findings_count=findings_count,
        sections=doc.parsed_sections or [],
        rule_gaps=rule_gaps,
    )

    if format.lower() == "pdf":
        import base64

        pdf_bytes = await generator.generate_pdf_report(html_report, doc.filename)
        return {
            "format": "pdf",
            # base64, not a lossy UTF-8 decode -- pdf_bytes is binary and
            # decode("utf-8", errors="ignore") was silently corrupting it.
            "data": base64.b64encode(pdf_bytes).decode("ascii"),
        }
    else:
        return {
            "format": "html",
            "data": html_report,
        }


@router.get(
    "",
    summary="List reviews",
)
async def list_reviews(
    doc_id: UUID | None = Query(None),
    org_id: UUID = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reviews for an organization or document."""
    from sqlalchemy import select

    # Verify org access
    await verify_org_access(str(org_id), current_user)

    query = select(Review).where(
        (Review.org_id == org_id) & (Review.deleted_at.is_(None))
    )

    if doc_id:
        query = query.where(Review.doc_id == doc_id)

    query = query.offset(skip).limit(limit).order_by(Review.created_at.desc())

    result = await db.execute(query)
    reviews = result.scalars().all()

    return [
        {
            "review_id": str(r.review_id),
            "doc_id": str(r.doc_id),
            "status": r.status,
            "overall_score": float(r.overall_score) if r.overall_score is not None else None,
            "findings_count": {
                "critical": r.critical_finding_count,
                "major": r.major_finding_count,
                "medium": r.medium_finding_count,
                "low": r.low_finding_count,
                "info": r.info_finding_count,
            },
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.patch(
    "/{review_id}/findings/{finding_id}",
    summary="Update a finding's status (e.g. mark fixed)",
)
async def update_finding_status(
    review_id: UUID,
    finding_id: UUID,
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a finding acknowledged/resolved/dismissed/reopened (open)."""
    from sqlalchemy import select

    allowed = {"open", "acknowledged", "resolved", "dismissed"}
    new_status = body.get("status")
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {sorted(allowed)}",
        )

    result = await db.execute(
        select(Finding).where(
            (Finding.finding_id == finding_id)
            & (Finding.review_id == review_id)
            & (Finding.deleted_at.is_(None))
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    await verify_org_access(str(finding.org_id), current_user)

    finding.status = new_status
    await db.commit()

    return {"finding_id": str(finding.finding_id), "status": finding.status}
