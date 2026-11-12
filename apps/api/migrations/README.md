# Schema notes (MongoDB)

PostgreSQL + pgvector SQL files in this folder are **legacy** (pre-MongoDB migration).
The live schema is document collections created on demand; indexes are ensured at API
startup via `app.db.ensure_indexes()`.

## Collections

| Collection | Purpose |
| --- | --- |
| `categories` | Catalogue categories |
| `products` | Products |
| `product_variants` | SKUs / prices |
| `inventory` | Stock on hand / reserved |
| `product_images` | Image metadata + indexing status |
| `image_embeddings` | L2-normalized 768-d `embedding` float arrays + `model_name` |
| `carts` / `cart_items` | Guest carts |
| `orders` / `order_items` | Checkout |
| `payment_events` | Idempotent payment webhooks |
| `search_events` | Visual search analytics |

## Offline vector search

Embeddings are stored as plain float arrays. Query-time cosine similarity is computed
in Python with NumPy (dot product of L2-normalized vectors). Atlas Vector Search is
optional for larger catalogues and is **not** required for local/offline demos.
