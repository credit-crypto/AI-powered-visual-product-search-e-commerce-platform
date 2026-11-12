"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import {
  addToCart,
  browserAssetUrl,
  formatMoney,
  getProductBySlug,
  type ProductDetail,
} from "@/lib/api";

export function ProductDetailView({ slug }: { slug: string }) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    getProductBySlug(slug)
      .then(setProduct)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Not found"));
  }, [slug]);

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-300">{error}</p>
        <Link href="/products" className="text-sm text-leaf-400 underline">
          Back to products
        </Link>
      </div>
    );
  }

  if (!product) {
    return <p className="text-sm text-ink-100/50">Loading product…</p>;
  }

  const image = browserAssetUrl(product.image_urls?.[0] || product.thumbnail_url);

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div className="aspect-square overflow-hidden border border-white/10 bg-ink-800">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-ink-100/40">
            No image
          </div>
        )}
      </div>

      <div className="space-y-5">
        <div className="space-y-2">
          <p className="text-sm text-ink-100/50">
            <Link href="/products" className="hover:text-leaf-400">
              Products
            </Link>
            <span className="mx-2">/</span>
            {product.slug}
          </p>
          <h1 className="font-display text-3xl text-ink-50 sm:text-4xl">{product.name}</h1>
          <p className="text-xl text-leaf-400">
            {formatMoney(product.price_cents, product.currency)}
          </p>
        </div>

        {product.description ? (
          <p className="text-ink-100/70">{product.description}</p>
        ) : null}

        {product.default_sku ? (
          <p className="text-xs text-ink-100/40">SKU {product.default_sku}</p>
        ) : null}

        <button
          type="button"
          disabled={isPending || !product.default_variant_id}
          className="rounded-md bg-leaf-500 px-5 py-2.5 text-sm font-medium text-ink-900 transition hover:bg-leaf-400 disabled:opacity-50"
          onClick={() => {
            if (!product.default_variant_id) return;
            setMessage(null);
            startTransition(() => {
              void addToCart(product.default_variant_id!)
                .then(() => setMessage("Added to cart"))
                .catch((err: unknown) =>
                  setError(err instanceof Error ? err.message : "Add failed"),
                );
            });
          }}
        >
          {isPending ? "Adding…" : "Add to cart"}
        </button>

        {message ? (
          <p className="text-sm text-leaf-400">
            {message}.{" "}
            <Link href="/cart" className="underline">
              View cart
            </Link>
          </p>
        ) : null}
      </div>
    </div>
  );
}
