"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useTransition } from "react";

import {
  browserAssetUrl,
  formatMoney,
  getCart,
  removeCartItem,
  updateCartItem,
  type CartResponse,
} from "@/lib/api";

export function CartView() {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const refresh = useCallback(() => {
    getCart()
      .then(setCart)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load cart"));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (!cart) return <p className="text-sm text-ink-100/50">Loading cart…</p>;

  if (cart.items.length === 0) {
    return (
      <div className="space-y-3 border border-white/10 px-4 py-8 text-center">
        <p className="text-sm text-ink-100/50">Your cart is empty</p>
        <Link href="/products" className="text-sm text-leaf-400 underline">
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ul className="divide-y divide-white/10 border border-white/10">
        {cart.items.map((item) => (
          <li key={item.variant_id} className="flex flex-wrap items-center gap-4 px-4 py-4">
            <div className="h-16 w-16 shrink-0 overflow-hidden bg-ink-800">
              {browserAssetUrl(item.thumbnail_url) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={browserAssetUrl(item.thumbnail_url)}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-ink-50">{item.product_name}</p>
              <p className="text-sm text-ink-100/60">
                {formatMoney(item.unit_price_cents || 0, item.currency)} · {item.sku}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={isPending || item.quantity <= 1}
                className="border border-white/15 px-2 py-1 text-sm disabled:opacity-40"
                onClick={() =>
                  startTransition(() => {
                    void updateCartItem(item.variant_id, item.quantity - 1).then(setCart);
                  })
                }
              >
                −
              </button>
              <span className="w-8 text-center text-sm">{item.quantity}</span>
              <button
                type="button"
                disabled={isPending}
                className="border border-white/15 px-2 py-1 text-sm disabled:opacity-40"
                onClick={() =>
                  startTransition(() => {
                    void updateCartItem(item.variant_id, item.quantity + 1).then(setCart);
                  })
                }
              >
                +
              </button>
              <button
                type="button"
                disabled={isPending}
                className="ml-2 text-sm text-ink-100/50 underline"
                onClick={() =>
                  startTransition(() => {
                    void removeCartItem(item.variant_id).then(setCart);
                  })
                }
              >
                Remove
              </button>
            </div>
            <p className="w-24 text-right text-sm text-leaf-400">
              {formatMoney(item.line_total_cents || 0, item.currency)}
            </p>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-lg text-ink-50">
          Subtotal{" "}
          <span className="text-leaf-400">{formatMoney(cart.subtotal_cents, cart.currency)}</span>
        </p>
        <Link
          href="/checkout"
          className="rounded-md bg-leaf-500 px-5 py-2.5 text-sm font-medium text-ink-900 transition hover:bg-leaf-400"
        >
          Checkout
        </Link>
      </div>
    </div>
  );
}
