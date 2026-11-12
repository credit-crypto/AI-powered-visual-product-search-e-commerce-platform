"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { CatalogueSearch } from "@/components/catalogue-search";
import { formatMoney, listProducts, type ProductSummary } from "@/lib/api";

export function ProductsGrid() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") || "";
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProducts(null);
    listProducts(q || undefined, 100)
      .then(setProducts)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [q]);

  return (
    <div className="space-y-6">
      <CatalogueSearch
        initialQuery={q}
        navigateOnTextSearch={false}
        onTextSearch={(next) => {
          const href = next ? `/products?q=${encodeURIComponent(next)}` : "/products";
          router.push(href);
        }}
      />

      {q ? (
        <p className="text-sm text-ink-100/60">
          Showing results for <span className="text-leaf-400">{q}</span>
        </p>
      ) : null}

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {!products && !error ? <p className="text-sm text-ink-100/50">Loading products…</p> : null}
      {products && products.length === 0 ? (
        <p className="text-sm text-ink-100/50">No products match this search.</p>
      ) : null}

      {products && products.length > 0 ? (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {products.map((product) => (
            <li key={product.id}>
              <Link
                href={`/products/${product.slug}`}
                className="group block h-full overflow-hidden border border-white/10 transition hover:border-leaf-400/40"
              >
                <div className="aspect-square bg-ink-800">
                  {product.thumbnail_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={product.thumbnail_url}
                      alt={product.name}
                      className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
                    />
                  ) : null}
                </div>
                <div className="space-y-1 p-3">
                  <p className="line-clamp-2 text-sm text-ink-50">{product.name}</p>
                  <p className="text-sm text-leaf-400">
                    {formatMoney(product.price_cents, product.currency)}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
