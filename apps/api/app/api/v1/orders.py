from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.repositories import orders as orders_repo

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItem(BaseModel):
    variant_id: UUID
    product_id: UUID | None = None
    sku: str | None = None
    product_name: str | None = None
    quantity: int
    unit_price_cents: int
    currency: str = "USD"
    line_total_cents: int | None = None


class OrderSummary(BaseModel):
    id: UUID
    status: str
    total_cents: int
    currency: str = "USD"
    email: str | None = None
    created_at: str | None = None
    items: list[OrderItem] = Field(default_factory=list)


@router.get("", response_model=list[OrderSummary])
async def list_orders(email: EmailStr = Query(..., description="Guest email used at checkout")) -> list[OrderSummary]:
    """Light account view: list orders by checkout email (no auth yet)."""
    rows = orders_repo.list_orders_by_email(str(email))
    return [
        OrderSummary(
            id=row["id"],
            status=row["status"],
            total_cents=int(row["total_cents"]),
            currency=row.get("currency") or "USD",
            email=row.get("email"),
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )
        for row in rows
    ]


@router.get("/{order_id}", response_model=OrderSummary)
async def get_order(order_id: UUID) -> OrderSummary:
    row = orders_repo.get_order(order_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    items = []
    for item in orders_repo.list_order_items(order_id):
        qty = int(item["quantity"])
        unit = int(item["unit_price_cents"])
        items.append(
            OrderItem(
                variant_id=item["variant_id"],
                product_id=item.get("product_id"),
                sku=item.get("sku"),
                product_name=item.get("product_name"),
                quantity=qty,
                unit_price_cents=unit,
                currency=item.get("currency") or "USD",
                line_total_cents=qty * unit,
            )
        )
    return OrderSummary(
        id=row["id"],
        status=row["status"],
        total_cents=int(row["total_cents"]),
        currency=row.get("currency") or "USD",
        email=row.get("email"),
        created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        items=items,
    )
