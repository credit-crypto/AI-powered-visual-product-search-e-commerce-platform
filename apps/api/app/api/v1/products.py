from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.repositories import catalogue as catalogue_repo

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
    rows = catalogue_repo.list_products(
        q=q, category_id=category_id, limit=limit, offset=offset
    )
    return [
        ProductSummary(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            price_cents=int(row["price_cents"] or 0),
            currency=row.get("currency") or "USD",
            thumbnail_url=row.get("thumbnail_url"),
        )
        for row in rows
    ]


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: UUID) -> ProductDetail:
    row = catalogue_repo.get_product(product_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return ProductDetail(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        description=row.get("description"),
        category_id=row.get("category_id"),
        price_cents=int(row.get("price_cents") or 0),
        currency=row.get("currency") or "USD",
        thumbnail_url=row.get("thumbnail_url"),
        image_urls=[row["thumbnail_url"]] if row.get("thumbnail_url") else [],
    )
