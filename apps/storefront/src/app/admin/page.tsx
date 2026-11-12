export default function AdminPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Admin</h1>
      <p className="text-ink-100/70">
        Admin stub for catalogue management and embedding reindex jobs. Auth + RBAC come later.
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink-100/60">
        <li>Create products — POST /api/v1/admin/products</li>
        <li>Upload images — POST /api/v1/admin/products/:id/images</li>
        <li>Reindex embeddings — POST /api/v1/admin/products/:id/reindex</li>
      </ul>
    </section>
  );
}
