from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationIngest, LocationQueueItem
from app.services.location_ingestion_service import LocationIngestionService, LocationQueueFull
from app.services.location_processor import LocationProcessor


class CaptureSession:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement) -> None:
        self.statement = statement


class RecordingLocationRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def build_location_row(
        self, *, user_id: str, device_id: str, latitude: float, longitude: float, reported_at: datetime
    ) -> dict:
        return {
            "user_id": user_id,
            "device_id": device_id,
            "latitude": latitude,
            "longitude": longitude,
            "reported_at": reported_at,
        }

    async def bulk_upsert_latest_locations(self, session, rows: list[dict]) -> None:
        self.rows = rows


class NoopGeozoneRepository:
    async def find_matching_geozones(self, session, *, user_id: str, latitude: float, longitude: float):
        return []


class NoopSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.mark.asyncio
async def test_latest_locations_upsert_conflicts_on_user_and_device() -> None:
    repository = LocationRepository()
    session = CaptureSession()
    rows = [
        repository.build_location_row(
            user_id="user-1",
            device_id="device-1",
            latitude=49.0,
            longitude=24.0,
            reported_at=datetime.now(timezone.utc),
        )
    ]

    await repository.bulk_upsert_latest_locations(session, rows)

    assert session.statement is not None
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (user_id, device_id)" in compiled


@pytest.mark.asyncio
async def test_location_processor_deduplicates_by_user_and_device() -> None:
    repository = RecordingLocationRepository()
    processor = LocationProcessor(
        geozone_repository=NoopGeozoneRepository(),
        location_repository=repository,
        redis_bus=None,
    )
    session = NoopSession()
    first_timestamp = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)
    later_timestamp = datetime(2026, 7, 6, 12, 0, 10, tzinfo=timezone.utc)
    even_later_timestamp = datetime(2026, 7, 6, 12, 0, 20, tzinfo=timezone.utc)

    await processor.process_batch(
        session,
        [
            (
                "user-a",
                LocationQueueItem(
                    user_id="user-a",
                    device_id="device-shared",
                    latitude=49.0,
                    longitude=24.0,
                    timestamp=first_timestamp,
                ),
            ),
            (
                "user-b",
                LocationQueueItem(
                    user_id="user-b",
                    device_id="device-shared",
                    latitude=50.0,
                    longitude=25.0,
                    timestamp=later_timestamp,
                ),
            ),
            (
                "user-a",
                LocationQueueItem(
                    user_id="user-a",
                    device_id="device-shared",
                    latitude=49.5,
                    longitude=24.5,
                    timestamp=even_later_timestamp,
                ),
            ),
        ],
    )

    assert len(repository.rows) == 2
    rows_by_user = {row["user_id"]: row for row in repository.rows}
    assert rows_by_user["user-a"]["reported_at"] == even_later_timestamp
    assert rows_by_user["user-b"]["reported_at"] == later_timestamp


@pytest.mark.asyncio
async def test_location_ingestion_service_rejects_when_queue_is_full() -> None:
    queue = asyncio.Queue(maxsize=1)
    service = LocationIngestionService(queue)
    payload = LocationIngest(
        device_id="device-1",
        latitude=49.0,
        longitude=24.0,
        timestamp=datetime.now(timezone.utc),
    )

    await service.enqueue(user_id="user-1", payload=payload)

    with pytest.raises(LocationQueueFull):
        await service.enqueue(user_id="user-1", payload=payload)