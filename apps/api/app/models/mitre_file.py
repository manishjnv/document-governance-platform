"""MitreFile ORM model. Uploaded MITRE-assessment source file (migration 029)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MitreFile(Base, TimestampMixin, SoftDeleteMixin):
    """Use-case dump or environment workbook backing an assessment."""

    __tablename__ = "mitre_files"
    __table_args__ = (
        CheckConstraint("kind IN ('use_cases', 'environment')", name="ck_mitre_files_kind"),
        CheckConstraint(
            "file_type IN ('xlsx', 'xls', 'csv', 'pdf', 'docx')",
            name="ck_mitre_files_file_type",
        ),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
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
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    s3_path: Mapped[str] = mapped_column(String(500), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(50), nullable=False, default="parsed")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
