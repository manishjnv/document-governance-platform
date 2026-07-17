"""Organization (tenant) ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import SubscriptionTier

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.kb_article import KBArticle
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
        # ponytail: portable (SQLite + Postgres) sanity check only — length=7
        # and leading '#', not full hex-digit validation. SQLite has no
        # regex operator, so a strict `~ '^#[0-9A-Fa-f]{6}$'` check here
        # would break `Base.metadata.create_all` for every test, not just
        # admin tests. The strict regex lives in two places that don't have
        # that constraint: migrations/004_phase2_admin.sql (real Postgres)
        # and the admin router's Pydantic request schema (pattern=...).
        CheckConstraint(
            "(brand_primary_color IS NULL OR "
            "(length(brand_primary_color) = 7 AND substr(brand_primary_color, 1, 1) = '#')) AND "
            "(brand_secondary_color IS NULL OR "
            "(length(brand_secondary_color) = 7 AND substr(brand_secondary_color, 1, 1) = '#'))",
            name="ck_organizations_brand_colors_format",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionTier.FREE.value
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    brand_primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    brand_secondary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    kb_articles: Mapped[list["KBArticle"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
