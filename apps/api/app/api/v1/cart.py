from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import resolve_session_token
from app.repositories import cart as cart_repo

router = APIRouter(prefix="/cart", tags=["cart"])


class CartItem(BaseModel):
    cart_item_id: UUID | None = None
    variant_id: UUID
    product_id: UUID | None = None
    quantity: int = Field(ge=1)
    product_name: str | None = None
    product_slug: str | None = None
    sku: str | None = None
    unit_price_cents: int | None = None
    currency: str = "USD"
    thumbnail_url: str | None = None
    available_qty: int | None = None
    line_total_cents: int | None = None


class CartResponse(BaseModel):
    id: UUID
    session_token: str
    status: str = "open"
    items: list[CartItem] = Field(default_factory=list)
    subtotal_cents: int = 0
    currency: str = "USD"


class AddToCartRequest(BaseModel):
    variant_id: UUID
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=0)


def _serialize_cart(cart: dict, session_token: str) -> CartResponse:
    items_raw = cart_repo.list_cart_items(cart["id"])
    items: list[CartItem] = []
    subtotal = 0
    currency = "USD"
    for row in items_raw:
        unit = int(row["unit_price_cents"] or 0)
        qty = int(row["quantity"])
        line = unit * qty
        subtotal += line
        currency = row.get("currency") or currency
        items.append(
            CartItem(
                cart_item_id=row["cart_item_id"],
                variant_id=row["variant_id"],
                product_id=row.get("product_id"),
                quantity=qty,
                product_name=row.get("product_name"),
                product_slug=row.get("product_slug"),
                sku=row.get("sku"),
                unit_price_cents=unit,
                currency=row.get("currency") or "USD",
                thumbnail_url=row.get("thumbnail_url"),
                available_qty=int(row["available_qty"]) if row.get("available_qty") is not None else None,
                line_total_cents=line,
            )
        )
    return CartResponse(
        id=cart["id"],
        session_token=session_token,
        status=cart.get("status") or "open",
        items=items,
        subtotal_cents=subtotal,
        currency=currency,
    )


@router.get("", response_model=CartResponse)
async def get_cart(session_token: str = Depends(resolve_session_token)) -> CartResponse:
    cart = cart_repo.get_or_create_cart(session_token)
    return _serialize_cart(cart, session_token)


@router.post("/items", response_model=CartResponse)
async def add_cart_item(
    body: AddToCartRequest,
    session_token: str = Depends(resolve_session_token),
) -> CartResponse:
    cart = cart_repo.get_or_create_cart(session_token)
    # If item exists, add quantities
    existing = {row["variant_id"]: row for row in cart_repo.list_cart_items(cart["id"])}
    new_qty = body.quantity
    if body.variant_id in existing:
        new_qty = int(existing[body.variant_id]["quantity"]) + body.quantity
    try:
        cart_repo.upsert_cart_item(cart["id"], body.variant_id, new_qty)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cart = cart_repo.get_or_create_cart(session_token)
    return _serialize_cart(cart, session_token)


@router.patch("/items/{variant_id}", response_model=CartResponse)
async def patch_cart_item(
    variant_id: UUID,
    body: UpdateCartItemRequest,
    session_token: str = Depends(resolve_session_token),
) -> CartResponse:
    cart = cart_repo.get_or_create_cart(session_token)
    try:
        cart_repo.set_cart_item_quantity(cart["id"], variant_id, body.quantity)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cart = cart_repo.get_or_create_cart(session_token)
    return _serialize_cart(cart, session_token)


@router.delete("/items/{variant_id}", response_model=CartResponse)
async def remove_cart_item(
    variant_id: UUID,
    session_token: str = Depends(resolve_session_token),
) -> CartResponse:
    cart = cart_repo.get_or_create_cart(session_token)
    cart_repo.delete_cart_item(cart["id"], variant_id)
    cart = cart_repo.get_or_create_cart(session_token)
    return _serialize_cart(cart, session_token)
