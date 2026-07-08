from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GeozoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    radius_m: int = Field(gt=0)
    is_active: bool = True


class GeozoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    radius_m: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class GeozoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    name: str
    latitude: float
    longitude: float
    radius_m: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

