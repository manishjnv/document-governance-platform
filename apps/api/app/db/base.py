"""Declarative base and shared column mixins for SQLAlchemy ORM models.

Engine/session lifecycle (async engine, connection pooling, sessionmaker)
is T-214 — out of scope here. This module only provides what the model
classes in app/models need to exist: a shared declarative Base plus the
created_at/updated_at/deleted_at triplet that organizations, users,
documents, reviews, and findings all repeat identically.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all EDGP ORM models."""


class TimestampMixin:
    """created_at / updated_at, matching the DB-side set_updated_at() trigger."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )


class SoftDeleteMixin:
    """deleted_at marker. Rows are never hard-deleted by the application —
    repositories must filter `deleted_at IS NULL` (see T-218)."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
