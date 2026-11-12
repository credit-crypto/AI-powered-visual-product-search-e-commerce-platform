from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.repositories import catalogue as catalogue_repo
from app.services.indexing import enqueue_embedding_job
from app.services.preprocess import InvalidImageError, load_and_validate_image
from app.services.storage import build_product_image_key, get_storage
from worker.tasks import reindex_product as reindex_product_task

router = APIRouter(prefix="/admin", tags=["admin"])


def _indexing_status(
    *,
    image_count: int,
    ready_count: int,
    pending_count: int,
    failed_count: int,
    embedded_count: int,
) -> str:
    if image_count == 0:
        return "no_images"
    if failed_count > 0 and ready_count + pending_count == 0:
        return "failed"
    if failed_count > 0:
        return "partial_failed"
    if pending_count > 0 or embedded_count < image_count:
        if ready_count == 0 and embedded_count == 0:
            return "pending"
        return "indexing"
    if ready_count >= image_count and embedded_count >= image_count:
        return "ready"
    return "indexing"


class CreateProductRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None
    category_id: UUID | None = None
    price_cents: int = Field(ge=0)
    currency: str = "USD"
    sku: str | None = None
    stock_qty: int = Field(default=25, ge=0)


class CreateProductResponse(BaseModel):
    id: UUID
    status: str = "created"
    slug: str | None = None
    sku: str | None = None


class EnqueueEmbeddingResponse(BaseModel):
    job_id: str
    status: str = "queued"
    product_image_id: UUID | None = None
    url: str | None = None


class AdminProductImage(BaseModel):
    id: UUID
    url: str
    status: str
    is_primary: bool = False
    width: int | None = None
    height: int | None = None
    has_embedding: bool = False
    position: int = 0


class AdminProductSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    status: str
    price_cents: int
    currency: str = "USD"
    default_sku: str | None = None
    stock_qty: int = 0
    thumbnail_url: str | None = None
    image_count: int = 0
    ready_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    embedded_count: int = 0
    indexing_status: str


class AdminProductDetail(AdminProductSummary):
    images: list[AdminProductImage] = Field(default_factory=list)


def _to_summary(row: dict) -> AdminProductSummary:
    image_count = int(row.get("image_count") or 0)
    ready_count = int(row.get("ready_count") or 0)
    pending_count = int(row.get("pending_count") or 0)
    failed_count = int(row.get("failed_count") or 0)
    embedded_count = int(row.get("embedded_count") or 0)
    return AdminProductSummary(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        description=row.get("description"),
        status=row.get("status") or "active",
        price_cents=int(row.get("price_cents") or 0),
        currency=row.get("currency") or "USD",
        default_sku=row.get("default_sku"),
        stock_qty=int(row.get("stock_qty") or 0),
        thumbnail_url=row.get("thumbnail_url"),
        image_count=image_count,
        ready_count=ready_count,
        pending_count=pending_count,
        failed_count=failed_count,
        embedded_count=embedded_count,
        indexing_status=_indexing_status(
            image_count=image_count,
            ready_count=ready_count,
            pending_count=pending_count,
            failed_count=failed_count,
            embedded_count=embedded_count,
        ),
    )


@router.get("/products", response_model=list[AdminProductSummary])
async def list_admin_products(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AdminProductSummary]:
    # TODO: require admin auth / RBAC.
    rows = catalogue_repo.list_admin_products(q=q, limit=limit, offset=offset)
    return [_to_summary(row) for row in rows]


@router.get("/products/{product_id}", response_model=AdminProductDetail)
async def get_admin_product(product_id: UUID) -> AdminProductDetail:
    # TODO: require admin auth / RBAC.
    row = catalogue_repo.get_admin_product(product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    summary = _to_summary(row)
    images = [
        AdminProductImage(
            id=img["id"],
            url=img["url"],
            status=img.get("status") or "pending",
            is_primary=bool(img.get("is_primary")),
            width=img.get("width"),
            height=img.get("height"),
            has_embedding=bool(img.get("has_embedding")),
            position=int(img.get("position") or 0),
        )
        for img in row.get("images") or []
    ]
    return AdminProductDetail(**summary.model_dump(), images=images)


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
            sku=body.sku,
            stock_qty=body.stock_qty,
            status="active",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateProductResponse(
        id=product["id"],
        status=product["status"],
        slug=product.get("slug"),
        sku=product.get("sku"),
    )


@router.post("/products/{product_id}/images", response_model=EnqueueEmbeddingResponse)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
) -> EnqueueEmbeddingResponse:
    # TODO: require admin auth / RBAC.
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

    existing = catalogue_repo.count_product_images(product_id)
    row = catalogue_repo.insert_product_image(
        product_id=product_id,
        storage_key=key,
        url=url,
        width=image.width,
        height=image.height,
        position=existing,
        is_primary=existing == 0,
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
    # TODO: require admin auth / RBAC.
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
