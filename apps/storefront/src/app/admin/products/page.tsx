import Link from "next/link";

import { AdminProductsList } from "@/components/admin-products-list";

export default function AdminProductsPage() {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm text-ink-100/50">
            <Link href="/admin" className="hover:text-leaf-400">
              Admin
            </Link>
            <span className="mx-2">/</span>
            Products
          </p>
          <h1 className="font-display text-3xl text-ink-50">Admin products</h1>
          <p className="text-ink-100/70">
            Catalogue with image counts and visual-search indexing status.
          </p>
        </div>
      </div>
      <AdminProductsList />
    </section>
  );
}
