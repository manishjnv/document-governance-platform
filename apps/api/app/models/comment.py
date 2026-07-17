"""Comment ORM model. Document comments and inline annotations (T-2061, T-2062)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class Comment(Base, TimestampMixin, SoftDeleteMixin):
    """Comment on a document. parent_comment_id threads a reply (stored flat — nesting
    is a presentation concern, not a storage one). anchor_start/anchor_end mark an
    inline annotation range into the document's text; both NULL = a doc-level comment.
    """

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint(
            "anchor_start IS NULL OR (anchor_end IS NOT NULL AND anchor_end >= anchor_start)",
            name="ck_comments_anchor_range",
        ),
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.comment_id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    anchor_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mentioned_user_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
