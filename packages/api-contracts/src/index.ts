/**
 * Minimal shared API contracts for Visual Shop.
 * Keep in sync with FastAPI `/api/v1` stubs; generate OpenAPI clients later.
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
}

export interface VisualSearchResponse {
  results: VisualSearchResultItem[];
  query_ms?: number | null;
  message?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
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
