import { ProductDetailView } from "@/components/product-detail";

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return (
    <section className="space-y-6">
      <ProductDetailView slug={slug} />
    </section>
  );
}
