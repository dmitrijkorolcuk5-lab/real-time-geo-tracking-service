from datetime import datetime

from pydantic import BaseModel, Field


class LocationIngest(BaseModel):
    device_id: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timestamp: datetime


class LocationBatchIngest(BaseModel):
    locations: list[LocationIngest]


class LocationBatchResult(BaseModel):
    accepted: int
    rejected: int


class LocationQueueItem(BaseModel):
    user_id: str
    device_id: str
    latitude: float
    longitude: float
    timestamp: datetime

