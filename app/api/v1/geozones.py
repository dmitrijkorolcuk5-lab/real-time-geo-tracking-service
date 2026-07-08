from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_geozone_service, get_session
from app.schemas.geozone import GeozoneCreate, GeozoneRead, GeozoneUpdate
from app.services.geozone_service import GeozoneService

router = APIRouter(prefix="/geozones", tags=["geozones"])


@router.post("", response_model=GeozoneRead, status_code=status.HTTP_201_CREATED)
async def create_geozone(
    payload: GeozoneCreate,
    user_id: str = Header(..., alias="X-User-Id"),
    session: AsyncSession = Depends(get_session),
    service: GeozoneService = Depends(get_geozone_service),
) -> GeozoneRead:
    return await service.create(session, user_id=user_id, payload=payload)


@router.get("", response_model=list[GeozoneRead])
async def list_geozones(
    user_id: str = Header(..., alias="X-User-Id"),
    session: AsyncSession = Depends(get_session),
    service: GeozoneService = Depends(get_geozone_service),
) -> list[GeozoneRead]:
    return await service.list(session, user_id=user_id)


@router.get("/{geozone_id}", response_model=GeozoneRead)
async def get_geozone(
    geozone_id: UUID,
    user_id: str = Header(..., alias="X-User-Id"),
    session: AsyncSession = Depends(get_session),
    service: GeozoneService = Depends(get_geozone_service),
) -> GeozoneRead:
    geozone = await service.get(session, geozone_id=geozone_id, user_id=user_id)
    if geozone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geozone not found")
    return geozone


@router.patch("/{geozone_id}", response_model=GeozoneRead)
async def update_geozone(
    geozone_id: UUID,
    payload: GeozoneUpdate,
    user_id: str = Header(..., alias="X-User-Id"),
    session: AsyncSession = Depends(get_session),
    service: GeozoneService = Depends(get_geozone_service),
) -> GeozoneRead:
    geozone = await service.update(session, geozone_id=geozone_id, user_id=user_id, payload=payload)
    if geozone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geozone not found")
    return geozone


@router.delete("/{geozone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_geozone(
    geozone_id: UUID,
    user_id: str = Header(..., alias="X-User-Id"),
    session: AsyncSession = Depends(get_session),
    service: GeozoneService = Depends(get_geozone_service),
) -> None:
    deleted = await service.delete(session, geozone_id=geozone_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geozone not found")

