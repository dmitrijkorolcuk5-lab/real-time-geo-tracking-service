from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import get_location_ingestion_service
from app.schemas.location import LocationBatchIngest, LocationBatchResult, LocationIngest
from app.services.location_ingestion_service import LocationIngestionService, LocationQueueFull

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=LocationBatchResult)
async def ingest_location(
    payload: LocationIngest,
    user_id: str = Header(..., alias="X-User-Id"),
    service: LocationIngestionService = Depends(get_location_ingestion_service),
) -> LocationBatchResult:
    try:
        await service.enqueue(user_id=user_id, payload=payload)
        return LocationBatchResult(accepted=1, rejected=0)
    except LocationQueueFull:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ingestion queue is full")


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED, response_model=LocationBatchResult)
async def ingest_locations_batch(
    payload: LocationBatchIngest,
    user_id: str = Header(..., alias="X-User-Id"),
    service: LocationIngestionService = Depends(get_location_ingestion_service),
) -> LocationBatchResult:
    accepted, rejected = await service.enqueue_batch(user_id=user_id, payloads=payload.locations)
    return LocationBatchResult(accepted=accepted, rejected=rejected)

