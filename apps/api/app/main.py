from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin, cart, checkout, orders, products, search, webhooks
from app.core.config import get_settings
from app.db import ensure_indexes
from app.services.encoder import get_encoder

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Token"],
)

app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(search.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(cart.router, prefix=settings.api_v1_prefix)
app.include_router(checkout.router, prefix=settings.api_v1_prefix)
app.include_router(orders.router, prefix=settings.api_v1_prefix)
app.include_router(webhooks.router, prefix=settings.api_v1_prefix)

if settings.storage_backend.lower() in {"filesystem", "local", "file"}:
    media_root = Path(settings.storage_local_path)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")


@app.on_event("startup")
def on_startup() -> None:
    ensure_indexes()
    get_encoder()


@app.get("/health")
async def health() -> dict[str, str]:
    encoder = get_encoder()
    return {
        "status": "ok",
        "service": settings.app_name,
        "database": "mongodb",
        "embedding_backend": settings.embedding_backend,
        "embedding_model": encoder.model_name,
        "storage_backend": settings.storage_backend,
        "payment_provider": settings.payment_provider,
    }
