from __future__ import annotations

from typing import Iterable
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geozone import Geozone


def _point_wkt(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def _read_statement() -> select:
    geometry_point = cast(Geozone.center, Geometry(geometry_type="POINT", srid=4326))
    return select(
        Geozone.id,
        Geozone.user_id,
        Geozone.name,
        func.ST_Y(geometry_point).label("latitude"),
        func.ST_X(geometry_point).label("longitude"),
        Geozone.radius_m,
        Geozone.is_active,
        Geozone.created_at,
        Geozone.updated_at,
    )


class GeozoneRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        name: str,
        latitude: float,
        longitude: float,
        radius_m: int,
        is_active: bool = True,
    ) -> Geozone:
        geozone = Geozone(
            user_id=user_id,
            name=name,
            center=_point_wkt(latitude, longitude),
            radius_m=radius_m,
            is_active=is_active,
        )
        session.add(geozone)
        await session.flush()
        return geozone

    async def list_by_user(self, session: AsyncSession, *, user_id: str) -> list[Geozone]:
        result = await session.execute(_read_statement().where(Geozone.user_id == user_id).order_by(Geozone.created_at.desc()))
        return result.all()

    async def get_by_id_and_user(self, session: AsyncSession, *, geozone_id: UUID, user_id: str):
        result = await session.execute(_read_statement().where(and_(Geozone.id == geozone_id, Geozone.user_id == user_id)))
        return result.one_or_none()

    async def update(
        self,
        session: AsyncSession,
        *,
        geozone_id: UUID,
        user_id: str,
        name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_m: int | None = None,
        is_active: bool | None = None,
    ):
        geozone = await session.get(Geozone, geozone_id)
        if geozone is None or geozone.user_id != user_id:
            return None
        if name is not None:
            geozone.name = name
        if latitude is not None and longitude is not None:
            geozone.center = _point_wkt(latitude, longitude)
        if radius_m is not None:
            geozone.radius_m = radius_m
        if is_active is not None:
            geozone.is_active = is_active
        await session.flush()
        return geozone

    async def delete(self, session: AsyncSession, *, geozone_id: UUID, user_id: str) -> bool:
        geozone = await session.get(Geozone, geozone_id)
        if geozone is None or geozone.user_id != user_id:
            return False
        await session.delete(geozone)
        await session.flush()
        return True

    def build_matching_statement(self, *, user_id: str, latitude: float, longitude: float):
        point = cast(_point_wkt(latitude, longitude), Geography(geometry_type="POINT", srid=4326))
        return select(Geozone).where(
            and_(
                Geozone.user_id == user_id,
                Geozone.is_active.is_(True),
                func.ST_DWithin(Geozone.center, point, Geozone.radius_m),
            )
        )

    async def find_matching_geozones(
        self, session: AsyncSession, *, user_id: str, latitude: float, longitude: float
    ) -> list[Geozone]:
        result = await session.execute(self.build_matching_statement(user_id=user_id, latitude=latitude, longitude=longitude))
        return list(result.scalars().all())

