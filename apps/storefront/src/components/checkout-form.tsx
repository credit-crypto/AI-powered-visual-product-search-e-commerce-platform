"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import {
  createCheckoutSession,
  formatMoney,
  getCart,
  type CartResponse,
} from "@/lib/api";

export function CheckoutForm() {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [cancelled, setCancelled] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setCancelled(params.get("cancelled") === "1");
    getCart()
      .then(setCart)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load cart"));
  }, []);

  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (!cart) return <p className="text-sm text-ink-100/50">Loading…</p>;

  if (cart.items.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-ink-100/70">Nothing to check out.</p>
        <Link href="/products" className="text-sm text-leaf-400 underline">
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {cancelled ? (
        <p className="border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
          Payment cancelled — your cart is still reserved only after you start checkout again.
        </p>
      ) : null}

      <ul className="divide-y divide-white/10 border border-white/10 text-sm">
        {cart.items.map((item) => (
          <li key={item.variant_id} className="flex justify-between gap-4 px-4 py-3">
            <span>
              {item.product_name} × {item.quantity}
            </span>
            <span className="text-leaf-400">
              {formatMoney(item.line_total_cents || 0, item.currency)}
            </span>
          </li>
        ))}
        <li className="flex justify-between px-4 py-3 font-medium text-ink-50">
          <span>Total</span>
          <span>{formatMoney(cart.subtotal_cents, cart.currency)}</span>
        </li>
      </ul>

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          startTransition(() => {
            void createCheckoutSession(email)
              .then((session) => {
                window.location.href = session.payment_url;
              })
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "Checkout failed");
              });
          });
        }}
      >
        <label className="block space-y-2 text-sm">
          <span className="text-ink-100/80">Email for order receipt</span>
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full border border-white/15 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-leaf-400"
            placeholder="you@example.com"
          />
        </label>
        <p className="text-xs text-ink-100/50">
          Demo payments use the <strong>stub</strong> provider (no real charge). Set{" "}
          <code className="text-leaf-400">PAYMENT_PROVIDER=stripe</code> with test keys for Stripe
          Checkout.
        </p>
        <button
          type="submit"
          disabled={isPending || !email}
          className="rounded-md bg-leaf-500 px-5 py-2.5 text-sm font-medium text-ink-900 transition hover:bg-leaf-400 disabled:opacity-50"
        >
          {isPending ? "Starting checkout…" : "Pay now"}
        </button>
      </form>
    </div>
  );
}
