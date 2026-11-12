import { AdminProductDetailView } from "@/components/admin-product-detail";

export default async function AdminProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <section>
      <AdminProductDetailView productId={id} />
    </section>
  );
}
