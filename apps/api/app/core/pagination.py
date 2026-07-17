"""Offset-based pagination helper. T-3006.

Reuses the skip/limit convention already present in documents.py/audit.py,
just packaged so new list endpoints don't hand-roll offset/limit/count math.
"""

from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Page/page_size query params with sane defaults and an upper bound."""

    page: int = Query(1, ge=1, description="1-indexed page number")
    page_size: int = Query(50, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


async def paginate(query: Select, db: AsyncSession, params: PaginationParams) -> dict:
    """Run `query` (a SELECT of ORM entities, no limit/offset applied yet)
    against `db` and return a plain dict with items/total/page/page_size/total_pages.

    Caller is responsible for serializing `items` (they're still ORM rows).
    """
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    result = await db.execute(query.offset(params.offset).limit(params.page_size))
    items = result.scalars().all()

    total_pages = ceil(total / params.page_size) if total else 0

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": total_pages,
    }
