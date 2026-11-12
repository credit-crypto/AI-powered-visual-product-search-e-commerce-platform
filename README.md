# Visual Shop

AI-powered visual product search e-commerce platform. Customers upload or capture a product photo and discover similar items in your catalogue.

```
visual-shop/
├── apps/storefront/     # Next.js (web) + Capacitor (iOS/Android)
├── apps/api/            # FastAPI + Celery worker + seed script
├── packages/api-contracts/
├── infrastructure/      # docker-compose (MongoDB, Redis, MinIO, API, worker)
└── README.md
```

**Stack notes:** catalogue + carts/orders live in **MongoDB**. Default embeddings use the offline **perceptual stub** (no HuggingFace/SigLIP2 download). Visual search scores L2-normalized 768-d vectors with in-process cosine similarity (Atlas Vector Search optional later).

## Demo: offline happy path

### 1. Start infrastructure

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

| Service | URL |
| --- | --- |
| API + docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| MinIO API / console | http://localhost:9000 / http://localhost:9001 |
| MongoDB | `mongodb://localhost:27017` → db `visualshop` |
| Redis | `localhost:6379` |

Local/agent demo without Docker: run MongoDB + Redis locally, set `STORAGE_BACKEND=filesystem`, `EMBEDDING_BACKEND=perceptual`, `INDEX_SYNC=1`.

### 2. Seed a sample catalogue

```bash
docker compose -f infrastructure/docker-compose.yml --profile seed run --rm seed
```

Or from the host:

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env   # MONGODB_URI, EMBEDDING_BACKEND=perceptual
PYTHONPATH=. python -m scripts.seed_catalogue
```

Creates **~100** products (`SEED_COUNT=N` to override), stores JPEGs, and writes **768-d** perceptual embeddings into `image_embeddings`.

### 3. Storefront

```bash
npm install
cp apps/storefront/.env.example apps/storefront/.env.local
npm run dev:storefront
```

Open http://localhost:3000/products → camera/image button → `/search/results`.

Admin upload UI (MVP, no auth): http://localhost:3000/admin

### 4. Cart + checkout (stub payment)

1. http://localhost:3000/products → add to cart  
2. http://localhost:3000/cart → checkout  
3. Stub pay → `/account/orders?paid=1`

Guest cart uses `X-Session-Token` (storefront `localStorage`).

### 5. API smoke test

```bash
curl -s -F "file=@/path/to/query.jpg" -F "limit=20" \
  http://localhost:8000/api/v1/search/image | jq .
```

## Embeddings: perceptual (default, offline) vs SigLIP2 (online opt-in)

| `EMBEDDING_BACKEND` | Model id | When |
| --- | --- | --- |
| `perceptual` (**default**) | `visual-shop/perceptual-v1` | Fully offline / CI — no weight download |
| `siglip2` | `google/siglip2-base-patch16-224` | Online only |

**Opt into SigLIP2 when online:**

```bash
cd apps/api
pip install -r requirements-ml.txt
# on api + worker:
export EMBEDDING_BACKEND=siglip2
# re-seed or reindex so embeddings match the new model_name
PYTHONPATH=. python -m scripts.seed_catalogue
```

Search only compares embeddings with the **same** `model_name` as the active encoder.

### How offline vectors are queried

1. Query image → perceptual encoder → L2-normalized 768-d float list  
2. Load `image_embeddings` for that `model_name` from MongoDB  
3. Cosine score = dot product of unit vectors (NumPy)  
4. Keep best image per product, return top N  

No Atlas cluster is required for this path.

### Storage

| `STORAGE_BACKEND` | Behaviour |
| --- | --- |
| `s3` | MinIO / S3 |
| `filesystem` | Disk under `STORAGE_LOCAL_PATH`, served at `/media/*` |

## Capacitor + Next.js

| Mode | Command |
| --- | --- |
| Web SSR | `npm run dev:storefront` / `build:web` |
| Mobile static | `npm run mobile:prepare` |

See `apps/storefront/next.config.ts` for same-origin API/media rewrites (Try Live friendly).
