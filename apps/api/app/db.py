"""MongoDB helpers (API + Celery worker). Offline MVP — no Atlas required."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.config import get_settings


@lru_cache
def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(
        settings.mongodb_uri,
        uuidRepresentation="standard",
    )


def get_db() -> Database:
    settings = get_settings()
    return get_client()[settings.mongodb_db]


def collection(name: str) -> Collection:
    return get_db()[name]


def reset_db_client() -> None:
    get_client.cache_clear()


def ensure_indexes() -> None:
    """Create indexes needed for catalogue, carts, orders, and embedding lookups."""
    db = get_db()

    db.categories.create_index("slug", unique=True)

    db.products.create_index("slug", unique=True)
    db.products.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    db.products.create_index("name")

    db.product_variants.create_index("product_id")
    db.product_variants.create_index("sku", unique=True)
    db.product_variants.create_index(
        [("product_id", ASCENDING), ("is_default", ASCENDING)],
    )

    db.inventory.create_index("variant_id", unique=True)

    db.product_images.create_index("product_id")
    db.product_images.create_index([("product_id", ASCENDING), ("status", ASCENDING)])

    db.image_embeddings.create_index("product_image_id", unique=True)
    db.image_embeddings.create_index("product_id")
    db.image_embeddings.create_index(
        [("model_name", ASCENDING), ("product_id", ASCENDING)],
    )

    db.carts.create_index(
        [("session_token", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
    )
    db.cart_items.create_index(
        [("cart_id", ASCENDING), ("variant_id", ASCENDING)],
        unique=True,
    )

    db.orders.create_index("email")
    db.orders.create_index("checkout_session_id")
    db.orders.create_index([("created_at", DESCENDING)])

    db.order_items.create_index("order_id")

    db.payment_events.create_index(
        [("provider", ASCENDING), ("event_id", ASCENDING)],
        unique=True,
    )

    db.search_events.create_index([("created_at", DESCENDING)])


def with_id(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Map Mongo `_id` → API `id`."""
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = out.pop("_id")
    return out


def with_ids(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [with_id(d) or d for d in docs]
