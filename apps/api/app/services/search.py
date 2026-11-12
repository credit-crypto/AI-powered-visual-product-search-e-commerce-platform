"""Vector similarity search over MongoDB embeddings (offline cosine)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.repositories import catalogue as catalogue_repo
from app.schemas.search import VisualSearchResultItem
from app.services.encoder import get_encoder


class SearchService(ABC):
    @abstractmethod
    async def similar_products(
        self,
        embedding: list[float],
        limit: int = 20,
        category_id: UUID | None = None,
    ) -> list[VisualSearchResultItem]:
        """Return products nearest to the query embedding."""


class MongoCosineSearchService(SearchService):
    """In-process cosine search over L2-normalized float arrays in MongoDB.

    No Atlas Vector Search required for local/offline demos. Atlas can be added
    later behind the same interface if the catalogue grows.
    """

    async def similar_products(
        self,
        embedding: list[float],
        limit: int = 20,
        category_id: UUID | None = None,
    ) -> list[VisualSearchResultItem]:
        encoder = get_encoder()
        rows = catalogue_repo.search_similar(
            embedding=embedding,
            limit=limit,
            category_id=category_id,
            model_name=encoder.model_name,
        )
        return [
            VisualSearchResultItem(
                product_id=row["product_id"],
                score=float(row["score"]),
                image_id=row["image_id"],
                name=row["name"],
                slug=row.get("slug"),
                thumbnail_url=row["thumbnail_url"],
                price_cents=int(row["price_cents"]) if row.get("price_cents") is not None else None,
                currency=row.get("currency"),
            )
            for row in rows
        ]


_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = MongoCosineSearchService()
    return _search_service
