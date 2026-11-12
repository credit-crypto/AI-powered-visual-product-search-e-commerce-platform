"""S3-compatible object storage helpers (MinIO locally, S3 in production)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ObjectStorage(ABC):
    @abstractmethod
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes and return a public or signed URL."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object by key."""


class StubObjectStorage(ObjectStorage):
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        # TODO: Use boto3 against MinIO/S3 with settings from config.
        _ = (data, content_type)
        return f"s3://visual-shop/{key}"

    async def delete(self, key: str) -> None:
        # TODO: Delete from bucket.
        _ = key
