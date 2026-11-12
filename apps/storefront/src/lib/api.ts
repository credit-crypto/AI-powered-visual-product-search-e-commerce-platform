import { captureSessionToken, sessionHeaders } from "@/lib/session";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
}

export interface VisualSearchResultItem {
  product_id: string;
  score: number;
  image_id?: string | null;
  name?: string | null;
  thumbnail_url?: string | null;
  price_cents?: number | null;
  currency?: string | null;
}

export interface VisualSearchResponse {
  results: VisualSearchResultItem[];
  query_ms?: number | null;
  model_name?: string | null;
  search_event_id?: string | null;
  message?: string | null;
}

export const SEARCH_RESULTS_KEY = "visual-shop:last-search";

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const session = sessionHeaders();
  Object.entries(session).forEach(([k, v]) => headers.set(k, v));
  const response = await fetch(`${getApiBaseUrl()}${path}`, { ...init, headers });
  captureSessionToken(response);
  return response;
}

export async function searchByImage(file: Blob, fileName = "query.jpg"): Promise<VisualSearchResponse> {
  const body = new FormData();
  body.append("file", file, fileName);
  body.append("limit", "20");

  const response = await apiFetch("/api/v1/search/image", {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Search failed (${response.status})`);
  }

  return response.json() as Promise<VisualSearchResponse>;
}

export interface ProductSummary {
  id: string;
  name: string;
  slug: string;
  price_cents: number;
  currency: string;
  thumbnail_url?: string | null;
  default_variant_id?: string | null;
}

export async function listProducts(): Promise<ProductSummary[]> {
  const response = await apiFetch("/api/v1/products", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load products (${response.status})`);
  }
  return response.json() as Promise<ProductSummary[]>;
}

export interface CartItem {
  cart_item_id?: string;
  variant_id: string;
  product_id?: string | null;
  quantity: number;
  product_name?: string | null;
  product_slug?: string | null;
  sku?: string | null;
  unit_price_cents?: number | null;
  currency?: string;
  thumbnail_url?: string | null;
  available_qty?: number | null;
  line_total_cents?: number | null;
}

export interface CartResponse {
  id: string;
  session_token: string;
  status: string;
  items: CartItem[];
  subtotal_cents: number;
  currency: string;
}

export async function getCart(): Promise<CartResponse> {
  const response = await apiFetch("/api/v1/cart");
  if (!response.ok) throw new Error(`Failed to load cart (${response.status})`);
  return response.json() as Promise<CartResponse>;
}

export async function addToCart(variantId: string, quantity = 1): Promise<CartResponse> {
  const response = await apiFetch("/api/v1/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variant_id: variantId, quantity }),
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Add to cart failed");
  }
  return response.json() as Promise<CartResponse>;
}

export async function updateCartItem(variantId: string, quantity: number): Promise<CartResponse> {
  const response = await apiFetch(`/api/v1/cart/items/${variantId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quantity }),
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Update cart failed");
  }
  return response.json() as Promise<CartResponse>;
}

export async function removeCartItem(variantId: string): Promise<CartResponse> {
  const response = await apiFetch(`/api/v1/cart/items/${variantId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Remove from cart failed");
  }
  return response.json() as Promise<CartResponse>;
}

export interface CheckoutSessionResponse {
  order_id: string;
  status: string;
  total_cents: number;
  currency: string;
  payment_provider: string;
  checkout_session_id: string;
  payment_url: string;
}

export async function createCheckoutSession(email: string): Promise<CheckoutSessionResponse> {
  const successUrl = `${window.location.origin}/account/orders?paid=1`;
  const cancelUrl = `${window.location.origin}/checkout?cancelled=1`;
  const response = await apiFetch("/api/v1/checkout/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      success_url: successUrl,
      cancel_url: cancelUrl,
    }),
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Checkout failed");
  }
  return response.json() as Promise<CheckoutSessionResponse>;
}

export interface OrderSummary {
  id: string;
  status: string;
  total_cents: number;
  currency: string;
  email?: string | null;
  created_at?: string | null;
  items?: Array<{
    variant_id: string;
    product_name?: string | null;
    sku?: string | null;
    quantity: number;
    unit_price_cents: number;
    line_total_cents?: number | null;
  }>;
}

export async function listOrders(email: string): Promise<OrderSummary[]> {
  const response = await apiFetch(`/api/v1/orders?email=${encodeURIComponent(email)}`);
  if (!response.ok) throw new Error(`Failed to load orders (${response.status})`);
  return response.json() as Promise<OrderSummary[]>;
}

export async function getOrder(orderId: string): Promise<OrderSummary> {
  const response = await apiFetch(`/api/v1/orders/${orderId}`);
  if (!response.ok) throw new Error(`Failed to load order (${response.status})`);
  return response.json() as Promise<OrderSummary>;
}

export function formatMoney(cents: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
  } catch {
    return `$${(cents / 100).toFixed(2)}`;
  }
}
