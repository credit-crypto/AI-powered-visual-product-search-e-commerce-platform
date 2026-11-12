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

export interface HealthResponse {
  status: string;
  service: string;
  embedding_backend?: string;
  embedding_model?: string;
}

export const API_V1_PREFIX = "/api/v1" as const;

export const routes = {
  health: "/health",
  products: `${API_V1_PREFIX}/products`,
  searchImage: `${API_V1_PREFIX}/search/image`,
  searchFeedback: `${API_V1_PREFIX}/search/feedback`,
  cart: `${API_V1_PREFIX}/cart`,
  checkout: `${API_V1_PREFIX}/orders/checkout`,
  adminProducts: `${API_V1_PREFIX}/admin/products`,
} as const;
