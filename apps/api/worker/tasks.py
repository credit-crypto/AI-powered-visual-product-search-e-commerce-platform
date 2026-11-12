"""Background tasks for catalogue image embedding.

Next milestone: download image from S3, preprocess, run SigLIP2, upsert
image_embeddings, mark product_images.status = ready.
"""

from __future__ import annotations

from worker.celery_app import celery_app


@celery_app.task(name="embeddings.generate_for_image")
def generate_embedding_for_image(product_image_id: str) -> dict[str, str]:
    # TODO: Load product_images row → fetch bytes from storage → encode → save vector.
    return {
        "product_image_id": product_image_id,
        "status": "stubbed",
        "message": "SigLIP2 embedding not implemented yet",
    }


@celery_app.task(name="embeddings.reindex_product")
def reindex_product(product_id: str) -> dict[str, str]:
    # TODO: Enqueue generate_embedding_for_image for each image of the product.
    return {
        "product_id": product_id,
        "status": "stubbed",
    }
