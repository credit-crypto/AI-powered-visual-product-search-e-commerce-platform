from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.search import SearchFeedbackRequest, VisualSearchResponse
from app.services.encoder import get_encoder
from app.services.search import get_search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/image", response_model=VisualSearchResponse)
async def search_by_image(
    file: UploadFile = File(...),
    limit: int = Form(default=20),
    category_id: UUID | None = Form(default=None),
) -> VisualSearchResponse:
    """Upload an image and return visually similar products.

    Foundation stub: encoder + search interfaces are wired but do not run
    SigLIP2 or pgvector queries yet.
    """
    # TODO: Validate image bytes/dimensions; rate-limit; optional crop coords.
    content = await file.read()
    encoder = get_encoder()
    embedding = await encoder.encode_image(content)

    search_service = get_search_service()
    results = await search_service.similar_products(
        embedding=embedding,
        limit=limit,
        category_id=category_id,
    )
    return VisualSearchResponse(
        results=results,
        message="Stub search — SigLIP2 + pgvector not implemented yet",
    )


@router.post("/feedback")
async def search_feedback(body: SearchFeedbackRequest) -> dict[str, str]:
    # TODO: Persist feedback to search_events / analytics tables.
    _ = body
    return {"status": "accepted"}
