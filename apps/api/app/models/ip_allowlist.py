"""IPAllowlistEntry ORM model. Org-level IP allowlist (T-2060, opt-in feature)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IPAllowlistEntry(Base):
    """One allowed CIDR range for an org. An org with zero rows has IP
    restriction turned off entirely -- see app.compliance.ip_policy.is_ip_allowed.
    """

    __tablename__ = "ip_allowlist"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    cidr: Mapped[str] = mapped_column(String(43), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )
