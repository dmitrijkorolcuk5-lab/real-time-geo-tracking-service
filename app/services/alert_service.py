from __future__ import annotations

from app.models.geozone import Geozone
from app.schemas.location import LocationQueueItem


class AlertService:
    def build_alert_payload(self, *, user_id: str, geozone: Geozone, location: LocationQueueItem) -> dict:
        return {
            "type": "geozone_alert",
            "user_id": user_id,
            "device_id": location.device_id,
            "geozone_id": geozone.id,
            "geozone_name": geozone.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": location.timestamp,
        }

