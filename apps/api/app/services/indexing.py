"""Helpers to enqueue (or run) embedding jobs for product images."""

from __future__ import annotations

import logging
import os
from uuid import UUID

from app.repositories import catalogue as catalogue_repo
from app.services.encoder import get_encoder
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


def index_product_image_sync(product_image_id: UUID) -> dict[str, str]:
    """Run the embedding pipeline inline (same logic as the Celery task)."""
    row = catalogue_repo.get_product_image(product_image_id)
    if row is None:
        raise ValueError(f"product_image {product_image_id} not found")

    catalogue_repo.set_product_image_status(product_image_id, "processing")
    try:
        storage = get_storage()
        image_bytes = storage.get_bytes(row["storage_key"])
        encoder = get_encoder()
        embedding = encoder.encode_image_sync(image_bytes)
        catalogue_repo.upsert_image_embedding(
            product_image_id=product_image_id,
            product_id=row["product_id"],
            embedding=embedding,
            model_name=encoder.model_name,
        )
        catalogue_repo.set_product_image_status(product_image_id, "ready")
        return {
            "product_image_id": str(product_image_id),
            "status": "ready",
            "model_name": encoder.model_name,
        }
    except Exception:
        catalogue_repo.set_product_image_status(product_image_id, "failed")
        raise


def enqueue_embedding_job(product_image_id: UUID) -> str:
    """Enqueue Celery job; fall back to sync indexing if broker unavailable or forced."""
    force_sync = os.getenv("INDEX_SYNC", "0") == "1"
    if not force_sync:
        try:
            from worker.tasks import generate_embedding_for_image

            async_result = generate_embedding_for_image.delay(str(product_image_id))
            return async_result.id
        except Exception as exc:
            logger.warning(
                "Celery enqueue failed (%s); indexing %s synchronously",
                exc,
                product_image_id,
            )

    result = index_product_image_sync(product_image_id)
    return f"sync:{result['product_image_id']}"
