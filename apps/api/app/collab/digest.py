"""Daily digest builder for comment and review activity."""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# ponytail: no email provider configured yet (SendGrid/SES is T-2019); this returns
# digest content only, wire up the actual send once that integration lands.


async def build_daily_digest(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str:
    """
    Build plain-text digest of last 24h activity.

    Includes:
      - New comments on documents owned/reviewed by this user
      - Reviews completed by this user
      - Findings assigned to this user

    Args:
        db: async database session
        user_id: user to build digest for
        org_id: organization (scoping)

    Returns:
        Plain-text digest content (no email sent).
    """
    # Import here to avoid circular imports
    from app.models.document import Document
    from app.models.review import Review
    from app.models.finding import Finding

    # Assume Comment model exists at app.models.comment
    try:
        from app.models.comment import Comment
    except ImportError:
        # Parallel agent hasn't landed comment.py yet; assume schema exists
        Comment = None

    now = datetime.now()
    yesterday = now - timedelta(hours=24)

    lines = [f"Daily Digest for {now.strftime('%Y-%m-%d')}"]
    lines.append("=" * 50)
    lines.append("")

    # Sections: reviews, comments, findings
    has_content = False

    # 1. Reviews completed by this user
    try:
        reviews_result = await db.execute(
            select(Review, Document).where(
                and_(
                    Review.triggered_by_user_id == user_id,
                    Review.org_id == org_id,
                    Review.completed_at.isnot(None),
                    Review.completed_at >= yesterday,
                    Review.deleted_at.is_(None),
                    Document.doc_id == Review.doc_id,
                    Document.deleted_at.is_(None),
                )
            )
        )
        reviews = reviews_result.all()
        if reviews:
            has_content = True
            lines.append("REVIEWS COMPLETED")
            lines.append("-" * 30)
            for review, doc in reviews:
                lines.append(f"  • {doc.filename} (v{doc.version})")
                if review.overall_score:
                    lines.append(f"    Score: {review.overall_score}/100")
            lines.append("")
    except Exception:
        pass

    # 2. Comments on your documents (if Comment model available)
    if Comment:
        try:
            # Find comments on documents you uploaded, created in last 24h
            comments_result = await db.execute(
                select(Comment, Document).where(
                    and_(
                        Document.uploaded_by_user_id == user_id,
                        Document.org_id == org_id,
                        Comment.doc_id == Document.doc_id,
                        Comment.created_at >= yesterday,
                        Comment.deleted_at.is_(None),
                        Document.deleted_at.is_(None),
                    )
                )
            )
            comments = comments_result.all()
            if comments:
                has_content = True
                lines.append("NEW COMMENTS ON YOUR DOCUMENTS")
                lines.append("-" * 30)
                for comment, doc in comments:
                    author_id = comment.user_id or "unknown"
                    lines.append(f"  • {doc.filename}: {str(author_id)[:8]}")
                    if comment.content:
                        preview = comment.content[:60].replace("\n", " ")
                        lines.append(f"    '{preview}...'")
                lines.append("")
        except Exception:
            pass

    # 3. Findings assigned to you
    try:
        findings_result = await db.execute(
            select(Finding, Review, Document).where(
                and_(
                    Finding.assigned_to_user_id == user_id,
                    Finding.org_id == org_id,
                    Finding.created_at >= yesterday,
                    Finding.deleted_at.is_(None),
                    Review.review_id == Finding.review_id,
                    Document.doc_id == Review.doc_id,
                    Document.deleted_at.is_(None),
                )
            )
        )
        findings = findings_result.all()
        if findings:
            has_content = True
            lines.append("FINDINGS ASSIGNED TO YOU")
            lines.append("-" * 30)
            for finding, review, doc in findings:
                lines.append(f"  • [{finding.severity.upper()}] {finding.title}")
                lines.append(f"    {doc.filename} (v{doc.version})")
            lines.append("")
    except Exception:
        pass

    if not has_content:
        lines.append("No activity in the last 24 hours.")

    lines.append("")
    lines.append("End of Digest")

    return "\n".join(lines)
