"use client";

import { useEffect, useState, useTransition } from "react";

import { formatMoney, getOrder, listOrders, type OrderSummary } from "@/lib/api";

const EMAIL_KEY = "visual-shop:orders-email";

export function OrdersView() {
  const [email, setEmail] = useState("");
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [highlight, setHighlight] = useState<OrderSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paidFlash, setPaidFlash] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const saved = localStorage.getItem(EMAIL_KEY);
    if (saved) setEmail(saved);
    const params = new URLSearchParams(window.location.search);
    setPaidFlash(params.get("paid") === "1");
    const orderId = params.get("order_id");
    if (orderId) {
      getOrder(orderId)
        .then((order) => {
          setHighlight(order);
          if (order.email) {
            setEmail(order.email);
            localStorage.setItem(EMAIL_KEY, order.email);
          }
        })
        .catch(() => undefined);
    }
  }, []);

  function load() {
    setError(null);
    localStorage.setItem(EMAIL_KEY, email);
    startTransition(() => {
      void listOrders(email)
        .then(setOrders)
        .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed"));
    });
  }

  return (
    <div className="space-y-6">
      {paidFlash ? (
        <p className="border border-leaf-500/40 bg-leaf-500/10 px-3 py-2 text-sm text-leaf-400">
          Payment received — thank you.
        </p>
      ) : null}

      {highlight ? (
        <div className="border border-white/10 px-4 py-4 text-sm">
          <p className="text-ink-50">
            Order <code className="text-leaf-400">{highlight.id}</code> · {highlight.status}
          </p>
          <p className="text-ink-100/70">
            {formatMoney(highlight.total_cents, highlight.currency)}
            {highlight.email ? ` · ${highlight.email}` : null}
          </p>
          {highlight.items?.length ? (
            <ul className="mt-3 space-y-1 text-ink-100/60">
              {highlight.items.map((item) => (
                <li key={`${item.variant_id}-${item.sku}`}>
                  {item.product_name || item.sku} × {item.quantity}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <form
        className="flex flex-wrap gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          load();
        }}
      >
        <input
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Checkout email"
          className="min-w-[16rem] flex-1 border border-white/15 bg-ink-900 px-3 py-2 text-sm text-ink-50 outline-none focus:border-leaf-400"
        />
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-leaf-500 px-4 py-2 text-sm font-medium text-ink-900 disabled:opacity-50"
        >
          {isPending ? "Loading…" : "Find orders"}
        </button>
      </form>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <ul className="divide-y divide-white/10 border border-white/10">
        {orders.length === 0 ? (
          <li className="px-4 py-6 text-sm text-ink-100/50">No orders yet for this email</li>
        ) : (
          orders.map((order) => (
            <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
              <div>
                <p className="text-ink-50">{order.id}</p>
                <p className="text-ink-100/50">{order.created_at}</p>
              </div>
              <p className="text-leaf-400">
                {order.status} · {formatMoney(order.total_cents, order.currency)}
              </p>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
