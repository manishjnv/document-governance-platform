"""Organization (tenant) ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import SubscriptionTier

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.review import Review
    from app.models.user import User


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Tenant container. Every other table is scoped to org_id for isolation."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "subscription_tier IN ('free', 'pro', 'enterprise')",
            name="ck_organizations_subscription_tier",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionTier.FREE.value
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
