"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminIndexingBadge } from "@/components/admin-indexing-badge";
import {
  browserAssetUrl,
  formatMoney,
  listAdminProducts,
  type AdminProductSummary,
} from "@/lib/api";

export function AdminProductsList() {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<AdminProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProducts(null);
    setError(null);
    listAdminProducts(query || undefined)
      .then(setProducts)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [query]);

  return (
    <div className="space-y-4">
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(q.trim());
        }}
      >
        <input
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Filter by name or slug…"
          className="min-w-[16rem] flex-1 rounded-md border border-white/15 bg-ink-900/80 px-3 py-2 text-sm text-ink-50 outline-none placeholder:text-ink-100/40"
        />
        <button
          type="submit"
          className="rounded-md border border-white/15 px-3 py-2 text-sm text-ink-100/80 transition hover:border-leaf-400/40 hover:text-leaf-400"
        >
          Filter
        </button>
        <Link
          href="/admin/products/new"
          className="rounded-md bg-leaf-500 px-3 py-2 text-sm font-medium text-ink-900 transition hover:bg-leaf-400"
        >
          New product
        </Link>
      </form>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {!products && !error ? <p className="text-sm text-ink-100/50">Loading…</p> : null}

      {products && products.length === 0 ? (
        <p className="text-sm text-ink-100/50">No products yet. Create one to get started.</p>
      ) : null}

      {products && products.length > 0 ? (
        <div className="overflow-x-auto border border-white/10">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-ink-100/50">
              <tr>
                <th className="px-3 py-2 font-medium">Product</th>
                <th className="px-3 py-2 font-medium">Price</th>
                <th className="px-3 py-2 font-medium">Stock</th>
                <th className="px-3 py-2 font-medium">Images</th>
                <th className="px-3 py-2 font-medium">Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {products.map((product) => {
                const thumb = browserAssetUrl(product.thumbnail_url);
                return (
                  <tr key={product.id} className="hover:bg-white/[0.03]">
                    <td className="px-3 py-3">
                      <Link
                        href={`/admin/products/${product.id}`}
                        className="flex items-center gap-3 transition hover:text-leaf-400"
                      >
                        <div className="h-10 w-10 shrink-0 overflow-hidden bg-ink-800">
                          {thumb ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={thumb} alt="" className="h-full w-full object-cover" />
                          ) : null}
                        </div>
                        <div>
                          <p className="text-ink-50">{product.name}</p>
                          <p className="text-xs text-ink-100/40">{product.slug}</p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-3 py-3 text-ink-100/80">
                      {formatMoney(product.price_cents, product.currency)}
                    </td>
                    <td className="px-3 py-3 text-ink-100/80">{product.stock_qty}</td>
                    <td className="px-3 py-3 text-ink-100/80">
                      {product.image_count}
                      <span className="text-ink-100/40">
                        {" "}
                        · {product.embedded_count} emb
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <AdminIndexingBadge status={product.indexing_status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
