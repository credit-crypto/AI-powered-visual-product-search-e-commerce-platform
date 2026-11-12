from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/products", tags=["products"])


class ProductSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    price_cents: int
    currency: str = "USD"
    thumbnail_url: str | None = None


class ProductDetail(ProductSummary):
    description: str | None = None
    category_id: UUID | None = None
    image_urls: list[str] = Field(default_factory=list)


@router.get("", response_model=list[ProductSummary])
async def list_products(
    q: str | None = Query(default=None, description="Text search query"),
    category_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ProductSummary]:
    # TODO: Query products table with optional category / text filters.
    _ = (q, category_id, limit, offset)
    return []


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: UUID) -> ProductDetail:
    # TODO: Load product, variants, and images from PostgreSQL.
    raise HTTPException(status_code=404, detail=f"Product {product_id} not found (stub)")
