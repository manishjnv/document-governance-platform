"""Search and search history schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchFilters(BaseModel):
    """Search filter parameters (also used in saved_searches.filters JSONB)."""

    document_type: Optional[str] = Field(None, description="Document type filter")
    date_from: Optional[str] = Field(None, description="ISO8601 date string, inclusive")
    date_to: Optional[str] = Field(None, description="ISO8601 date string, inclusive")


class SearchHistoryCreate(BaseModel):
    """Create a search history entry (auto-called after every search)."""

    query: str = Field(..., min_length=1, max_length=500)
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchHistoryRead(BaseModel):
    """Search history entry as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    history_id: UUID
    query: str
    filters: dict[str, Any]
    created_at: datetime


class SavedSearchCreate(BaseModel):
    """Create a saved search."""

    name: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1, max_length=500)
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SavedSearchUpdate(BaseModel):
    """Update a saved search."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    query: Optional[str] = Field(None, min_length=1, max_length=500)
    filters: Optional[SearchFilters] = None


class SavedSearchRead(BaseModel):
    """Saved search as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    saved_id: UUID
    name: str
    query: str
    filters: dict[str, Any]
    created_at: datetime


class SearchResultItem(BaseModel):
    """One search result (part of SearchResponse)."""

    doc_id: str
    filename: str
    document_type: Optional[str] = None
    rank: float = Field(..., ge=0.0, le=1.0, description="Relevance score 0–1")
    snippet: str = Field(..., description="Truncated matching text excerpt")
    created_at: str = Field(..., description="ISO8601 datetime string")


class SearchResponse(BaseModel):
    """Response from /api/v1/search endpoint."""

    query: str
    total: int = Field(..., ge=0)
    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=100)
    results: list[SearchResultItem] = Field(default_factory=list)
