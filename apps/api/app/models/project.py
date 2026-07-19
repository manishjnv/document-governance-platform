"""Project ORM model. Organizes documents into a first-class group (Phase A
of the Document Lifecycle plan) -- replaces free-text Document.project_name."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.organization import Organization


class Project(Base):
    """One row per named project within an org. Unique on (org_id, name)."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_projects_org_name"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
