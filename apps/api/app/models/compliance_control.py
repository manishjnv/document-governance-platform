"""Compliance control ORM model for framework tracking.

T-2051 (SOC2), T-2052 (ISO27001), T-2053 (GDPR), T-2054 (HIPAA),
T-2055 (compliance report generation)

Self-reported implementation status of starter compliance-control checklists.
This is a self-assessment tool, not a certification or audit.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ComplianceControl(Base, TimestampMixin):
    """Compliance control tracking for SOC2, ISO27001, GDPR, HIPAA."""

    __tablename__ = "compliance_controls"
    __table_args__ = (
        CheckConstraint(
            "framework IN ('SOC2', 'ISO27001', 'GDPR', 'HIPAA')",
            name="ck_compliance_controls_framework",
        ),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'implemented', 'verified')",
            name="ck_compliance_controls_status",
        ),
    )

    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    framework: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    control_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started", index=True
    )
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, default=None
    )
