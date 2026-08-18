"""MitreUseCase ORM model. One detection rule parsed from a use-case dump
(migration 029). mappings JSONB: [{technique_id, source, confidence,
rationale}] — the Phase 0 coverage contract shape.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MitreUseCase(Base, TimestampMixin, SoftDeleteMixin):
    """Detection rule row. enabled is nullable — NULL means status unknown
    (coverage treats it as enabled and records an assumption)."""

    __tablename__ = "mitre_use_cases"
    __table_args__ = (
        CheckConstraint(
            # keep in lockstep with migrations 033/038 (the 5th migration
            # sync point — a create_all-bootstrapped DB gets THIS constraint)
            "mapping_status IN ('customer_tagged', 'keyword_tagged', "
            "'ai_tagged', 'manual', 'tool_attested', 'unmapped', 'invalid')",
            name="ck_mitre_use_cases_mapping_status",
        ),
    )

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mitre_assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mitre_files.file_id", ondelete="SET NULL"), nullable=True
    )
    row_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Detection condition/query text (migration 032) — kept distinct from
    # description; capped at 2000 chars by the router at create time.
    logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # Migration 036 (Phase A6): optional customer-provided health columns.
    # severity: leniently-parsed free text (critical/high/medium/low/... or
    # raw). last_triggered: an ISO-ish date string or the literal "never";
    # NULL when the column was absent/blank in the dump. Both feed small
    # quality.py strength adjustments only — never coverage/state.
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_triggered: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mappings: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unmapped")
