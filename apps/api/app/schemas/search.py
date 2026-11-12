from uuid import UUID

from pydantic import BaseModel, Field


class VisualSearchResultItem(BaseModel):
    product_id: UUID
    score: float
    image_id: UUID | None = None
    name: str | None = None
    thumbnail_url: str | None = None


class VisualSearchResponse(BaseModel):
    results: list[VisualSearchResultItem] = Field(default_factory=list)
    query_ms: int | None = None
    message: str | None = None


class SearchFeedbackRequest(BaseModel):
    search_event_id: UUID | None = None
    product_id: UUID
    relevant: bool
    notes: str | None = None
