from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.repositories import catalogue as catalogue_repo
from app.services.indexing import enqueue_embedding_job
from app.services.preprocess import InvalidImageError, load_and_validate_image
from app.services.storage import build_product_image_key, get_storage
from worker.tasks import reindex_product as reindex_product_task

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateProductRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None
    category_id: UUID | None = None
    price_cents: int = Field(ge=0)
    currency: str = "USD"


class CreateProductResponse(BaseModel):
    id: UUID
    status: str = "created"


class EnqueueEmbeddingResponse(BaseModel):
    job_id: str
    status: str = "queued"
    product_image_id: UUID | None = None
    url: str | None = None


@router.post("/products", response_model=CreateProductResponse)
async def create_product(body: CreateProductRequest) -> CreateProductResponse:
    # TODO: require admin auth / RBAC.
    try:
        product = catalogue_repo.create_product(
            name=body.name,
            slug=body.slug,
            description=body.description,
            category_id=body.category_id,
            price_cents=body.price_cents,
            currency=body.currency,
            status="active",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateProductResponse(id=product["id"], status=product["status"])


@router.post("/products/{product_id}/images", response_model=EnqueueEmbeddingResponse)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
) -> EnqueueEmbeddingResponse:
    product = catalogue_repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    try:
        image = load_and_validate_image(content)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content_type = file.content_type or "image/jpeg"
    key = build_product_image_key(str(product_id), file.filename)
    storage = get_storage()
    url = storage.put_bytes(key, content, content_type)

    row = catalogue_repo.insert_product_image(
        product_id=product_id,
        storage_key=key,
        url=url,
        width=image.width,
        height=image.height,
        is_primary=True,
    )
    job_id = enqueue_embedding_job(row["id"])
    status = "ready" if job_id.startswith("sync:") else "queued"
    return EnqueueEmbeddingResponse(
        job_id=job_id,
        status=status,
        product_image_id=row["id"],
        url=url,
    )


@router.post("/products/{product_id}/reindex", response_model=EnqueueEmbeddingResponse)
async def reindex_product(product_id: UUID) -> EnqueueEmbeddingResponse:
    product = catalogue_repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        async_result = reindex_product_task.delay(str(product_id))
        return EnqueueEmbeddingResponse(job_id=async_result.id, status="queued")
    except Exception:
        image_ids = catalogue_repo.list_product_image_ids(product_id)
        for image_id in image_ids:
            enqueue_embedding_job(image_id)
        return EnqueueEmbeddingResponse(
            job_id=f"sync-reindex:{product_id}",
            status="ready" if image_ids else "queued",
        )
