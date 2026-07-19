"""Review ORM model. One row per AI review execution against a document version."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import ReviewStatus

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.finding import Finding
    from app.models.organization import Organization


class Review(Base, TimestampMixin, SoftDeleteMixin):
    """AI review execution. document_version records which document version was reviewed."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')", name="ck_reviews_status"
        ),
        CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name="ck_reviews_completed_has_timestamp",
        ),
        CheckConstraint(
            "status <> 'failed' OR error_message IS NOT NULL",
            name="ck_reviews_failed_has_error",
        ),
        CheckConstraint(
            "critical_finding_count >= 0 AND major_finding_count >= 0 AND "
            "medium_finding_count >= 0 AND low_finding_count >= 0 AND info_finding_count >= 0",
            name="ck_reviews_finding_counts_nonneg",
        ),
        CheckConstraint(
            "processing_time_seconds IS NULL OR processing_time_seconds >= 0",
            name="ck_reviews_processing_time_nonneg",
        ),
        CheckConstraint("document_version > 0", name="ck_reviews_document_version_positive"),
        # Score-range CHECK spanning all 9 score columns lives in the SQL
        # migration (a single CheckConstraint string here would just repeat
        # it) — this ORM model relies on the DB constraint, not a duplicate.
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False
    )
    document_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    triggered_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ReviewStatus.PENDING.value
    )
    overall_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    risk_breakdown: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    score_completeness: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_clarity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_consistency: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_commercial: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_delivery: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_operations: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    score_security: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    executive_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    critical_finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    major_finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    info_finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="reviews")
    document: Mapped["Document"] = relationship(back_populates="reviews")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
