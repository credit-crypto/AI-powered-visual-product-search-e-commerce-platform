"""Object storage: S3/MinIO (default) or local filesystem for agent/CI demos."""

from __future__ import annotations

import logging
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.client import Config

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ObjectStorage(ABC):
    @abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes and return a publicly reachable URL."""

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        """Download object bytes by key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an object by key."""

    def public_url_for(self, key: str) -> str:
        settings = get_settings()
        return f"{settings.public_s3_base}/{settings.s3_bucket}/{key}"


class S3ObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return self.public_url_for(key)

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class FilesystemObjectStorage(ObjectStorage):
    """Stores objects under STORAGE_LOCAL_PATH and serves via /media/{key}."""

    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.storage_local_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._public_base = settings.media_public_base.rstrip("/")

    def _path_for(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValueError("invalid storage key")
        return path

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        _ = content_type
        return f"{self._public_base}/{key}"

    def get_bytes(self, key: str) -> bytes:
        return self._path_for(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def build_product_image_key(product_id: str, filename: str | None = None) -> str:
    suffix = (filename or "image.bin").rsplit(".", 1)
    ext = suffix[-1].lower() if len(suffix) == 2 else "bin"
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        ext = "jpg"
    return f"products/{product_id}/{uuid4().hex}.{ext}"


@lru_cache
def get_storage() -> ObjectStorage:
    settings = get_settings()
    backend = (settings.storage_backend or "s3").strip().lower()
    if backend in {"filesystem", "local", "file"}:
        logger.info("Using filesystem object storage at %s", settings.storage_local_path)
        return FilesystemObjectStorage()
    return S3ObjectStorage()


def reset_storage() -> None:
    get_storage.cache_clear()
