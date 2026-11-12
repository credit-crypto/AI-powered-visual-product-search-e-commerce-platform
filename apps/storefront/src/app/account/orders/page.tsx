import { OrdersView } from "@/components/orders-view";

export default function OrdersPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-3xl text-ink-50">Orders</h1>
      <p className="text-ink-100/70">
        Look up orders by the email used at checkout (auth stub for MVP).
      </p>
      <OrdersView />
    </section>
  );
}
