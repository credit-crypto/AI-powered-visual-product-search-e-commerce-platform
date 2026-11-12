"""Orders, inventory reservation, and payment event persistence (MongoDB)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pymongo import ReturnDocument

from app.db import collection, with_id


class InsufficientStockError(Exception):
    def __init__(self, variant_id: UUID, requested: int, available: int) -> None:
        self.variant_id = variant_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {variant_id}: requested {requested}, available {available}"
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_variant_snapshot(variant_id: UUID) -> dict[str, Any] | None:
    variant = collection("product_variants").find_one({"_id": variant_id})
    if not variant:
        return None
    product = collection("products").find_one({"_id": variant["product_id"]})
    inv = collection("inventory").find_one({"variant_id": variant_id})
    return {
        "variant_id": variant["_id"],
        "sku": variant.get("sku"),
        "price_cents": int(variant.get("price_cents") or 0),
        "currency": variant.get("currency") or "USD",
        "product_id": variant.get("product_id"),
        "product_name": product.get("name") if product else None,
        "quantity_on_hand": int(inv.get("quantity_on_hand") or 0) if inv else 0,
        "quantity_reserved": int(inv.get("quantity_reserved") or 0) if inv else 0,
    }


def create_pending_order_with_reservation(
    *,
    cart_id: UUID,
    email: str,
    items: list[dict[str, Any]],
    currency: str,
    payment_provider: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Atomically reserve inventory and create a pending order with line snapshots."""
    if not items:
        raise ValueError("cart is empty")

    total = sum(int(i["unit_price_cents"]) * int(i["quantity"]) for i in items)
    inventory = collection("inventory")

    # Reserve each line with a conditional update (offline-safe atomic ops).
    reserved_variant_ids: list[tuple[UUID, int]] = []
    try:
        for item in items:
            qty = int(item["quantity"])
            variant_id = item["variant_id"]
            updated = inventory.find_one_and_update(
                {
                    "variant_id": variant_id,
                    "$expr": {
                        "$gte": [
                            {"$subtract": ["$quantity_on_hand", "$quantity_reserved"]},
                            qty,
                        ]
                    },
                },
                {
                    "$inc": {"quantity_reserved": qty},
                    "$set": {"updated_at": _now()},
                },
                return_document=ReturnDocument.AFTER,
            )
            if updated is None:
                inv = inventory.find_one({"variant_id": variant_id})
                available = 0
                if inv:
                    available = int(inv.get("quantity_on_hand") or 0) - int(
                        inv.get("quantity_reserved") or 0
                    )
                raise InsufficientStockError(variant_id, qty, available)
            reserved_variant_ids.append((variant_id, qty))
    except Exception:
        # Roll back any reservations already taken in this attempt.
        for variant_id, qty in reserved_variant_ids:
            inventory.update_one(
                {"variant_id": variant_id},
                {
                    "$inc": {"quantity_reserved": -qty},
                    "$set": {"updated_at": _now()},
                },
            )
        raise

    order_id = uuid4()
    now = _now()
    order_doc = {
        "_id": order_id,
        "email": email,
        "cart_id": cart_id,
        "status": "pending",
        "total_cents": total,
        "currency": currency,
        "payment_provider": payment_provider,
        "payment_ref": None,
        "checkout_session_id": None,
        "reserved": True,
        "idempotency_key": idempotency_key,
        "created_at": now,
        "updated_at": now,
    }
    collection("orders").insert_one(order_doc)

    order_items = collection("order_items")
    for item in items:
        order_items.insert_one(
            {
                "_id": uuid4(),
                "order_id": order_id,
                "variant_id": item["variant_id"],
                "product_id": item["product_id"],
                "quantity": int(item["quantity"]),
                "unit_price_cents": int(item["unit_price_cents"]),
                "sku": item.get("sku"),
                "product_name": item.get("product_name"),
                "currency": item.get("currency") or currency,
                "created_at": now,
            }
        )

    return {
        "id": order_id,
        "email": email,
        "status": "pending",
        "total_cents": total,
        "currency": currency,
        "cart_id": cart_id,
        "payment_provider": payment_provider,
        "checkout_session_id": None,
        "created_at": now,
    }


def set_checkout_session(
    order_id: UUID, checkout_session_id: str, payment_ref: str | None = None
) -> None:
    updates: dict[str, Any] = {
        "checkout_session_id": checkout_session_id,
        "updated_at": _now(),
    }
    if payment_ref is not None:
        updates["payment_ref"] = payment_ref
    collection("orders").update_one({"_id": order_id}, {"$set": updates})


def get_order(order_id: UUID) -> dict[str, Any] | None:
    return with_id(collection("orders").find_one({"_id": order_id}))


def get_order_by_checkout_session(checkout_session_id: str) -> dict[str, Any] | None:
    return with_id(
        collection("orders").find_one({"checkout_session_id": checkout_session_id})
    )


def list_order_items(order_id: UUID) -> list[dict[str, Any]]:
    cursor = collection("order_items").find({"order_id": order_id}).sort("_id", 1)
    return [
        {
            "id": row["_id"],
            "variant_id": row["variant_id"],
            "product_id": row.get("product_id"),
            "quantity": int(row.get("quantity") or 0),
            "unit_price_cents": int(row.get("unit_price_cents") or 0),
            "sku": row.get("sku"),
            "product_name": row.get("product_name"),
            "currency": row.get("currency"),
        }
        for row in cursor
    ]


def list_orders_by_email(email: str, limit: int = 50) -> list[dict[str, Any]]:
    cursor = (
        collection("orders")
        .find({"email": {"$regex": f"^{email}$", "$options": "i"}})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [with_id(row) or row for row in cursor]


def payment_event_exists(provider: str, event_id: str) -> bool:
    return (
        collection("payment_events").find_one({"provider": provider, "event_id": event_id})
        is not None
    )


def finalize_paid_order(
    *,
    order_id: UUID,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
    payment_ref: str | None = None,
) -> dict[str, Any]:
    """Idempotently mark order paid, decrement stock, release reservation, convert cart."""
    events = collection("payment_events")
    orders = collection("orders")
    inventory = collection("inventory")

    if events.find_one({"provider": provider, "event_id": event_id}):
        order = orders.find_one({"_id": order_id})
        if order is None:
            raise LookupError("order not found")
        return with_id(order) or order

    order = orders.find_one({"_id": order_id})
    if order is None:
        raise LookupError("order not found")

    if order.get("status") == "paid":
        try:
            events.insert_one(
                {
                    "_id": uuid4(),
                    "provider": provider,
                    "event_id": event_id,
                    "event_type": event_type,
                    "order_id": order_id,
                    "payload": payload,
                    "created_at": _now(),
                }
            )
        except Exception:
            pass
        return with_id(order) or order

    if order.get("status") not in {"pending", "paid"}:
        raise ValueError(f"order status {order['status']} cannot be marked paid")

    lines = list(collection("order_items").find({"order_id": order_id}))
    if order.get("reserved"):
        for line in lines:
            qty = int(line["quantity"])
            inv = inventory.find_one({"variant_id": line["variant_id"]})
            if not inv:
                continue
            inventory.update_one(
                {"_id": inv["_id"]},
                {
                    "$set": {
                        "quantity_on_hand": max(int(inv.get("quantity_on_hand") or 0) - qty, 0),
                        "quantity_reserved": max(int(inv.get("quantity_reserved") or 0) - qty, 0),
                        "updated_at": _now(),
                    }
                },
            )

    updates: dict[str, Any] = {
        "status": "paid",
        "reserved": False,
        "updated_at": _now(),
    }
    if payment_ref is not None:
        updates["payment_ref"] = payment_ref
    orders.update_one({"_id": order_id}, {"$set": updates})

    if order.get("cart_id"):
        collection("cart_items").delete_many({"cart_id": order["cart_id"]})
        collection("carts").update_one(
            {"_id": order["cart_id"]},
            {"$set": {"status": "converted", "updated_at": _now()}},
        )

    try:
        events.insert_one(
            {
                "_id": uuid4(),
                "provider": provider,
                "event_id": event_id,
                "event_type": event_type,
                "order_id": order_id,
                "payload": payload,
                "created_at": _now(),
            }
        )
    except Exception:
        # Unique index race — treat as idempotent success.
        pass

    updated = orders.find_one({"_id": order_id})
    return with_id(updated) or updated or {}


def release_reservation(order_id: UUID) -> None:
    """Release reserved stock for a cancelled/expired pending order."""
    orders = collection("orders")
    order = orders.find_one({"_id": order_id})
    if not order or not order.get("reserved") or order.get("status") != "pending":
        return

    inventory = collection("inventory")
    for line in collection("order_items").find({"order_id": order_id}):
        qty = int(line["quantity"])
        inv = inventory.find_one({"variant_id": line["variant_id"]})
        if not inv:
            continue
        inventory.update_one(
            {"_id": inv["_id"]},
            {
                "$set": {
                    "quantity_reserved": max(int(inv.get("quantity_reserved") or 0) - qty, 0),
                    "updated_at": _now(),
                }
            },
        )

    orders.update_one(
        {"_id": order_id},
        {"$set": {"status": "cancelled", "reserved": False, "updated_at": _now()}},
    )
