"""Bulk document operations. T-2013: Batch review trigger for multiple documents."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.schemas.auth import TokenData
from app.routers.reviews import get_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents-bulk"])


@router.post("/bulk-review", status_code=status.HTTP_202_ACCEPTED, summary="Trigger review for multiple documents")
async def bulk_trigger_review(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger AI review for multiple documents in bulk.

    Request body: {"doc_ids": list[str]}

    Returns per-document status:
      [{"doc_id": str, "status": "triggered"|"error", "detail": str|None}, ...]
    """
    doc_ids = body.get("doc_ids", [])

    if not isinstance(doc_ids, list) or not doc_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="doc_ids must be a non-empty list",
        )

    # Fetch all docs in one query to verify org_id and existence. Ignore
    # malformed doc_ids here -- the per-item loop below reports them as
    # "Invalid UUID format" instead of 500ing the whole batch.
    parsed_ids = []
    for doc_id in doc_ids:
        try:
            parsed_ids.append(UUID(doc_id))
        except (ValueError, AttributeError, TypeError):
            continue

    result = await db.execute(
        select(Document).where(
            (Document.doc_id.in_(parsed_ids)) & (Document.deleted_at.is_(None))
        )
    )
    docs_by_id = {doc.doc_id: doc for doc in result.scalars().all()}

    # Verify org access for all docs
    await verify_org_access(str(current_user.org_id), current_user)

    status_list = []

    for doc_id_str in doc_ids:
        try:
            doc_id = UUID(doc_id_str)
        except ValueError:
            status_list.append({
                "doc_id": doc_id_str,
                "status": "error",
                "detail": "Invalid UUID format",
            })
            continue

        doc = docs_by_id.get(doc_id)

        # A prior doc in this batch may have hit a DB error and rolled back
        # the shared session -- rollback() expires every ORM object attached
        # to it (SQLAlchemy default), including docs already fetched above
        # but not yet processed. Touching an expired attribute (doc.org_id
        # below) would otherwise make the async ORM try a synchronous
        # lazy-refresh outside of greenlet context and blow up with
        # "greenlet_spawn has not been called". Refresh eagerly first.
        if doc is not None and inspect(doc).expired:
            await db.refresh(doc)

        # Document not found or doesn't belong to org
        if not doc or doc.org_id != UUID(str(current_user.org_id)):
            status_list.append({
                "doc_id": doc_id_str,
                "status": "error",
                "detail": "Document not found or access denied",
            })
            continue

        # Trigger review (reuse the orchestrator pattern from reviews.py)
        try:
            from datetime import datetime, timezone
            from uuid import uuid4

            from app.models.review import Review

            # Create review record
            review_id = uuid4()
            review = Review(
                review_id=review_id,
                org_id=doc.org_id,
                doc_id=doc_id,
                triggered_by_user_id=UUID(str(current_user.user_id)),
                status="running",
            )

            db.add(review)
            await db.flush()

            # Run orchestrated review in background
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

                # Store results (abbreviated; full flow in reviews.py)
                review.status = "completed"
                # ck_reviews_completed_has_timestamp requires completed_at
                # whenever status='completed' -- omitting it made every
                # successful review fail its commit with a CheckViolation,
                # which triggered the rollback (and the expired-attribute
                # crash above) on the next doc in the batch.
                review.completed_at = datetime.now(timezone.utc)
                review.overall_score = orchestrated_result.overall_confidence * 100
                review.processing_time_seconds = int(orchestrated_result.total_duration_seconds)

                # Store findings
                from app.models.finding import Finding
                from app.scoring import DocumentScorer

                scorer = DocumentScorer()
                all_findings = []
                for agent_name, agent_info in orchestrated_result.merged_findings.get("agents", {}).items():
                    if agent_info.get("status") == "success":
                        all_findings.extend(agent_info.get("findings", []))

                scoring_result = await scorer.score_document(
                    str(doc_id),
                    all_findings,
                    orchestrated_result.rule_violations,
                )

                review.executive_summary = scoring_result.summary
                review.overall_score = scoring_result.overall_score
                review.risk_score = scoring_result.risk_score

                # Count findings by severity
                critical_count = 0
                major_count = 0
                medium_count = 0
                low_count = 0
                info_count = 0

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

                logger.info(
                    f"Bulk review {review_id} completed for doc {doc_id}: "
                    f"{critical_count} critical, {major_count} major findings"
                )

            except Exception as e:
                logger.error(f"Bulk review failed for doc {doc_id}: {e}")
                review.status = "failed"
                review.error_message = str(e)

            await db.commit()

            status_list.append({
                "doc_id": doc_id_str,
                "status": "triggered",
                "detail": None,
            })

        except Exception as e:
            logger.error(f"Failed to trigger bulk review for doc {doc_id}: {e}")
            await db.rollback()

            status_list.append({
                "doc_id": doc_id_str,
                "status": "error",
                "detail": str(e),
            })

    return {"results": status_list}
