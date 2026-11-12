import { CheckoutForm } from "@/components/checkout-form";

export default function CheckoutPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Checkout</h1>
      <p className="text-ink-100/70">
        Prices and stock are recalculated on the server before payment starts.
      </p>
      <CheckoutForm />
    </section>
  );
}
