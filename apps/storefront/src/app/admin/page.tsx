import Link from "next/link";

export default function AdminPage() {
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl text-ink-50">Admin</h1>
        <p className="text-ink-100/70">
          Catalogue management for Visual Shop. Upload products and images; embeddings index
          automatically for visual search.
        </p>
      </div>

      <p className="rounded-md border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-sm text-amber-100/80">
        Security stub: admin routes are open (no auth/RBAC yet). Fine for Try Live MVP only.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/admin/products"
          className="block border border-white/10 p-5 transition hover:border-leaf-400/40"
        >
          <h2 className="font-display text-xl text-ink-50">Products</h2>
          <p className="mt-2 text-sm text-ink-100/60">
            List catalogue items with indexing status, create new products, upload images, reindex.
          </p>
        </Link>
        <Link
          href="/admin/products/new"
          className="block border border-white/10 p-5 transition hover:border-leaf-400/40"
        >
          <h2 className="font-display text-xl text-ink-50">New product</h2>
          <p className="mt-2 text-sm text-ink-100/60">
            Name, description, price, SKU/stock, and image uploads in one flow.
          </p>
        </Link>
      </div>
    </section>
  );
}
