from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/cart", tags=["cart"])


class CartItem(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1)
    product_name: str | None = None
    unit_price_cents: int | None = None


class CartResponse(BaseModel):
    id: UUID | None = None
    items: list[CartItem] = Field(default_factory=list)


class AddToCartRequest(BaseModel):
    variant_id: UUID
    quantity: int = Field(default=1, ge=1)


@router.get("", response_model=CartResponse)
async def get_cart() -> CartResponse:
    # TODO: Resolve session/user cart from PostgreSQL.
    return CartResponse(items=[])


@router.post("/items", response_model=CartResponse)
async def add_cart_item(body: AddToCartRequest) -> CartResponse:
    # TODO: Upsert cart_items; check inventory availability.
    _ = body
    return CartResponse(items=[])


@router.delete("/items/{variant_id}", response_model=CartResponse)
async def remove_cart_item(variant_id: UUID) -> CartResponse:
    # TODO: Remove line item from cart.
    _ = variant_id
    return CartResponse(items=[])
