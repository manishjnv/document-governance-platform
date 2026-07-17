"""ResourceGrant ORM model. Fine-grained per-resource access grant (T-2056).

No soft delete: a revoked or expired grant is hard-deleted, not marked
deleted_at -- see app.compliance.access_control.revoke_access and
purge_expired_grants. TimestampMixin's updated_at is never written after
creation in practice (a grant is created once, then deleted on
revoke/expire, never patched) but is kept for consistency with every other
mixin-based table; migrations/010_phase2_access_control.sql carries the
matching column.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ResourceGrant(Base, TimestampMixin):
    """Grants `permission` on (resource_type, resource_id) to grantee_user_id."""

    __tablename__ = "resource_grants"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('document', 'review')", name="ck_resource_grants_resource_type"
        ),
        CheckConstraint(
            "permission IN ('view', 'comment', 'edit', 'approve')",
            name="ck_resource_grants_permission",
        ),
    )

    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    grantee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String(50), nullable=False)
    granted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
