import { captureSessionToken, sessionHeaders } from "@/lib/session";

/**
 * Browser calls go same-origin (Next rewrites → API) so Try Live / public
 * tunnels work. Native Capacitor still needs an absolute API host.
 * Server-side / SSR uses the internal API URL.
 */
export function getApiBaseUrl(): string {
  const configured =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_URL?.replace(/\/$/, "") || configured
    );
  }

  try {
    const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } })
      .Capacitor;
    if (cap?.isNativePlatform?.()) {
      return configured;
    }
  } catch {
    /* ignore */
  }

  // Same-origin via next.config rewrites (/api/v1, /media).
  return "";
}

/** Rewrite localhost API media URLs to same-origin paths for Try Live. */
export function browserAssetUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("/")) return url;
  try {
    const parsed = new URL(url);
    const localHost =
      parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
    if (localHost && (parsed.port === "8000" || parsed.port === "3000" || parsed.port === "")) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    return url;
  }
  return url;
}

export interface VisualSearchResultItem {
  product_id: string;
  score: number;
  image_id?: string | null;
  name?: string | null;
  slug?: string | null;
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

export interface ProductDetail extends ProductSummary {
  description?: string | null;
  category_id?: string | null;
  image_urls?: string[];
  default_sku?: string | null;
}

export async function listProducts(q?: string, limit = 100): Promise<ProductSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (q?.trim()) params.set("q", q.trim());
  const response = await apiFetch(`/api/v1/products?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load products (${response.status})`);
  }
  return response.json() as Promise<ProductSummary[]>;
}

export async function getProductBySlug(slug: string): Promise<ProductDetail> {
  const response = await apiFetch(`/api/v1/products/slug/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Product not found (${response.status})`);
  }
  return response.json() as Promise<ProductDetail>;
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

/* —— Admin catalogue (MVP: no auth) —— */

export interface AdminProductImage {
  id: string;
  url: string;
  status: string;
  is_primary: boolean;
  width?: number | null;
  height?: number | null;
  has_embedding: boolean;
  position: number;
}

export interface AdminProductSummary {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  status: string;
  price_cents: number;
  currency: string;
  default_sku?: string | null;
  stock_qty: number;
  thumbnail_url?: string | null;
  image_count: number;
  ready_count: number;
  pending_count: number;
  failed_count: number;
  embedded_count: number;
  indexing_status: string;
}

export interface AdminProductDetail extends AdminProductSummary {
  images: AdminProductImage[];
}

export interface CreateAdminProductInput {
  name: string;
  slug: string;
  description?: string;
  price_cents: number;
  currency?: string;
  sku?: string;
  stock_qty?: number;
}

async function readError(response: Response, fallback: string): Promise<string> {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (parsed.detail != null) return JSON.stringify(parsed.detail);
  } catch {
    /* plain text */
  }
  return text || fallback;
}

export async function listAdminProducts(q?: string): Promise<AdminProductSummary[]> {
  const params = new URLSearchParams({ limit: "100" });
  if (q?.trim()) params.set("q", q.trim());
  const response = await apiFetch(`/api/v1/admin/products?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response, "Failed to load admin products"));
  return response.json() as Promise<AdminProductSummary[]>;
}

export async function getAdminProduct(productId: string): Promise<AdminProductDetail> {
  const response = await apiFetch(`/api/v1/admin/products/${productId}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response, "Product not found"));
  return response.json() as Promise<AdminProductDetail>;
}

export async function createAdminProduct(
  input: CreateAdminProductInput,
): Promise<{ id: string; status: string; slug?: string; sku?: string }> {
  const response = await apiFetch("/api/v1/admin/products", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await readError(response, "Create product failed"));
  return response.json();
}

export async function uploadAdminProductImage(
  productId: string,
  file: Blob,
  fileName: string,
): Promise<{ job_id: string; status: string; product_image_id?: string; url?: string }> {
  const body = new FormData();
  body.append("file", file, fileName);
  const response = await apiFetch(`/api/v1/admin/products/${productId}/images`, {
    method: "POST",
    body,
  });
  if (!response.ok) throw new Error(await readError(response, "Image upload failed"));
  return response.json();
}

export async function reindexAdminProduct(
  productId: string,
): Promise<{ job_id: string; status: string }> {
  const response = await apiFetch(`/api/v1/admin/products/${productId}/reindex`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(await readError(response, "Reindex failed"));
  return response.json();
}

export function slugifyProductName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function indexingStatusLabel(status: string): string {
  switch (status) {
    case "ready":
      return "Indexed";
    case "pending":
      return "Pending";
    case "indexing":
      return "Indexing";
    case "failed":
      return "Failed";
    case "partial_failed":
      return "Partial failure";
    case "no_images":
      return "No images";
    default:
      return status;
  }
}
