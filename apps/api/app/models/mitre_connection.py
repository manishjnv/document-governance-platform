"""MitreConnection ORM model (migration 034, Phase 13b): an org's saved
SIEM connection. `config` is non-secret parameters only;
`secret_ciphertext` is AES-256-GCM output from app/mitre/connectors/vault
(nonce || ciphertext||tag, AAD-bound to connection_id) with `key_version`
for rotation. The plaintext secret exists only transiently inside the
connector call — it is never a column, never in `config`, never logged.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MitreConnection(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mitre_connections"
    __table_args__ = (
        # keep in lockstep with migrations 034/035 (the 5th migration sync
        # point — a create_all-bootstrapped DB gets THESE constraints)
        CheckConstraint(
            "platform IN ('sentinel')",
            name="ck_mitre_connections_platform",
        ),
        CheckConstraint(
            "schedule_cadence IS NULL OR schedule_cadence IN ('daily', 'weekly')",
            name="ck_mitre_connections_schedule_cadence",
        ),
        CheckConstraint(
            "schedule_hour_utc IS NULL OR (schedule_hour_utc >= 0 AND schedule_hour_utc <= 23)",
            name="ck_mitre_connections_schedule_hour",
        ),
        CheckConstraint(
            "schedule_weekday IS NULL OR (schedule_weekday >= 0 AND schedule_weekday <= 6)",
            name="ck_mitre_connections_schedule_weekday",
        ),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    config: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    secret_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    # Phase 13c (migration 035): auto-run schedule, off unless cadence set.
    schedule_cadence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    schedule_hour_utc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
