import { Suspense } from "react";

import { ProductsGrid } from "@/components/products-grid";

export default function ProductsPage() {
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="font-display text-3xl text-ink-50">Products</h1>
        <p className="text-ink-100/70">
          Browse the catalogue, search by keyword, or use the camera button for visual search.
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-ink-100/50">Loading catalogue…</p>}>
        <ProductsGrid />
      </Suspense>
    </section>
  );
}
