import { ProductsList } from "@/components/products-list";

export default function ProductsPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Products</h1>
      <p className="text-ink-100/70">Active catalogue items from the API.</p>
      <ProductsList />
    </section>
  );
}
