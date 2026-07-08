from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class LocationUpdateMessage(BaseModel):
    type: Literal["location_update"] = "location_update"
    device_id: str
    latitude: float
    longitude: float
    timestamp: datetime


class GeozoneAlertMessage(BaseModel):
    type: Literal["geozone_alert"] = "geozone_alert"
    user_id: str
    device_id: str
    geozone_id: UUID
    geozone_name: str
    latitude: float
    longitude: float
    timestamp: datetime

