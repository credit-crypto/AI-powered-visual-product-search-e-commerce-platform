"""Guest/session cart persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.db import get_connection, get_cursor


def get_or_create_cart(session_token: str) -> dict[str, Any]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, session_token, status, created_at, updated_at
            FROM carts
            WHERE session_token = %s AND status = 'open'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_token,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        cur.execute(
            """
            INSERT INTO carts (session_token, status)
            VALUES (%s, 'open')
            RETURNING id, session_token, status, created_at, updated_at
            """,
            (session_token,),
        )
        return dict(cur.fetchone())


def get_cart_by_id(cart_id: UUID) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, session_token, status, user_id, created_at, updated_at
            FROM carts WHERE id = %s
            """,
            (cart_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_cart_items(cart_id: UUID) -> list[dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                ci.id AS cart_item_id,
                ci.variant_id,
                ci.quantity,
                v.sku,
                v.price_cents AS unit_price_cents,
                v.currency,
                v.product_id,
                p.name AS product_name,
                p.slug AS product_slug,
                (
                  SELECT pi.url FROM product_images pi
                  WHERE pi.product_id = p.id
                  ORDER BY pi.is_primary DESC, pi.position ASC
                  LIMIT 1
                ) AS thumbnail_url,
                COALESCE(inv.quantity_on_hand - inv.quantity_reserved, 0) AS available_qty
            FROM cart_items ci
            JOIN product_variants v ON v.id = ci.variant_id
            JOIN products p ON p.id = v.product_id
            LEFT JOIN inventory inv ON inv.variant_id = v.id
            WHERE ci.cart_id = %s
            ORDER BY ci.id
            """,
            (cart_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def upsert_cart_item(cart_id: UUID, variant_id: UUID, quantity: int) -> None:
    if quantity < 1:
        raise ValueError("quantity must be >= 1")
    with get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM product_variants WHERE id = %s",
            (variant_id,),
        )
        if cur.fetchone() is None:
            raise LookupError("variant not found")
        cur.execute(
            """
            INSERT INTO cart_items (cart_id, variant_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (cart_id, variant_id)
            DO UPDATE SET quantity = EXCLUDED.quantity
            """,
            (cart_id, variant_id, quantity),
        )
        cur.execute(
            "UPDATE carts SET updated_at = now() WHERE id = %s",
            (cart_id,),
        )


def set_cart_item_quantity(cart_id: UUID, variant_id: UUID, quantity: int) -> None:
    if quantity < 1:
        delete_cart_item(cart_id, variant_id)
        return
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE cart_items
            SET quantity = %s
            WHERE cart_id = %s AND variant_id = %s
            """,
            (quantity, cart_id, variant_id),
        )
        if cur.rowcount == 0:
            raise LookupError("cart item not found")
        cur.execute(
            "UPDATE carts SET updated_at = now() WHERE id = %s",
            (cart_id,),
        )


def delete_cart_item(cart_id: UUID, variant_id: UUID) -> None:
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM cart_items WHERE cart_id = %s AND variant_id = %s",
            (cart_id, variant_id),
        )
        cur.execute(
            "UPDATE carts SET updated_at = now() WHERE id = %s",
            (cart_id,),
        )


def clear_cart_items(cart_id: UUID) -> None:
    with get_cursor() as cur:
        cur.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))
        cur.execute(
            "UPDATE carts SET updated_at = now() WHERE id = %s",
            (cart_id,),
        )


def mark_cart_converted(cart_id: UUID) -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE carts
            SET status = 'converted', updated_at = now()
            WHERE id = %s
            """,
            (cart_id,),
        )


def new_session_token() -> str:
    return uuid4().hex
