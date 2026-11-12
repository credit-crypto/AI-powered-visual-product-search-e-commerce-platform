from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Visual Shop API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://visualshop:visualshop@localhost:5432/visualshop"
    database_url_sync: str = "postgresql://visualshop:visualshop@localhost:5432/visualshop"
    redis_url: str = "redis://localhost:6379/0"

    # S3-compatible storage (MinIO locally)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "visual-shop"
    s3_region: str = "us-east-1"

    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
