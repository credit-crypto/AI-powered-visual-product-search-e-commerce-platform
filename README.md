# Visual Shop

AI-powered visual product search e-commerce platform. Customers upload or capture a product photo and discover similar items in your catalogue.

```
visual-shop/
├── apps/storefront/     # Next.js (web) + Capacitor (iOS/Android)
├── apps/api/            # FastAPI + Celery worker + seed script
├── packages/api-contracts/
├── infrastructure/      # docker-compose (Postgres/pgvector, Redis, MinIO, API, worker)
└── README.md
```

## Demo: visual search happy path

### 1. Start infrastructure

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

Services:

| Service | URL |
| --- | --- |
| API + docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| MinIO API / console | http://localhost:9000 / http://localhost:9001 (`minioadmin` / `minioadmin`) |
| Postgres | `localhost:5432` — `visualshop` / `visualshop` / `visualshop` |
| Redis | `localhost:6379` |

### 2. Seed a sample catalogue

```bash
docker compose -f infrastructure/docker-compose.yml --profile seed run --rm seed
```

Or from the host (with the same env as `.env.example`):

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. python -m scripts.seed_catalogue
```

This creates 8 synthetic products, uploads JPEGs to MinIO, and writes **768-d** embeddings into `image_embeddings` (inline by default so search works immediately).

### 3. Storefront

```bash
npm install
cp apps/storefront/.env.example apps/storefront/.env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev:storefront
```

Open http://localhost:3000/visual-search → upload any seeded-style image (or a photo of a similar colour/shape) → `/search/results` shows the top matches.

### 4. API-only smoke test

```bash
# after seed — reuse a product image from MinIO or a local JPEG
curl -s -F "file=@/path/to/query.jpg" -F "limit=20" \
  http://localhost:8000/api/v1/search/image | jq .
```

## Embeddings: perceptual (default) vs SigLIP2

| `EMBEDDING_BACKEND` | Model id stored in DB | When to use |
| --- | --- | --- |
| `perceptual` (default) | `visual-shop/perceptual-v1` | Local Docker demo / CI — CPU-only, no weight download. Colour + spatial features projected to **VECTOR(768)**, L2-normalized. Similar-looking seed images rank near each other. |
| `siglip2` | `google/siglip2-base-patch16-224` | Real visual encoder. Install `apps/api/requirements-ml.txt`, set the env var on **api** and **worker**, rebuild. First boot downloads weights (~1GB+). |

Indexing path (admin or seed):

1. Upload image → MinIO (`product_images`, status `pending`)
2. Celery `embeddings.generate_for_image` → preprocess → encode → upsert `image_embeddings` → status `ready`
3. Customer `POST /api/v1/search/image` encodes with the **same** backend/model name and runs pgvector cosine search (`<=>`), grouped by product, top 20.

If Celery/Redis is unavailable, the API falls back to **synchronous** indexing for that upload. Set `INDEX_SYNC=1` to force inline indexing.

### Storage backends

| `STORAGE_BACKEND` | Behaviour |
| --- | --- |
| `s3` (default in Compose) | MinIO / S3 via boto3. Public URLs use `S3_PUBLIC_ENDPOINT_URL` (e.g. `http://localhost:9000`). |
| `filesystem` | Local disk under `STORAGE_LOCAL_PATH`, served at `/media/*` (`MEDIA_PUBLIC_BASE`). Handy when MinIO isn’t running. |

## Capacitor + Next.js

| Mode | Command | Behaviour |
| --- | --- | --- |
| Web / SSR | `npm run dev:storefront` | Primary web path |
| Capacitor live | set `server.url` in `capacitor.config.ts` | WebView → Next host |
| Capacitor static | `npm run build:mobile` → `cap:sync` | `CAPACITOR=1` static export to `out/` |

Visual search uses `<input capture>` on web and `@capacitor/camera` when the native shell is present.

## Admin indexing API

```bash
# create product
curl -s -X POST http://localhost:8000/api/v1/admin/products \
  -H 'content-type: application/json' \
  -d '{"name":"Demo Hat","slug":"demo-hat","price_cents":2500}'

# upload image (queues Celery embedding job)
curl -s -X POST "http://localhost:8000/api/v1/admin/products/<PRODUCT_ID>/images" \
  -F "file=@./hat.jpg"
```

## Development notes

- Schema: `apps/api/migrations/001_catalogue_pgvector.sql` (applied on first Postgres boot)
- Optional ML deps: `apps/api/requirements-ml.txt`
- Cart / checkout / Auth.js remain stubs for a later milestone
