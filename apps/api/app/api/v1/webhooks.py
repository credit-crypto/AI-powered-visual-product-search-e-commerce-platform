from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from app.repositories import orders as orders_repo
from app.services.payments import get_payment_provider

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payments")
async def payments_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    """Idempotent payment webhook (Stripe or stub JSON)."""
    payload = await request.body()
    provider = get_payment_provider()
    try:
        event = provider.verify_and_parse_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    event_type = event["event_type"]
    # Only finalize on success-like events
    success_types = {
        "payment.succeeded",
        "checkout.session.completed",
        "payment_intent.succeeded",
    }
    if event_type not in success_types:
        return {"status": "ignored", "event_type": event_type}

    order_id_raw = event.get("order_id")
    checkout_session_id = event.get("checkout_session_id")
    order = None
    if order_id_raw:
        try:
            order = orders_repo.get_order(UUID(str(order_id_raw)))
        except Exception:
            order = None
    if order is None and checkout_session_id:
        order = orders_repo.get_order_by_checkout_session(str(checkout_session_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found for webhook")

    updated = orders_repo.finalize_paid_order(
        order_id=order["id"],
        provider=provider.name,
        event_id=str(event["event_id"]),
        event_type=event_type,
        payload=event.get("raw") or event,
        payment_ref=event.get("payment_ref"),
    )
    return {
        "status": "ok",
        "order_id": str(updated["id"]),
        "order_status": updated["status"],
    }
