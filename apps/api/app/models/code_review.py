"""CodeReview ORM model. One row per imported VVAH findings.json/SARIF report.

Isolated Code Security Review module (migration 039) — no relationships to
existing models; FK columns only, so no existing model file changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class CodeReview(Base, TimestampMixin, SoftDeleteMixin):
    """Imported code-security scan report (VVAH findings.json or SARIF)."""

    __tablename__ = "code_reviews"
    __table_args__ = (
        CheckConstraint(
            "source_format IN ('findings', 'sarif')",
            name="ck_code_reviews_source_format",
        ),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    git_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_format: Mapped[str] = mapped_column(String(10), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    manifest_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    report: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
