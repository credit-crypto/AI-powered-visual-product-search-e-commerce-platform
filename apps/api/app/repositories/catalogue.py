"""Catalogue + embedding persistence (MongoDB)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import numpy as np

from app.db import collection, with_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_product(
    *,
    name: str,
    slug: str,
    description: str | None,
    category_id: UUID | None,
    price_cents: int,
    currency: str = "USD",
    status: str = "active",
    sku: str | None = None,
    stock_qty: int = 25,
) -> dict[str, Any]:
    product_id = uuid4()
    variant_id = uuid4()
    variant_sku = (sku or "").strip() or f"{slug}-default"
    qty = max(0, int(stock_qty))
    now = _now()

    collection("products").insert_one(
        {
            "_id": product_id,
            "category_id": category_id,
            "name": name,
            "slug": slug,
            "description": description,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
    )
    collection("product_variants").insert_one(
        {
            "_id": variant_id,
            "product_id": product_id,
            "sku": variant_sku,
            "name": "Default",
            "price_cents": price_cents,
            "currency": currency,
            "is_default": True,
            "created_at": now,
        }
    )
    collection("inventory").insert_one(
        {
            "_id": uuid4(),
            "variant_id": variant_id,
            "quantity_on_hand": qty,
            "quantity_reserved": 0,
            "updated_at": now,
        }
    )
    return {
        "id": product_id,
        "name": name,
        "slug": slug,
        "status": status,
        "variant_id": variant_id,
        "sku": variant_sku,
        "stock_qty": qty,
    }


def _default_variant(product_id: UUID) -> dict[str, Any] | None:
    return collection("product_variants").find_one(
        {"product_id": product_id, "is_default": True}
    )


def _thumbnail_url(product_id: UUID) -> str | None:
    img = collection("product_images").find_one(
        {"product_id": product_id},
        sort=[("is_primary", -1), ("position", 1), ("created_at", 1)],
    )
    return img.get("url") if img else None


def _enrich_product(product: dict[str, Any]) -> dict[str, Any]:
    variant = _default_variant(product["_id"])
    out = with_id(product) or {}
    if variant:
        out["default_variant_id"] = variant["_id"]
        out["default_sku"] = variant.get("sku")
        out["price_cents"] = int(variant.get("price_cents") or 0)
        out["currency"] = variant.get("currency") or "USD"
    else:
        out["default_variant_id"] = None
        out["default_sku"] = None
        out["price_cents"] = 0
        out["currency"] = "USD"
    out["thumbnail_url"] = _thumbnail_url(product["_id"])
    return out


def get_product(product_id: UUID) -> dict[str, Any] | None:
    product = collection("products").find_one({"_id": product_id})
    if not product:
        return None
    return _enrich_product(product)


def get_product_by_slug(slug: str) -> dict[str, Any] | None:
    product = collection("products").find_one({"slug": slug})
    if not product:
        return None
    return _enrich_product(product)


def list_products(
    *,
    q: str | None = None,
    category_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    filt: dict[str, Any] = {"status": "active"}
    if category_id:
        filt["category_id"] = category_id
    if q:
        filt["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    cursor = (
        collection("products")
        .find(filt)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [_enrich_product(doc) for doc in cursor]


def insert_product_image(
    *,
    product_id: UUID,
    storage_key: str,
    url: str,
    width: int | None,
    height: int | None,
    position: int = 0,
    is_primary: bool = False,
) -> dict[str, Any]:
    image_id = uuid4()
    now = _now()
    doc = {
        "_id": image_id,
        "product_id": product_id,
        "storage_key": storage_key,
        "url": url,
        "position": position,
        "is_primary": is_primary,
        "width": width,
        "height": height,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    collection("product_images").insert_one(doc)
    return {
        "id": image_id,
        "product_id": product_id,
        "storage_key": storage_key,
        "url": url,
        "status": "pending",
    }


def get_product_image(image_id: UUID) -> dict[str, Any] | None:
    return with_id(collection("product_images").find_one({"_id": image_id}))


def list_product_image_ids(product_id: UUID) -> list[UUID]:
    cursor = (
        collection("product_images")
        .find({"product_id": product_id}, {"_id": 1})
        .sort([("position", 1), ("created_at", 1)])
    )
    return [row["_id"] for row in cursor]


def count_product_images(product_id: UUID) -> int:
    return collection("product_images").count_documents({"product_id": product_id})


def list_product_images(product_id: UUID) -> list[dict[str, Any]]:
    emb_ids = {
        row["product_image_id"]
        for row in collection("image_embeddings").find(
            {"product_id": product_id}, {"product_image_id": 1}
        )
    }
    cursor = (
        collection("product_images")
        .find({"product_id": product_id})
        .sort([("is_primary", -1), ("position", 1), ("created_at", 1)])
    )
    out: list[dict[str, Any]] = []
    for img in cursor:
        item = with_id(img) or {}
        item["has_embedding"] = img["_id"] in emb_ids
        out.append(item)
    return out


def _admin_stats(product_id: UUID) -> dict[str, int]:
    images = list(collection("product_images").find({"product_id": product_id}, {"status": 1}))
    image_count = len(images)
    ready_count = sum(1 for i in images if i.get("status") == "ready")
    pending_count = sum(1 for i in images if i.get("status") in {"pending", "processing"})
    failed_count = sum(1 for i in images if i.get("status") == "failed")
    embedded_count = collection("image_embeddings").count_documents({"product_id": product_id})
    return {
        "image_count": image_count,
        "ready_count": ready_count,
        "pending_count": pending_count,
        "failed_count": failed_count,
        "embedded_count": embedded_count,
    }


def _admin_enrich(product: dict[str, Any]) -> dict[str, Any]:
    out = _enrich_product(product)
    variant = _default_variant(product["_id"])
    stock = 0
    if variant:
        inv = collection("inventory").find_one({"variant_id": variant["_id"]})
        if inv:
            stock = int(inv.get("quantity_on_hand") or 0)
    out["stock_qty"] = stock
    out.update(_admin_stats(product["_id"]))
    return out


def list_admin_products(
    *,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    filt: dict[str, Any] = {}
    if q:
        filt["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"slug": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    cursor = (
        collection("products")
        .find(filt)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [_admin_enrich(doc) for doc in cursor]


def get_admin_product(product_id: UUID) -> dict[str, Any] | None:
    product = collection("products").find_one({"_id": product_id})
    if not product:
        return None
    out = _admin_enrich(product)
    out["images"] = list_product_images(product_id)
    return out


def set_product_image_status(image_id: UUID, status: str) -> None:
    collection("product_images").update_one(
        {"_id": image_id},
        {"$set": {"status": status, "updated_at": _now()}},
    )


def upsert_image_embedding(
    *,
    product_image_id: UUID,
    product_id: UUID,
    embedding: list[float],
    model_name: str,
) -> UUID:
    """Store an L2-normalized 768-d embedding as a float array (offline cosine search)."""
    now = _now()
    vec = [float(x) for x in embedding]
    existing = collection("image_embeddings").find_one({"product_image_id": product_image_id})
    if existing:
        collection("image_embeddings").update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "embedding": vec,
                    "model_name": model_name,
                    "product_id": product_id,
                    "updated_at": now,
                }
            },
        )
        return existing["_id"]
    emb_id = uuid4()
    collection("image_embeddings").insert_one(
        {
            "_id": emb_id,
            "product_image_id": product_image_id,
            "product_id": product_id,
            "model_name": model_name,
            "embedding": vec,
            "created_at": now,
            "updated_at": now,
        }
    )
    return emb_id


def search_similar(
    *,
    embedding: list[float],
    limit: int = 20,
    category_id: UUID | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """Offline cosine similarity over stored embeddings (no Atlas Vector Search required).

    Loads catalogue embeddings for the active encoder model, scores with numpy
    (dot product of L2-normalized vectors), keeps the best image per product,
    then hydrates product metadata. Suitable for local/demo catalogues; swap for
    Atlas Vector Search later if desired.
    """
    query = np.asarray(embedding, dtype=np.float32)
    qn = float(np.linalg.norm(query))
    if qn > 1e-12:
        query = query / qn

    filt: dict[str, Any] = {}
    if model_name:
        filt["model_name"] = model_name

    # Fetch embeddings; join readiness via product_images.status
    emb_docs = list(collection("image_embeddings").find(filt))
    if not emb_docs:
        return []

    image_ids = [e["product_image_id"] for e in emb_docs]
    ready_images = {
        img["_id"]: img
        for img in collection("product_images").find(
            {"_id": {"$in": image_ids}, "status": "ready"}
        )
    }
    if not ready_images:
        return []

    product_ids = list({e["product_id"] for e in emb_docs if e["product_image_id"] in ready_images})
    product_filt: dict[str, Any] = {"_id": {"$in": product_ids}, "status": "active"}
    if category_id:
        product_filt["category_id"] = category_id
    products = {
        p["_id"]: p for p in collection("products").find(product_filt)
    }
    if not products:
        return []

    # Best score per product
    best: dict[UUID, tuple[float, dict[str, Any], dict[str, Any]]] = {}
    for emb in emb_docs:
        img = ready_images.get(emb["product_image_id"])
        product = products.get(emb["product_id"])
        if not img or not product:
            continue
        vec = np.asarray(emb["embedding"], dtype=np.float32)
        vn = float(np.linalg.norm(vec))
        if vn > 1e-12:
            vec = vec / vn
        score = float(np.dot(query, vec))
        prev = best.get(emb["product_id"])
        if prev is None or score > prev[0]:
            best[emb["product_id"]] = (score, product, img)

    ranked = sorted(best.items(), key=lambda item: item[1][0], reverse=True)[:limit]
    results: list[dict[str, Any]] = []
    for product_id, (score, product, img) in ranked:
        variant = _default_variant(product_id)
        results.append(
            {
                "product_id": product_id,
                "score": score,
                "image_id": img["_id"],
                "name": product.get("name"),
                "slug": product.get("slug"),
                "thumbnail_url": img.get("url") or _thumbnail_url(product_id),
                "price_cents": int(variant.get("price_cents") or 0) if variant else 0,
                "currency": (variant.get("currency") if variant else None) or "USD",
            }
        )
    return results


def record_search_event(
    *,
    result_count: int,
    latency_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    event_id = uuid4()
    collection("search_events").insert_one(
        {
            "_id": event_id,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
            "created_at": _now(),
        }
    )
    return event_id


def ensure_category(name: str, slug: str) -> UUID:
    existing = collection("categories").find_one({"slug": slug})
    if existing:
        return existing["_id"]
    cat_id = uuid4()
    collection("categories").insert_one(
        {
            "_id": cat_id,
            "name": name,
            "slug": slug,
            "created_at": _now(),
        }
    )
    return cat_id
