/**
 * Shared API contracts for Visual Shop.
 * Keep in sync with FastAPI `/api/v1`.
 */

export interface ProductSummary {
  id: string;
  name: string;
  slug: string;
  price_cents: number;
  currency: string;
  thumbnail_url?: string | null;
  default_variant_id?: string | null;
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

export interface CartItem {
  variant_id: string;
  quantity: number;
  product_name?: string | null;
  unit_price_cents?: number | null;
  line_total_cents?: number | null;
}

export interface CartResponse {
  id: string;
  session_token: string;
  items: CartItem[];
  subtotal_cents: number;
  currency: string;
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

export interface OrderSummary {
  id: string;
  status: string;
  total_cents: number;
  currency: string;
  email?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  embedding_backend?: string;
  embedding_model?: string;
  payment_provider?: string;
}

export const API_V1_PREFIX = "/api/v1" as const;

export const routes = {
  health: "/health",
  products: `${API_V1_PREFIX}/products`,
  searchImage: `${API_V1_PREFIX}/search/image`,
  searchFeedback: `${API_V1_PREFIX}/search/feedback`,
  cart: `${API_V1_PREFIX}/cart`,
  checkoutSession: `${API_V1_PREFIX}/checkout/session`,
  paymentWebhook: `${API_V1_PREFIX}/webhooks/payments`,
  orders: `${API_V1_PREFIX}/orders`,
  adminProducts: `${API_V1_PREFIX}/admin/products`,
} as const;
