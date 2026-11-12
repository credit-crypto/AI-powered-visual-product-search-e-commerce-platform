import Link from "next/link";

import { AdminProductForm } from "@/components/admin-product-form";

export default function AdminNewProductPage() {
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <p className="text-sm text-ink-100/50">
          <Link href="/admin" className="hover:text-leaf-400">
            Admin
          </Link>
          <span className="mx-2">/</span>
          <Link href="/admin/products" className="hover:text-leaf-400">
            Products
          </Link>
          <span className="mx-2">/</span>
          New
        </p>
        <h1 className="font-display text-3xl text-ink-50">New product</h1>
        <p className="text-ink-100/70">
          Create a catalogue item, upload photos, and kick off embedding for visual search.
        </p>
      </div>
      <AdminProductForm />
    </section>
  );
}
