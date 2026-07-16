"""Finding ORM model. AI agent findings and rule-engine hits, per review."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import FindingSource, FindingStatus, Severity

if TYPE_CHECKING:
    from app.models.review import Review


class Finding(Base, TimestampMixin, SoftDeleteMixin):
    """Individual finding attached to a review — an AI agent observation or a rule hit."""

    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint("finding_source IN ('agent', 'rule')", name="ck_findings_source"),
        CheckConstraint(
            "(finding_source = 'agent' AND agent_name IS NOT NULL AND rule_id IS NULL) OR "
            "(finding_source = 'rule' AND rule_id IS NOT NULL AND agent_name IS NULL)",
            name="ck_findings_source_origin",
        ),
        CheckConstraint(
            "severity IN ('critical', 'major', 'medium', 'low', 'info')",
            name="ck_findings_severity",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_findings_confidence_range"),
        CheckConstraint(
            "business_impact IS NULL OR business_impact IN ('high', 'medium', 'low')",
            name="ck_findings_business_impact",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="ck_findings_status",
        ),
    )

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False
    )

    finding_source: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("100.00"))
    business_impact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default=FindingStatus.OPEN.value)
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    review: Mapped["Review"] = relationship(back_populates="findings")
