"""Orders, inventory reservation, and payment event persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg2.extras import Json, RealDictCursor

from app.db import get_connection, get_cursor


class InsufficientStockError(Exception):
    def __init__(self, variant_id: UUID, requested: int, available: int) -> None:
        self.variant_id = variant_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {variant_id}: requested {requested}, available {available}"
        )


def get_variant_snapshot(variant_id: UUID) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                v.id AS variant_id,
                v.sku,
                v.price_cents,
                v.currency,
                v.product_id,
                p.name AS product_name,
                COALESCE(inv.quantity_on_hand, 0) AS quantity_on_hand,
                COALESCE(inv.quantity_reserved, 0) AS quantity_reserved
            FROM product_variants v
            JOIN products p ON p.id = v.product_id
            LEFT JOIN inventory inv ON inv.variant_id = v.id
            WHERE v.id = %s
            """,
            (variant_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


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

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Reserve stock under row locks
            for item in items:
                cur.execute(
                    """
                    SELECT quantity_on_hand, quantity_reserved
                    FROM inventory
                    WHERE variant_id = %s
                    FOR UPDATE
                    """,
                    (item["variant_id"],),
                )
                inv = cur.fetchone()
                if inv is None:
                    raise InsufficientStockError(item["variant_id"], item["quantity"], 0)
                available = int(inv["quantity_on_hand"]) - int(inv["quantity_reserved"])
                if available < int(item["quantity"]):
                    raise InsufficientStockError(
                        item["variant_id"], int(item["quantity"]), available
                    )
                cur.execute(
                    """
                    UPDATE inventory
                    SET quantity_reserved = quantity_reserved + %s,
                        updated_at = now()
                    WHERE variant_id = %s
                    """,
                    (item["quantity"], item["variant_id"]),
                )

            cur.execute(
                """
                INSERT INTO orders (
                    email, cart_id, status, total_cents, currency,
                    payment_provider, idempotency_key, reserved
                )
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, true)
                RETURNING id, email, status, total_cents, currency, cart_id,
                          payment_provider, checkout_session_id, created_at
                """,
                (
                    email,
                    cart_id,
                    total,
                    currency,
                    payment_provider,
                    idempotency_key,
                ),
            )
            order = dict(cur.fetchone())

            for item in items:
                cur.execute(
                    """
                    INSERT INTO order_items (
                        order_id, variant_id, product_id, quantity,
                        unit_price_cents, sku, product_name, currency
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order["id"],
                        item["variant_id"],
                        item["product_id"],
                        item["quantity"],
                        item["unit_price_cents"],
                        item["sku"],
                        item["product_name"],
                        item.get("currency") or currency,
                    ),
                )

            return order


def set_checkout_session(order_id: UUID, checkout_session_id: str, payment_ref: str | None = None) -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE orders
            SET checkout_session_id = %s,
                payment_ref = COALESCE(%s, payment_ref),
                updated_at = now()
            WHERE id = %s
            """,
            (checkout_session_id, payment_ref, order_id),
        )


def get_order(order_id: UUID) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, cart_id, status, total_cents, currency,
                   payment_provider, payment_ref, checkout_session_id,
                   reserved, idempotency_key, created_at, updated_at
            FROM orders WHERE id = %s
            """,
            (order_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_order_by_checkout_session(checkout_session_id: str) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, cart_id, status, total_cents, currency,
                   payment_provider, payment_ref, checkout_session_id,
                   reserved, created_at
            FROM orders WHERE checkout_session_id = %s
            """,
            (checkout_session_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_order_items(order_id: UUID) -> list[dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, variant_id, product_id, quantity, unit_price_cents,
                   sku, product_name, currency
            FROM order_items
            WHERE order_id = %s
            ORDER BY id
            """,
            (order_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def list_orders_by_email(email: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, status, total_cents, currency, created_at, updated_at
            FROM orders
            WHERE lower(email) = lower(%s)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (email, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def payment_event_exists(provider: str, event_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM payment_events
            WHERE provider = %s AND event_id = %s
            """,
            (provider, event_id),
        )
        return cur.fetchone() is not None


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
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Idempotency: if event already processed, return current order
            cur.execute(
                """
                SELECT 1 FROM payment_events
                WHERE provider = %s AND event_id = %s
                FOR UPDATE
                """,
                (provider, event_id),
            )
            if cur.fetchone():
                cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                return dict(cur.fetchone())

            cur.execute(
                """
                SELECT * FROM orders WHERE id = %s FOR UPDATE
                """,
                (order_id,),
            )
            order = cur.fetchone()
            if order is None:
                raise LookupError("order not found")
            order = dict(order)

            if order["status"] == "paid":
                cur.execute(
                    """
                    INSERT INTO payment_events (provider, event_id, event_type, order_id, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (provider, event_id) DO NOTHING
                    """,
                    (provider, event_id, event_type, order_id, Json(payload)),
                )
                return order

            if order["status"] not in {"pending", "paid"}:
                raise ValueError(f"order status {order['status']} cannot be marked paid")

            cur.execute(
                """
                SELECT variant_id, quantity FROM order_items WHERE order_id = %s
                """,
                (order_id,),
            )
            lines = cur.fetchall()

            if order.get("reserved"):
                for line in lines:
                    cur.execute(
                        """
                        SELECT quantity_on_hand, quantity_reserved
                        FROM inventory WHERE variant_id = %s FOR UPDATE
                        """,
                        (line["variant_id"],),
                    )
                    inv = cur.fetchone()
                    if inv is None:
                        continue
                    qty = int(line["quantity"])
                    cur.execute(
                        """
                        UPDATE inventory
                        SET quantity_on_hand = GREATEST(quantity_on_hand - %s, 0),
                            quantity_reserved = GREATEST(quantity_reserved - %s, 0),
                            updated_at = now()
                        WHERE variant_id = %s
                        """,
                        (qty, qty, line["variant_id"]),
                    )

            cur.execute(
                """
                UPDATE orders
                SET status = 'paid',
                    reserved = false,
                    payment_ref = COALESCE(%s, payment_ref),
                    updated_at = now()
                WHERE id = %s
                RETURNING *
                """,
                (payment_ref, order_id),
            )
            updated = dict(cur.fetchone())

            if order.get("cart_id"):
                cur.execute(
                    """
                    DELETE FROM cart_items WHERE cart_id = %s
                    """,
                    (order["cart_id"],),
                )
                cur.execute(
                    """
                    UPDATE carts SET status = 'converted', updated_at = now()
                    WHERE id = %s
                    """,
                    (order["cart_id"],),
                )

            cur.execute(
                """
                INSERT INTO payment_events (provider, event_id, event_type, order_id, payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (provider, event_id, event_type, order_id, Json(payload)),
            )
            return updated


def release_reservation(order_id: UUID) -> None:
    """Release reserved stock for a cancelled/expired pending order."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (order_id,))
            order = cur.fetchone()
            if not order or not order["reserved"] or order["status"] != "pending":
                return
            cur.execute(
                "SELECT variant_id, quantity FROM order_items WHERE order_id = %s",
                (order_id,),
            )
            for line in cur.fetchall():
                cur.execute(
                    """
                    UPDATE inventory
                    SET quantity_reserved = GREATEST(quantity_reserved - %s, 0),
                        updated_at = now()
                    WHERE variant_id = %s
                    """,
                    (line["quantity"], line["variant_id"]),
                )
            cur.execute(
                """
                UPDATE orders
                SET status = 'cancelled', reserved = false, updated_at = now()
                WHERE id = %s
                """,
                (order_id,),
            )
