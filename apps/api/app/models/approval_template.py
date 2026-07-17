"""Approval template ORM model. Reusable approval workflows (T-2068)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UUIDListJSONB(TypeDecorator):
    """JSONB column that round-trips a Python list[uuid.UUID].

    Plain JSONB can't serialize uuid.UUID objects (json.dumps raises
    TypeError). Convert to str on the way in, back to uuid.UUID on the way
    out, so callers (create_template/apply_template) can pass and receive
    real UUID objects like every other UUID-typed column in this codebase.
    """

    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return [str(v) for v in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return [uuid.UUID(v) for v in value]


class ApprovalTemplate(Base):
    """Reusable approval workflow template — specifies approvers and mode (parallel/serial)."""

    __tablename__ = "approval_templates"
    __table_args__ = (
        CheckConstraint("mode IN ('parallel', 'serial')", name="ck_approval_templates_mode"),
        CheckConstraint(
            "jsonb_array_length(approver_user_ids) > 0",
            name="ck_approval_templates_approvers",
        ),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # List of approver user UUIDs as JSONB array for flexible list handling
    approver_user_ids: Mapped[list] = mapped_column(UUIDListJSONB, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="parallel")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="clock_timestamp()")
