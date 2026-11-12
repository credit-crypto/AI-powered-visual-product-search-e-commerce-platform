"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useTransition } from "react";

import { AdminIndexingBadge } from "@/components/admin-indexing-badge";
import {
  browserAssetUrl,
  formatMoney,
  getAdminProduct,
  reindexAdminProduct,
  uploadAdminProductImage,
  type AdminProductDetail,
} from "@/lib/api";

export function AdminProductDetailView({ productId }: { productId: string }) {
  const [product, setProduct] = useState<AdminProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const refresh = useCallback(() => {
    getAdminProduct(productId)
      .then(setProduct)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Not found"));
  }, [productId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-300">{error}</p>
        <Link href="/admin/products" className="text-sm text-leaf-400 underline">
          Back to admin products
        </Link>
      </div>
    );
  }

  if (!product) {
    return <p className="text-sm text-ink-100/50">Loading product…</p>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm text-ink-100/50">
            <Link href="/admin/products" className="hover:text-leaf-400">
              Admin products
            </Link>
            <span className="mx-2">/</span>
            {product.slug}
          </p>
          <h1 className="font-display text-3xl text-ink-50">{product.name}</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-ink-100/70">
            <span>{formatMoney(product.price_cents, product.currency)}</span>
            <span>SKU {product.default_sku || "—"}</span>
            <span>Stock {product.stock_qty}</span>
            <AdminIndexingBadge status={product.indexing_status} />
          </div>
          {product.description ? (
            <p className="max-w-2xl text-ink-100/70">{product.description}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/products/${product.slug}`}
            className="rounded-md border border-white/15 px-3 py-2 text-sm text-ink-100/80 transition hover:text-leaf-400"
          >
            View storefront
          </Link>
          <button
            type="button"
            disabled={isPending}
            className="rounded-md border border-white/15 px-3 py-2 text-sm text-ink-100/80 transition hover:text-leaf-400 disabled:opacity-50"
            onClick={() => {
              setMessage(null);
              startTransition(() => {
                void (async () => {
                  try {
                    const result = await reindexAdminProduct(product.id);
                    setMessage(`Reindex ${result.status} (${result.job_id})`);
                    refresh();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Reindex failed");
                  }
                })();
              });
            }}
          >
            Reindex embeddings
          </button>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink-50">Images</h2>
        <p className="text-sm text-ink-100/50">
          {product.image_count} image{product.image_count === 1 ? "" : "s"} ·{" "}
          {product.embedded_count} embedded · {product.ready_count} ready
          {product.failed_count ? ` · ${product.failed_count} failed` : ""}
        </p>

        {product.images.length === 0 ? (
          <p className="text-sm text-ink-100/50">No images yet — upload below.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {product.images.map((image) => {
              const src = browserAssetUrl(image.url);
              return (
                <li key={image.id} className="overflow-hidden border border-white/10">
                  <div className="aspect-square bg-ink-800">
                    {src ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={src} alt="" className="h-full w-full object-cover" />
                    ) : null}
                  </div>
                  <div className="space-y-1 p-2 text-xs text-ink-100/60">
                    <p>
                      {image.status}
                      {image.has_embedding ? " · embedded" : " · no embedding"}
                    </p>
                    {image.is_primary ? <p className="text-leaf-400">Primary</p> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <label className="block max-w-md space-y-2 text-sm">
          <span className="text-ink-100/70">Add images</span>
          <input
            type="file"
            accept="image/*"
            multiple
            disabled={isPending}
            onChange={(event) => {
              const list = event.target.files ? Array.from(event.target.files) : [];
              event.target.value = "";
              if (!list.length) return;
              setMessage(null);
              startTransition(() => {
                void (async () => {
                  try {
                    for (let i = 0; i < list.length; i += 1) {
                      setMessage(`Uploading ${i + 1}/${list.length}…`);
                      await uploadAdminProductImage(product.id, list[i], list[i].name);
                    }
                    setMessage("Upload complete — embeddings queued/ready.");
                    refresh();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Upload failed");
                  }
                })();
              });
            }}
            className="block w-full text-sm text-ink-100/60 file:mr-3 file:rounded-md file:border-0 file:bg-leaf-500 file:px-3 file:py-1.5 file:text-ink-900"
          />
        </label>
      </section>

      {message ? <p className="text-sm text-leaf-400">{message}</p> : null}
    </div>
  );
}
