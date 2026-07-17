"""Comment request/response schemas (T-2061 comments, T-2062 inline annotations)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommentCreate(BaseModel):
    """New top-level comment, or a reply when parent_comment_id is set.
    Setting anchor_start/anchor_end turns it into an inline annotation
    anchored to that range of the document's text; omit both for a
    plain, doc-level comment."""

    content: str = Field(..., min_length=1)
    parent_comment_id: Optional[UUID] = None
    anchor_start: Optional[int] = Field(None, ge=0)
    anchor_end: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def _anchor_range_valid(self) -> "CommentCreate":
        # Mirrors the DB's ck_comments_anchor_range CHECK — fail fast client-side.
        if self.anchor_start is not None:
            if self.anchor_end is None or self.anchor_end < self.anchor_start:
                raise ValueError(
                    "anchor_end must be set and >= anchor_start when anchor_start is set"
                )
        return self


class CommentRead(BaseModel):
    """Comment as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    comment_id: UUID
    org_id: UUID
    doc_id: UUID
    user_id: Optional[UUID] = None
    parent_comment_id: Optional[UUID] = None
    content: str
    anchor_start: Optional[int] = None
    anchor_end: Optional[int] = None
    created_at: datetime
    updated_at: datetime
