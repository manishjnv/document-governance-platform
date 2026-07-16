"""Review management API endpoints.

T-510: Rule management API
T-509: Store review results in database
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import ReviewOrchestrator
from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

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
        status="running",
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    # T-510: Run review in background
    # (In production, this would be an async task via Celery/Redis)
    try:
        orchestrator = await get_orchestrator()

        # Get document sections if parsed
        sections = {}
        if doc.parsed_sections:
            for section in doc.parsed_sections:
                sections[section.get("heading", "").lower()] = section.get("content", "")

        # Run orchestrated review
        orchestrated_result = await orchestrator.review(
            str(doc_id),
            doc.parsed_text or "",
            document_type=doc.document_type or "SOW",
            sections=sections,
        )

        # Store results in database
        review.status = "completed"
        review.overall_score = orchestrated_result.overall_confidence * 100
        review.processing_time_seconds = int(orchestrated_result.total_duration_seconds)

        # T-618: Calculate scores using scoring algorithm
        from app.scoring import DocumentScorer

        scorer = DocumentScorer()

        # Collect all findings for scoring
        all_findings = []
        for agent_name, agent_info in orchestrated_result.merged_findings.get("agents", {}).items():
            if agent_info.get("status") == "success":
                all_findings.extend(agent_info.get("findings", []))

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

        # Store individual findings
        for agent_name, agent_info in orchestrated_result.merged_findings.get("agents", {}).items():
            if agent_info.get("status") == "success":
                for finding_data in agent_info.get("findings", []):
                    finding = Finding(
                        finding_id=uuid4(),
                        org_id=doc.org_id,
                        review_id=review_id,
                        finding_source="agent",
                        agent_name=agent_name,
                        category=finding_data.get("type", "unknown"),
                        title=finding_data.get("description", "")[:255],
                        description=finding_data.get("description", ""),
                        evidence=finding_data.get("evidence"),
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

        await db.commit()

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
        logger.error(f"Review failed for doc {doc_id}: {e}")
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
        "overall_score": float(review.overall_score) if review.overall_score else None,
        "risk_score": float(review.risk_score) if review.risk_score else None,
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
                "severity": f.severity,
                "confidence": int(f.confidence),
                "recommendation": f.recommendation,
                "status": f.status,
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
    from app.scoring.algorithm import CategoryScore, ScoringResult

    category_scores = {}
    for category in ["completeness", "clarity", "consistency", "commercial", "delivery", "operations", "security"]:
        col = f"score_{category}"
        score_val = getattr(review, col, None)
        if score_val:
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
        }
        for f in findings
    ]

    html_report = await generator.generate_html_report(
        str(review.doc_id),
        doc.original_filename or doc.filename,
        scoring_result,
        findings_list,
    )

    if format.lower() == "pdf":
        pdf_bytes = await generator.generate_pdf_report(html_report, doc.filename)
        return {
            "format": "pdf",
            "data": pdf_bytes.decode("utf-8", errors="ignore"),
        }
    else:
        # Fix the HTML: complete the executive summary section
        html_report = html_report.replace(
            "</section>",
            generator._continue_summary(scoring_result) + "</section>",
            1,
        )
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
            "overall_score": float(r.overall_score) if r.overall_score else None,
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
