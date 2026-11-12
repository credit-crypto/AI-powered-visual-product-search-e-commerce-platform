import time
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.repositories import catalogue as catalogue_repo
from app.schemas.search import SearchFeedbackRequest, VisualSearchResponse
from app.services.encoder import get_encoder
from app.services.preprocess import InvalidImageError, load_and_validate_image
from app.services.search import get_search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/image", response_model=VisualSearchResponse)
async def search_by_image(
    file: UploadFile = File(...),
    limit: int | None = Form(default=None),
    category_id: UUID | None = Form(default=None),
) -> VisualSearchResponse:
    """Upload an image and return the top visually similar products.

    Uses the same embedding backend as catalogue indexing (EMBEDDING_BACKEND).
    Customer uploads are encoded in-process and not retained.
    """
    settings = get_settings()
    result_limit = limit or settings.search_default_limit
    result_limit = max(1, min(result_limit, 50))

    content = await file.read()
    try:
        load_and_validate_image(content)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started = time.perf_counter()
    encoder = get_encoder()
    embedding = await encoder.encode_image(content)
    search_service = get_search_service()
    results = await search_service.similar_products(
        embedding=embedding,
        limit=result_limit,
        category_id=category_id,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    event_id = catalogue_repo.record_search_event(
        result_count=len(results),
        latency_ms=elapsed_ms,
        metadata={
            "model_name": encoder.model_name,
            "limit": result_limit,
            "category_id": str(category_id) if category_id else None,
        },
    )

    return VisualSearchResponse(
        results=results,
        query_ms=elapsed_ms,
        model_name=encoder.model_name,
        search_event_id=event_id,
        message=None if results else "No indexed products matched this image yet",
    )


@router.post("/feedback")
async def search_feedback(body: SearchFeedbackRequest) -> dict[str, str]:
    # TODO: Persist feedback against search_events for quality metrics.
    _ = body
    return {"status": "accepted"}
