from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Visual Shop API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True
    api_public_base: str = "http://localhost:8000"
    storefront_public_base: str = "http://localhost:3000"

    # MongoDB (replaces PostgreSQL + pgvector). Local/offline default — no Atlas required.
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db: str = "visualshop"
    redis_url: str = "redis://localhost:6379/0"

    # Object storage: "s3" (MinIO/S3) or "filesystem" (local demo / no MinIO)
    storage_backend: str = "s3"
    storage_local_path: str = "/tmp/visual-shop-storage"
    media_public_base: str = "http://localhost:8000/media"

    # S3-compatible storage (MinIO locally)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "visual-shop"
    s3_region: str = "us-east-1"

    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"

    # Embedding backend: "perceptual" (CPU-friendly demo default) or "siglip2"
    embedding_backend: str = "perceptual"
    embedding_model_name: str = "google/siglip2-base-patch16-224"
    embedding_dim: int = 768
    max_upload_bytes: int = 8 * 1024 * 1024
    min_image_side: int = 32
    max_image_side: int = 4096
    search_default_limit: int = 20

    # Payments: "stub" (default demo) or "stripe"
    payment_provider: str = "stub"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stub_payment_secret: str = "visual-shop-stub-secret"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def public_s3_base(self) -> str:
        return (self.s3_public_endpoint_url or self.s3_endpoint_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
