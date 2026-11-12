# Visual Shop

AI-powered visual product search e-commerce platform. Customers upload or capture a product photo and discover similar items in your catalogue.

Monorepo layout:

```
visual-shop/
├── apps/storefront/     # Next.js (web) + Capacitor (iOS/Android)
├── apps/api/            # FastAPI + Celery worker stubs
├── packages/api-contracts/
├── infrastructure/      # docker-compose (Postgres/pgvector, Redis, MinIO, API, worker)
└── README.md
```

## Quick start

### Infrastructure (API + DB + Redis + MinIO + worker)

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

- API: http://localhost:8000 — docs at `/docs`, health at `/health`
- Postgres (pgvector): `localhost:5432` — user/pass/db `visualshop`
- Redis: `localhost:6379`
- MinIO (S3-compatible): http://localhost:9000 — console `:9001` (`minioadmin` / `minioadmin`)

The starter SQL migration (`apps/api/migrations/001_catalogue_pgvector.sql`) runs automatically on first DB boot.

### Storefront (web)

```bash
npm install
npm run dev:storefront
```

Open http://localhost:3000. Stub routes: `/`, `/products`, `/visual-search`, `/search/results`, `/cart`, `/admin`.

### API locally (without Docker)

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Celery worker stub:

```bash
cd apps/api
celery -A worker.celery_app.celery_app worker --loglevel=info
```

## Capacitor + Next.js (web and mobile in parallel)

**Decision:** keep one Next.js App Router codebase for both surfaces.

| Mode | Command | Behaviour |
| --- | --- | --- |
| Web / SSR | `npm run dev:storefront` or `build:web` | Normal Next.js (SSR/SSG). Primary web path. |
| Capacitor live | set `server.url` in `capacitor.config.ts` | Native WebView loads the running Next server (best DX while iterating). |
| Capacitor static | `npm run build:mobile` → `cap:sync` | `CAPACITOR=1` enables `output: "export"` into `out/`; Capacitor `webDir` is `out`. |

Mobile prepare (static shell):

```bash
cd apps/storefront
npm run mobile:prepare          # static export + cap sync
# then open native projects (after first `npx cap add ios|android`):
npm run cap:open:ios
npm run cap:open:android
```

First-time native projects (run once on a machine with Xcode / Android Studio):

```bash
cd apps/storefront
npx cap add ios
npx cap add android
```

`ios/` and `android/` are gitignored until you choose to commit them.

**Notes**

- Static export cannot use server-only Next features inside the WebView; prefer live `server.url` during development if you need SSR APIs.
- Camera capture for visual search uses Capacitor Camera on device; the web stub uses `<input type="file" capture>`.

## What’s stubbed (next milestone)

- SigLIP2 encoder (`app/services/encoder.py`) and pgvector search (`app/services/search.py`)
- Celery embedding jobs (`worker/tasks.py`)
- Admin image upload → S3/MinIO → index pipeline
- Full cart / checkout / Auth.js

## API surface (foundation)

| Method | Path | Status |
| --- | --- | --- |
| GET | `/health` | live |
| GET | `/api/v1/products` | stub |
| POST | `/api/v1/search/image` | stub (wired to encoder/search interfaces) |
| POST | `/api/v1/search/feedback` | stub |
| `/api/v1/admin/*` | product + image + reindex | stub |
| `/api/v1/cart/*` | cart | stub |
| `/api/v1/orders/*` | checkout + webhook | stub |
