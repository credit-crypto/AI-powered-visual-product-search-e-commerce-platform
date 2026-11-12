"""Guest/session cart persistence (MongoDB)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.db import collection, with_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_cart(session_token: str) -> dict[str, Any]:
    carts = collection("carts")
    row = carts.find_one(
        {"session_token": session_token, "status": "open"},
        sort=[("created_at", -1)],
    )
    if row:
        return with_id(row) or row

    cart_id = uuid4()
    now = _now()
    doc = {
        "_id": cart_id,
        "session_token": session_token,
        "user_id": None,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    carts.insert_one(doc)
    return with_id(doc) or doc


def get_cart_by_id(cart_id: UUID) -> dict[str, Any] | None:
    return with_id(collection("carts").find_one({"_id": cart_id}))


def list_cart_items(cart_id: UUID) -> list[dict[str, Any]]:
    items = list(collection("cart_items").find({"cart_id": cart_id}).sort("_id", 1))
    out: list[dict[str, Any]] = []
    for item in items:
        variant = collection("product_variants").find_one({"_id": item["variant_id"]})
        if not variant:
            continue
        product = collection("products").find_one({"_id": variant["product_id"]})
        inv = collection("inventory").find_one({"variant_id": variant["_id"]})
        thumb = None
        if product:
            img = collection("product_images").find_one(
                {"product_id": product["_id"]},
                sort=[("is_primary", -1), ("position", 1)],
            )
            thumb = img.get("url") if img else None
        available = 0
        if inv:
            available = int(inv.get("quantity_on_hand") or 0) - int(
                inv.get("quantity_reserved") or 0
            )
        out.append(
            {
                "cart_item_id": item["_id"],
                "variant_id": item["variant_id"],
                "quantity": int(item.get("quantity") or 0),
                "sku": variant.get("sku"),
                "unit_price_cents": int(variant.get("price_cents") or 0),
                "currency": variant.get("currency") or "USD",
                "product_id": variant.get("product_id"),
                "product_name": product.get("name") if product else None,
                "product_slug": product.get("slug") if product else None,
                "thumbnail_url": thumb,
                "available_qty": available,
            }
        )
    return out


def upsert_cart_item(cart_id: UUID, variant_id: UUID, quantity: int) -> None:
    if quantity < 1:
        raise ValueError("quantity must be >= 1")
    if collection("product_variants").find_one({"_id": variant_id}) is None:
        raise LookupError("variant not found")
    collection("cart_items").update_one(
        {"cart_id": cart_id, "variant_id": variant_id},
        {
            "$set": {"quantity": quantity, "updated_at": _now()},
            "$setOnInsert": {"_id": uuid4(), "created_at": _now()},
        },
        upsert=True,
    )
    collection("carts").update_one(
        {"_id": cart_id},
        {"$set": {"updated_at": _now()}},
    )


def set_cart_item_quantity(cart_id: UUID, variant_id: UUID, quantity: int) -> None:
    if quantity < 1:
        delete_cart_item(cart_id, variant_id)
        return
    result = collection("cart_items").update_one(
        {"cart_id": cart_id, "variant_id": variant_id},
        {"$set": {"quantity": quantity, "updated_at": _now()}},
    )
    if result.matched_count == 0:
        raise LookupError("cart item not found")
    collection("carts").update_one(
        {"_id": cart_id},
        {"$set": {"updated_at": _now()}},
    )


def delete_cart_item(cart_id: UUID, variant_id: UUID) -> None:
    collection("cart_items").delete_one({"cart_id": cart_id, "variant_id": variant_id})
    collection("carts").update_one(
        {"_id": cart_id},
        {"$set": {"updated_at": _now()}},
    )


def clear_cart_items(cart_id: UUID) -> None:
    collection("cart_items").delete_many({"cart_id": cart_id})
    collection("carts").update_one(
        {"_id": cart_id},
        {"$set": {"updated_at": _now()}},
    )


def mark_cart_converted(cart_id: UUID) -> None:
    collection("carts").update_one(
        {"_id": cart_id},
        {"$set": {"status": "converted", "updated_at": _now()}},
    )


def new_session_token() -> str:
    return uuid4().hex
