"""Payment providers: Stripe Checkout (real) or local stub for demos."""

from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CheckoutSessionResult:
    provider: str
    checkout_session_id: str
    payment_url: str
    payment_ref: str | None = None


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_checkout_session(
        self,
        *,
        order_id: UUID,
        email: str,
        amount_cents: int,
        currency: str,
        line_items: list[dict[str, Any]],
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        ...

    @abstractmethod
    def verify_and_parse_webhook(
        self, payload: bytes, signature_header: str | None
    ) -> dict[str, Any]:
        """Return normalized event: {event_id, event_type, checkout_session_id, payment_ref, raw}."""


class StubPaymentProvider(PaymentProvider):
    """No Stripe keys required. Returns a local URL that completes payment via API."""

    name = "stub"

    def create_checkout_session(
        self,
        *,
        order_id: UUID,
        email: str,
        amount_cents: int,
        currency: str,
        line_items: list[dict[str, Any]],
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        settings = get_settings()
        session_id = f"stub_cs_{uuid4().hex}"
        token = _stub_token(order_id, session_id)
        # Storefront can redirect here; the page calls the complete endpoint.
        base = settings.api_public_base.rstrip("/")
        payment_url = (
            f"{base}/api/v1/checkout/stub-pay"
            f"?order_id={order_id}&session_id={session_id}&token={token}"
            f"&success_url={_url_quote(success_url)}"
        )
        _ = (email, amount_cents, currency, line_items, cancel_url)
        return CheckoutSessionResult(
            provider=self.name,
            checkout_session_id=session_id,
            payment_url=payment_url,
            payment_ref=session_id,
        )

    def verify_and_parse_webhook(
        self, payload: bytes, signature_header: str | None
    ) -> dict[str, Any]:
        import json

        data = json.loads(payload.decode("utf-8"))
        event_id = data.get("id") or data.get("event_id") or f"stub_evt_{uuid4().hex}"
        return {
            "event_id": str(event_id),
            "event_type": data.get("type") or data.get("event_type") or "payment.succeeded",
            "checkout_session_id": data.get("checkout_session_id")
            or data.get("data", {}).get("object", {}).get("id"),
            "payment_ref": data.get("payment_ref"),
            "order_id": data.get("order_id"),
            "raw": data,
        }


class StripePaymentProvider(PaymentProvider):
    name = "stripe"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise RuntimeError(
                "STRIPE_SECRET_KEY is required when PAYMENT_PROVIDER=stripe"
            )
        try:
            import stripe
        except ImportError as exc:
            raise RuntimeError(
                "stripe package missing; pip install stripe or use PAYMENT_PROVIDER=stub"
            ) from exc
        self._stripe = stripe
        stripe.api_key = settings.stripe_secret_key
        self._webhook_secret = settings.stripe_webhook_secret

    def create_checkout_session(
        self,
        *,
        order_id: UUID,
        email: str,
        amount_cents: int,
        currency: str,
        line_items: list[dict[str, Any]],
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        stripe_items = []
        for item in line_items:
            stripe_items.append(
                {
                    "price_data": {
                        "currency": (item.get("currency") or currency).lower(),
                        "unit_amount": int(item["unit_price_cents"]),
                        "product_data": {
                            "name": item.get("product_name") or item.get("sku") or "Item",
                        },
                    },
                    "quantity": int(item["quantity"]),
                }
            )
        if not stripe_items:
            # Fallback single line for total
            stripe_items = [
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_cents,
                        "product_data": {"name": f"Order {order_id}"},
                    },
                    "quantity": 1,
                }
            ]

        session = self._stripe.checkout.Session.create(
            mode="payment",
            customer_email=email,
            line_items=stripe_items,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order_id),
            metadata={"order_id": str(order_id)},
        )
        return CheckoutSessionResult(
            provider=self.name,
            checkout_session_id=session.id,
            payment_url=session.url,
            payment_ref=session.payment_intent,
        )

    def verify_and_parse_webhook(
        self, payload: bytes, signature_header: str | None
    ) -> dict[str, Any]:
        if not self._webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET required for Stripe webhooks")
        if not signature_header:
            raise ValueError("Missing Stripe-Signature header")
        event = self._stripe.Webhook.construct_event(
            payload, signature_header, self._webhook_secret
        )
        obj = event["data"]["object"]
        return {
            "event_id": event["id"],
            "event_type": event["type"],
            "checkout_session_id": obj.get("id") if event["type"].startswith("checkout.session") else obj.get("checkout_session"),
            "payment_ref": obj.get("payment_intent"),
            "order_id": (obj.get("metadata") or {}).get("order_id")
            or obj.get("client_reference_id"),
            "raw": event,
        }


def _stub_token(order_id: UUID, session_id: str) -> str:
    settings = get_settings()
    secret = settings.stub_payment_secret.encode("utf-8")
    msg = f"{order_id}:{session_id}".encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def verify_stub_token(order_id: UUID, session_id: str, token: str) -> bool:
    expected = _stub_token(order_id, session_id)
    return hmac.compare_digest(expected, token)


def _url_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


@lru_cache
def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    provider = (settings.payment_provider or "stub").strip().lower()
    if provider == "stripe":
        return StripePaymentProvider()
    if provider in {"stub", "test", "local"}:
        return StubPaymentProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER={provider!r}")
