"""Persisted, dismissible version-link suggestions (Phase B of Document
Lifecycle plan). Generated after any upload; stays visible on the
Documents page until accepted or dismissed -- not a one-time toast."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentLinkSuggestion(Base):
    __tablename__ = "document_link_suggestions"
    __table_args__ = (
        UniqueConstraint("doc_id", name="uq_document_link_suggestions_doc"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'dismissed')",
            name="ck_document_link_suggestions_status",
        ),
    )

    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False
    )
    suggested_doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
