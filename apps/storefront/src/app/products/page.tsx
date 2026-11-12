export default function ProductsPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Products</h1>
      <p className="text-ink-100/70">
        Catalogue listing stub. Wire to <code className="text-leaf-400">GET /api/v1/products</code>{" "}
        in a later milestone.
      </p>
      <ul className="divide-y divide-white/10 border border-white/10">
        <li className="px-4 py-3 text-sm text-ink-100/50">No products yet</li>
      </ul>
    </section>
  );
}
