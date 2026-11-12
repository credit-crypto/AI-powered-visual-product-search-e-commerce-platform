"""Background tasks for catalogue image embedding."""

from __future__ import annotations

import logging
from uuid import UUID

from app.repositories import catalogue as catalogue_repo
from app.services.indexing import index_product_image_sync
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="embeddings.generate_for_image", bind=True, max_retries=3)
def generate_embedding_for_image(self, product_image_id: str) -> dict[str, str]:
    """Download image from storage → preprocess → encode → upsert embedding → ready."""
    try:
        return index_product_image_sync(UUID(product_image_id))
    except Exception as exc:
        logger.exception("Failed to index image %s", product_image_id)
        raise self.retry(exc=exc, countdown=5) from exc


@celery_app.task(name="embeddings.reindex_product")
def reindex_product(product_id: str) -> dict[str, object]:
    image_ids = catalogue_repo.list_product_image_ids(UUID(product_id))
    job_ids = [
        generate_embedding_for_image.delay(str(image_id)).id for image_id in image_ids
    ]
    return {
        "product_id": product_id,
        "status": "queued",
        "image_count": len(image_ids),
        "job_ids": job_ids,
    }
