from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/orders", tags=["orders"])


class CheckoutRequest(BaseModel):
    cart_id: UUID | None = None
    email: str | None = None
    # TODO: shipping address, payment method / Stripe session fields


class CheckoutResponse(BaseModel):
    order_id: UUID
    status: str
    payment_url: str | None = None


class OrderSummary(BaseModel):
    id: UUID
    status: str
    total_cents: int
    currency: str = "USD"


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(body: CheckoutRequest) -> CheckoutResponse:
    # TODO: Reserve stock transactionally; create order; start Stripe Checkout.
    raise HTTPException(
        status_code=501,
        detail=f"checkout not implemented yet (cart_id={body.cart_id})",
    )


@router.get("/{order_id}", response_model=OrderSummary)
async def get_order(order_id: UUID) -> OrderSummary:
    # TODO: Load order + items for the authenticated customer.
    raise HTTPException(status_code=404, detail=f"Order {order_id} not found (stub)")


@router.post("/webhooks/payment")
async def payment_webhook() -> dict[str, str]:
    # TODO: Verify PSP signature; idempotent order status update.
    return {"status": "ignored", "message": "webhook stub"}
