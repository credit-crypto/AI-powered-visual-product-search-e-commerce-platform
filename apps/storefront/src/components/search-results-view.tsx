"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  SEARCH_RESULTS_KEY,
  type VisualSearchResponse,
  type VisualSearchResultItem,
} from "@/lib/api";

function formatPrice(cents?: number | null, currency?: string | null): string {
  if (cents == null) return "";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
    }).format(cents / 100);
  } catch {
    return `$${(cents / 100).toFixed(2)}`;
  }
}

function ResultCard({ item }: { item: VisualSearchResultItem }) {
  return (
    <article className="flex gap-4 border-b border-white/10 py-4">
      <div className="h-24 w-24 shrink-0 overflow-hidden bg-ink-800">
        {item.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.thumbnail_url}
            alt={item.name || "Product"}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-ink-100/40">
            No image
          </div>
        )}
      </div>
      <div className="space-y-1">
        <h2 className="font-display text-lg text-ink-50">{item.name || "Untitled product"}</h2>
        <p className="text-sm text-leaf-400">
          Similarity {(item.score * 100).toFixed(1)}%
          {item.price_cents != null ? ` · ${formatPrice(item.price_cents, item.currency)}` : null}
        </p>
        <p className="text-xs text-ink-100/40">{item.product_id}</p>
      </div>
    </article>
  );
}

export function SearchResultsView() {
  const [payload, setPayload] = useState<VisualSearchResponse | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(SEARCH_RESULTS_KEY);
      if (raw) setPayload(JSON.parse(raw) as VisualSearchResponse);
    } catch {
      setPayload(null);
    } finally {
      setReady(true);
    }
  }, []);

  if (!ready) {
    return <p className="text-sm text-ink-100/50">Loading results…</p>;
  }

  if (!payload) {
    return (
      <div className="space-y-3">
        <p className="text-ink-100/70">No search results yet.</p>
        <Link href="/visual-search" className="text-sm text-leaf-400 underline">
          Run a visual search
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm text-ink-100/60">
        <p>
          {payload.results.length} product{payload.results.length === 1 ? "" : "s"}
          {payload.query_ms != null ? ` · ${payload.query_ms} ms` : null}
        </p>
        {payload.model_name ? <p className="text-xs">{payload.model_name}</p> : null}
      </div>

      {payload.message ? <p className="text-sm text-ink-100/60">{payload.message}</p> : null}

      {payload.results.length === 0 ? (
        <div className="border border-white/10 px-4 py-8 text-center text-sm text-ink-100/50">
          No matches — seed the catalogue and ensure images are indexed.
        </div>
      ) : (
        <div>
          {payload.results.map((item) => (
            <ResultCard key={`${item.product_id}-${item.image_id}`} item={item} />
          ))}
        </div>
      )}

      <Link href="/visual-search" className="inline-block text-sm text-leaf-400 underline">
        Search again
      </Link>
    </div>
  );
}
