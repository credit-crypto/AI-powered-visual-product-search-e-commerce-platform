import { CartView } from "@/components/cart-view";

export default function CartPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Cart</h1>
      <p className="text-ink-100/70">Guest cart tied to your browser session token.</p>
      <CartView />
    </section>
  );
}
