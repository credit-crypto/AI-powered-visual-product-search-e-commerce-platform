"""Vector similarity search interface over pgvector.

Next milestone: cosine nearest-neighbour query against image_embeddings
(HNSW), group by product_id, apply category filters / rerank.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.schemas.search import VisualSearchResultItem


class SearchService(ABC):
    @abstractmethod
    async def similar_products(
        self,
        embedding: list[float],
        limit: int = 20,
        category_id: UUID | None = None,
    ) -> list[VisualSearchResultItem]:
        """Return products nearest to the query embedding."""


class StubSearchService(SearchService):
    async def similar_products(
        self,
        embedding: list[float],
        limit: int = 20,
        category_id: UUID | None = None,
    ) -> list[VisualSearchResultItem]:
        # TODO: SELECT ... ORDER BY embedding <=> :query LIMIT :limit using pgvector.
        _ = (embedding, limit, category_id)
        return []


_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = StubSearchService()
    return _search_service
