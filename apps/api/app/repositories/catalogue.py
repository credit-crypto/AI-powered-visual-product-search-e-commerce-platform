"""Catalogue + embedding persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import numpy as np
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json

from app.db import get_connection, get_cursor


def _register(conn) -> None:
    register_vector(conn)


def _as_vector(embedding: list[float]) -> np.ndarray:
    return np.asarray(embedding, dtype=np.float32)


def create_product(
    *,
    name: str,
    slug: str,
    description: str | None,
    category_id: UUID | None,
    price_cents: int,
    currency: str = "USD",
    status: str = "active",
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (category_id, name, slug, description, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, slug, status
                """,
                (category_id, name, slug, description, status),
            )
            product = cur.fetchone()
            product_id = product[0]
            cur.execute(
                """
                INSERT INTO product_variants
                    (product_id, sku, name, price_cents, currency, is_default)
                VALUES (%s, %s, %s, %s, %s, true)
                RETURNING id
                """,
                (product_id, f"{slug}-default", "Default", price_cents, currency),
            )
            variant_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO inventory (variant_id, quantity_on_hand, quantity_reserved)
                VALUES (%s, %s, 0)
                """,
                (variant_id, 25),
            )
    return {
        "id": product_id,
        "name": product[1],
        "slug": product[2],
        "status": product[3],
        "variant_id": variant_id,
    }


def get_product(product_id: UUID) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id, p.name, p.slug, p.description, p.category_id, p.status,
                   v.id AS default_variant_id, v.sku AS default_sku,
                   v.price_cents, v.currency,
                   (
                     SELECT pi.url FROM product_images pi
                     WHERE pi.product_id = p.id
                     ORDER BY pi.is_primary DESC, pi.position ASC, pi.created_at ASC
                     LIMIT 1
                   ) AS thumbnail_url
            FROM products p
            LEFT JOIN product_variants v ON v.product_id = p.id AND v.is_default = true
            WHERE p.id = %s
            """,
            (product_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_products(
    *,
    q: str | None = None,
    category_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    clauses = ["p.status = 'active'"]
    params: list[Any] = []
    if category_id:
        clauses.append("p.category_id = %s")
        params.append(category_id)
    if q:
        clauses.append("(p.name ILIKE %s OR p.description ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    where = " AND ".join(clauses)
    params.extend([limit, offset])
    with get_cursor() as cur:
        cur.execute(
            f"""
            SELECT p.id, p.name, p.slug,
                   v.id AS default_variant_id,
                   COALESCE(v.price_cents, 0) AS price_cents,
                   COALESCE(v.currency, 'USD') AS currency,
                   (
                     SELECT pi.url FROM product_images pi
                     WHERE pi.product_id = p.id
                     ORDER BY pi.is_primary DESC, pi.position ASC, pi.created_at ASC
                     LIMIT 1
                   ) AS thumbnail_url
            FROM products p
            LEFT JOIN product_variants v ON v.product_id = p.id AND v.is_default = true
            WHERE {where}
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params,
        )
        return [dict(row) for row in cur.fetchall()]


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
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO product_images
                (product_id, storage_key, url, position, is_primary, width, height, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id, product_id, storage_key, url, status
            """,
            (product_id, storage_key, url, position, is_primary, width, height),
        )
        return dict(cur.fetchone())


def get_product_image(image_id: UUID) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, product_id, storage_key, url, status, width, height
            FROM product_images
            WHERE id = %s
            """,
            (image_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_product_image_ids(product_id: UUID) -> list[UUID]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id FROM product_images WHERE product_id = %s ORDER BY position, created_at",
            (product_id,),
        )
        return [row["id"] for row in cur.fetchall()]


def set_product_image_status(image_id: UUID, status: str) -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE product_images
            SET status = %s, updated_at = now()
            WHERE id = %s
            """,
            (status, image_id),
        )


def upsert_image_embedding(
    *,
    product_image_id: UUID,
    product_id: UUID,
    embedding: list[float],
    model_name: str,
) -> UUID:
    with get_connection() as conn:
        _register(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO image_embeddings
                    (product_image_id, product_id, model_name, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_image_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    updated_at = now()
                RETURNING id
                """,
                (product_image_id, product_id, model_name, _as_vector(embedding)),
            )
            return cur.fetchone()[0]


def search_similar(
    *,
    embedding: list[float],
    limit: int = 20,
    category_id: UUID | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """pgvector cosine search; one row per product (best matching image)."""
    filters = ["p.status = 'active'", "pi.status = 'ready'"]
    filter_params: list[Any] = []
    if model_name:
        filters.append("e.model_name = %s")
        filter_params.append(model_name)
    if category_id:
        filters.append("p.category_id = %s")
        filter_params.append(category_id)
    where = " AND ".join(filters)

    sql = f"""
        SELECT *
        FROM (
            SELECT DISTINCT ON (ranked.product_id)
                ranked.product_id,
                ranked.name,
                ranked.image_id,
                ranked.thumbnail_url,
                ranked.price_cents,
                ranked.currency,
                ranked.score
            FROM (
                SELECT
                    p.id AS product_id,
                    p.name,
                    pi.id AS image_id,
                    pi.url AS thumbnail_url,
                    COALESCE(v.price_cents, 0) AS price_cents,
                    COALESCE(v.currency, 'USD') AS currency,
                    (1 - (e.embedding <=> %s)) AS score,
                    (e.embedding <=> %s) AS distance
                FROM image_embeddings e
                JOIN product_images pi ON pi.id = e.product_image_id
                JOIN products p ON p.id = e.product_id
                LEFT JOIN product_variants v
                    ON v.product_id = p.id AND v.is_default = true
                WHERE {where}
            ) ranked
            ORDER BY ranked.product_id, ranked.distance ASC
        ) best
        ORDER BY best.score DESC
        LIMIT %s
    """
    query_vec = _as_vector(embedding)
    params: list[Any] = [query_vec, query_vec, *filter_params, limit]
    with get_connection() as conn:
        _register(conn)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def record_search_event(
    *,
    result_count: int,
    latency_ms: int,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO search_events (query_type, result_count, latency_ms, metadata)
            VALUES ('image', %s, %s, %s)
            RETURNING id
            """,
            (result_count, latency_ms, Json(metadata or {})),
        )
        return cur.fetchone()["id"]


def ensure_category(name: str, slug: str) -> UUID:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO categories (name, slug)
            VALUES (%s, %s)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (name, slug),
        )
        return cur.fetchone()["id"]
