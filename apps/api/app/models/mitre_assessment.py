"""MitreAssessment ORM model. One row per MITRE ATT&CK coverage-assessment run.

Isolated MITRE module (migration 029) — no relationships to existing models;
FK columns only, so no existing model file changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MitreAssessment(Base, TimestampMixin, SoftDeleteMixin):
    """MITRE coverage assessment. technique_results/summary are materialized
    once at run time against the stamped attack_version."""

    __tablename__ = "mitre_assessments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_mitre_assessments_status",
        ),
        CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name="ck_mitre_assessments_completed_has_timestamp",
        ),
        CheckConstraint(
            "status <> 'failed' OR error_message IS NOT NULL",
            name="ck_mitre_assessments_failed_has_error",
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    attack_version: Mapped[str] = mapped_column(String(20), nullable=False)
    params: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    technique_results: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
