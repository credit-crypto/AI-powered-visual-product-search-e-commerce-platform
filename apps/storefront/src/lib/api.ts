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

export async function searchByImage(file: Blob, fileName = "query.jpg"): Promise<VisualSearchResponse> {
  const body = new FormData();
  body.append("file", file, fileName);
  body.append("limit", "20");

  const response = await fetch(`${getApiBaseUrl()}/api/v1/search/image`, {
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
}

export async function listProducts(): Promise<ProductSummary[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/products`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load products (${response.status})`);
  }
  return response.json() as Promise<ProductSummary[]>;
}
