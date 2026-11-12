"use client";

import { useEffect, useState, useTransition } from "react";

import { addToCart, formatMoney, listProducts, type ProductSummary } from "@/lib/api";

export function ProductsList() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    listProducts()
      .then(setProducts)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (!products) {
    return <p className="text-sm text-ink-100/50">Loading products…</p>;
  }

  if (products.length === 0) {
    return (
      <p className="text-sm text-ink-100/50">
        No products yet. Run the seed script (see README demo steps).
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {message ? <p className="text-sm text-leaf-400">{message}</p> : null}
      <ul className="divide-y divide-white/10 border border-white/10">
        {products.map((product) => (
          <li key={product.id} className="flex flex-wrap items-center gap-4 px-4 py-3">
            <div className="h-14 w-14 shrink-0 overflow-hidden bg-ink-800">
              {product.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={product.thumbnail_url}
                  alt={product.name}
                  className="h-full w-full object-cover"
                />
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-ink-50">{product.name}</p>
              <p className="text-sm text-ink-100/60">
                {formatMoney(product.price_cents, product.currency)}
              </p>
            </div>
            <button
              type="button"
              disabled={isPending || !product.default_variant_id}
              className="rounded-md border border-white/15 px-3 py-1.5 text-sm text-ink-100 transition hover:border-leaf-400/50 disabled:opacity-40"
              onClick={() => {
                if (!product.default_variant_id) return;
                setMessage(null);
                startTransition(() => {
                  void addToCart(product.default_variant_id!)
                    .then(() => setMessage(`Added ${product.name} to cart`))
                    .catch((err: unknown) =>
                      setError(err instanceof Error ? err.message : "Add failed"),
                    );
                });
              }}
            >
              Add to cart
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
