from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_location import DeviceLocation


def _point_wkt(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


class LocationRepository:
    async def bulk_upsert_latest_locations(self, session: AsyncSession, rows: list[dict]) -> None:
        if not rows:
            return
        statement = insert(DeviceLocation).values(rows)
        upsert_statement = statement.on_conflict_do_update(
            index_elements=[DeviceLocation.user_id, DeviceLocation.device_id],
            set_={
                "location": statement.excluded.location,
                "latitude": statement.excluded.latitude,
                "longitude": statement.excluded.longitude,
                "reported_at": statement.excluded.reported_at,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        await session.execute(upsert_statement)

    def build_location_row(
        self, *, user_id: str, device_id: str, latitude: float, longitude: float, reported_at: datetime
    ) -> dict:
        return {
            "user_id": user_id,
            "device_id": device_id,
            "location": _point_wkt(latitude, longitude),
            "latitude": latitude,
            "longitude": longitude,
            "reported_at": reported_at,
        }

