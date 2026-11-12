from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

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


@router.post("/products", response_model=CreateProductResponse)
async def create_product(body: CreateProductRequest) -> CreateProductResponse:
    # TODO: Insert product + default variant; require admin auth.
    raise HTTPException(
        status_code=501,
        detail=f"create_product not implemented yet (slug={body.slug})",
    )


@router.post("/products/{product_id}/images", response_model=EnqueueEmbeddingResponse)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
) -> EnqueueEmbeddingResponse:
    # TODO: Store image in S3/MinIO, insert product_images row, enqueue Celery embedding job.
    _ = (product_id, file)
    return EnqueueEmbeddingResponse(job_id="stub-job", status="queued")


@router.post("/products/{product_id}/reindex", response_model=EnqueueEmbeddingResponse)
async def reindex_product(product_id: UUID) -> EnqueueEmbeddingResponse:
    # TODO: Enqueue embedding jobs for all product images.
    return EnqueueEmbeddingResponse(job_id=f"reindex-{product_id}", status="queued")
