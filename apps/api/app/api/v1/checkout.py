from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import resolve_session_token
from app.core.config import get_settings
from app.repositories import cart as cart_repo
from app.repositories import orders as orders_repo
from app.repositories.orders import InsufficientStockError
from app.services.payments import get_payment_provider, verify_stub_token

router = APIRouter(tags=["checkout"])


class CheckoutSessionRequest(BaseModel):
    email: EmailStr
    success_url: str | None = None
    cancel_url: str | None = None
    idempotency_key: str | None = None


class CheckoutSessionResponse(BaseModel):
    order_id: UUID
    status: str
    total_cents: int
    currency: str
    payment_provider: str
    checkout_session_id: str
    payment_url: str


@router.post("/checkout/session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    body: CheckoutSessionRequest,
    session_token: str = Depends(resolve_session_token),
) -> CheckoutSessionResponse:
    """Recalculate prices/availability, reserve stock, create payment session."""
    settings = get_settings()
    cart = cart_repo.get_or_create_cart(session_token)
    raw_items = cart_repo.list_cart_items(cart["id"])
    if not raw_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    snapshots: list[dict] = []
    for row in raw_items:
        snap = orders_repo.get_variant_snapshot(row["variant_id"])
        if snap is None:
            raise HTTPException(status_code=400, detail=f"Variant {row['variant_id']} no longer exists")
        qty = int(row["quantity"])
        available = int(snap["quantity_on_hand"]) - int(snap["quantity_reserved"])
        if available < qty:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Insufficient stock for {snap['product_name']} "
                    f"(requested {qty}, available {available})"
                ),
            )
        snapshots.append(
            {
                "variant_id": snap["variant_id"],
                "product_id": snap["product_id"],
                "sku": snap["sku"],
                "product_name": snap["product_name"],
                "unit_price_cents": int(snap["price_cents"]),
                "currency": snap["currency"],
                "quantity": qty,
            }
        )

    currency = snapshots[0]["currency"]
    provider = get_payment_provider()
    try:
        order = orders_repo.create_pending_order_with_reservation(
            cart_id=cart["id"],
            email=str(body.email),
            items=snapshots,
            currency=currency,
            payment_provider=provider.name,
            idempotency_key=body.idempotency_key,
        )
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        # Unique idempotency key collision → return existing if possible
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    success_url = body.success_url or (
        f"{settings.storefront_public_base.rstrip('/')}/account/orders?paid=1"
        f"&order_id={order['id']}"
    )
    cancel_url = body.cancel_url or (
        f"{settings.storefront_public_base.rstrip('/')}/checkout?cancelled=1"
    )

    session = provider.create_checkout_session(
        order_id=order["id"],
        email=str(body.email),
        amount_cents=int(order["total_cents"]),
        currency=currency,
        line_items=snapshots,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    orders_repo.set_checkout_session(
        order["id"], session.checkout_session_id, session.payment_ref
    )

    return CheckoutSessionResponse(
        order_id=order["id"],
        status=order["status"],
        total_cents=int(order["total_cents"]),
        currency=currency,
        payment_provider=session.provider,
        checkout_session_id=session.checkout_session_id,
        payment_url=session.payment_url,
    )


@router.get("/checkout/stub-pay", response_class=HTMLResponse)
async def stub_pay_page(
    order_id: UUID = Query(...),
    session_id: str = Query(...),
    token: str = Query(...),
    success_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Browser landing page for stub payments — confirms then completes."""
    if not verify_stub_token(order_id, session_id, token):
        raise HTTPException(status_code=403, detail="Invalid stub payment token")
    order = orders_repo.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("checkout_session_id") != session_id:
        raise HTTPException(status_code=400, detail="Session mismatch")

    settings = get_settings()
    redirect_to = success_url or (
        f"{settings.storefront_public_base.rstrip('/')}/account/orders?paid=1&order_id={order_id}"
    )
    complete_url = (
        f"{settings.api_public_base.rstrip('/')}/api/v1/checkout/stub-complete"
        f"?order_id={order_id}&session_id={session_id}&token={token}"
        f"&redirect={redirect_to}"
    )
    total = f"${order['total_cents'] / 100:.2f}"
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Stub checkout</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f1a15;color:#f4f6f5;display:grid;place-items:center;min-height:100vh;margin:0}}
.card{{border:1px solid #ffffff22;padding:2rem;max-width:28rem}}
a.btn{{display:inline-block;margin-top:1rem;background:#3d9b62;color:#0f1a15;padding:.6rem 1rem;text-decoration:none;border-radius:6px}}
</style></head>
<body><div class="card">
<h1>Stub payment</h1>
<p>Order <code>{order_id}</code></p>
<p>Total <strong>{total} {order['currency']}</strong></p>
<p>No real charge — demo mode.</p>
<a class="btn" href="{complete_url}">Pay now (stub)</a>
</div></body></html>"""
    return HTMLResponse(html)


@router.get("/checkout/stub-complete")
async def stub_complete(
    order_id: UUID = Query(...),
    session_id: str = Query(...),
    token: str = Query(...),
    redirect: str | None = Query(default=None),
):
    if not verify_stub_token(order_id, session_id, token):
        raise HTTPException(status_code=403, detail="Invalid stub payment token")
    order = orders_repo.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("checkout_session_id") != session_id:
        raise HTTPException(status_code=400, detail="Session mismatch")

    event_id = f"stub_complete_{session_id}"
    orders_repo.finalize_paid_order(
        order_id=order_id,
        provider="stub",
        event_id=event_id,
        event_type="payment.succeeded",
        payload={"order_id": str(order_id), "checkout_session_id": session_id},
        payment_ref=session_id,
    )

    settings = get_settings()
    target = redirect or (
        f"{settings.storefront_public_base.rstrip('/')}/account/orders?paid=1&order_id={order_id}"
    )
    return RedirectResponse(url=target, status_code=303)
