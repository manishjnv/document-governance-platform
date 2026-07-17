"""Document ORM model. One row per uploaded version."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import FileType, StorageStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.review import Review


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """Uploaded document. document_group_id links versions of the same logical document."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("file_type IN ('pdf', 'docx')", name="ck_documents_file_type"),
        CheckConstraint(
            "document_type IS NULL OR document_type IN ('SOW', 'Proposal', 'RFP', 'Other')",
            name="ck_documents_document_type",
        ),
        CheckConstraint(
            "storage_status IN ('uploaded', 'archived', 'deleted_from_s3')",
            name="ck_documents_storage_status",
        ),
        CheckConstraint("version > 0", name="ck_documents_version_positive"),
        CheckConstraint("file_size_bytes > 0", name="ck_documents_file_size_positive"),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 0", name="ck_documents_page_count_nonneg"
        ),
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    s3_path: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_etag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_sections: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    storage_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=StorageStatus.UPLOADED.value
    )

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
