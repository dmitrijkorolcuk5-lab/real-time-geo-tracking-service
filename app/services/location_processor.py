from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.geozone_repository import GeozoneRepository
from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationQueueItem
from app.services.alert_service import AlertService
from app.services.redis_bus import RedisBus

logger = get_logger(__name__)


class LocationProcessor:
    def __init__(
        self,
        *,
        geozone_repository: GeozoneRepository | None = None,
        location_repository: LocationRepository | None = None,
        alert_service: AlertService | None = None,
        redis_bus: RedisBus | None = None,
    ) -> None:
        self.geozone_repository = geozone_repository or GeozoneRepository()
        self.location_repository = location_repository or LocationRepository()
        self.alert_service = alert_service or AlertService()
        self.redis_bus = redis_bus

    async def process_batch(self, session: AsyncSession, items: list[tuple[str, LocationQueueItem]]) -> None:
        if not items:
            return
        latest_by_device: dict[tuple[str, str], tuple[str, LocationQueueItem]] = {}
        for user_id, location in items:
            key = (user_id, location.device_id)
            current = latest_by_device.get(key)
            if current is None or location.timestamp >= current[1].timestamp:
                latest_by_device[key] = (user_id, location)

        rows = [
            self.location_repository.build_location_row(
                user_id=user_id,
                device_id=location.device_id,
                latitude=location.latitude,
                longitude=location.longitude,
                reported_at=location.timestamp,
            )
            for user_id, location in latest_by_device.values()
        ]
        await self.location_repository.bulk_upsert_latest_locations(session, rows)

        for user_id, location in latest_by_device.values():
            location_payload = {
                "type": "location_update",
                "device_id": location.device_id,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timestamp": location.timestamp,
            }
            if self.redis_bus is not None:
                await self.redis_bus.publish({"event_type": "location_update", "user_id": user_id, "payload": location_payload})
            matched = await self.geozone_repository.find_matching_geozones(
                session,
                user_id=user_id,
                latitude=location.latitude,
                longitude=location.longitude,
            )
            logger.info(
                "geozone matches found user_id=%s device_id=%s count=%s",
                user_id,
                location.device_id,
                len(matched),
            )
            for geozone in matched:
                alert_payload = self.alert_service.build_alert_payload(user_id=user_id, geozone=geozone, location=location)
                if self.redis_bus is not None:
                    await self.redis_bus.publish({"event_type": "geozone_alert", "user_id": user_id, "payload": alert_payload})

        await session.commit()

