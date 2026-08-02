"""MitreConnection ORM model (migration 034, Phase 13b): an org's saved
SIEM connection. `config` is non-secret parameters only;
`secret_ciphertext` is AES-256-GCM output from app/mitre/connectors/vault
(nonce || ciphertext||tag, AAD-bound to connection_id) with `key_version`
for rotation. The plaintext secret exists only transiently inside the
connector call — it is never a column, never in `config`, never logged.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MitreConnection(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mitre_connections"
    __table_args__ = (
        CheckConstraint(
            # keep in lockstep with migration 034 (the 5th migration sync
            # point — a create_all-bootstrapped DB gets THIS constraint)
            "platform IN ('sentinel')",
            name="ck_mitre_connections_platform",
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
