"use client";

import { useEffect, useState } from "react";

import { listProducts, type ProductSummary } from "@/lib/api";

function formatPrice(cents: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
  } catch {
    return `$${(cents / 100).toFixed(2)}`;
  }
}

export function ProductsList() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    <ul className="divide-y divide-white/10 border border-white/10">
      {products.map((product) => (
        <li key={product.id} className="flex items-center gap-4 px-4 py-3">
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
          <div>
            <p className="text-ink-50">{product.name}</p>
            <p className="text-sm text-ink-100/60">
              {formatPrice(product.price_cents, product.currency)}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
