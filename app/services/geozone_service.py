from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.geozone_repository import GeozoneRepository
from app.schemas.geozone import GeozoneCreate, GeozoneRead, GeozoneUpdate


class GeozoneService:
    def __init__(self, repository: GeozoneRepository | None = None) -> None:
        self.repository = repository or GeozoneRepository()

    def _to_read(self, row) -> GeozoneRead:
        return GeozoneRead.model_validate(row._mapping)

    async def create(self, session: AsyncSession, *, user_id: str, payload: GeozoneCreate) -> GeozoneRead:
        geozone = await self.repository.create(
            session,
            user_id=user_id,
            name=payload.name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_m=payload.radius_m,
            is_active=payload.is_active,
        )
        await session.commit()
        fresh = await self.repository.get_by_id_and_user(session, geozone_id=geozone.id, user_id=user_id)
        return self._to_read(fresh)

    async def list(self, session: AsyncSession, *, user_id: str) -> list[GeozoneRead]:
        rows = await self.repository.list_by_user(session, user_id=user_id)
        return [self._to_read(row) for row in rows]

    async def get(self, session: AsyncSession, *, geozone_id, user_id: str) -> GeozoneRead | None:
        row = await self.repository.get_by_id_and_user(session, geozone_id=geozone_id, user_id=user_id)
        return None if row is None else self._to_read(row)

    async def update(self, session: AsyncSession, *, geozone_id, user_id: str, payload: GeozoneUpdate) -> GeozoneRead | None:
        geozone = await self.repository.update(
            session,
            geozone_id=geozone_id,
            user_id=user_id,
            name=payload.name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_m=payload.radius_m,
            is_active=payload.is_active,
        )
        if geozone is None:
            return None
        await session.commit()
        row = await self.repository.get_by_id_and_user(session, geozone_id=geozone_id, user_id=user_id)
        return None if row is None else self._to_read(row)

    async def delete(self, session: AsyncSession, *, geozone_id, user_id: str) -> bool:
        deleted = await self.repository.delete(session, geozone_id=geozone_id, user_id=user_id)
        if deleted:
            await session.commit()
        return deleted

