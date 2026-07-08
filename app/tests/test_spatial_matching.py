from datetime import datetime, timezone

import pytest

from app.repositories.geozone_repository import GeozoneRepository
from app.schemas.location import LocationQueueItem


class CaptureResult:
    def all(self):
        return []


class CaptureSession:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return CaptureResult()


def test_matching_statement_uses_postgis_distance() -> None:
    repository = GeozoneRepository()
    statement = repository.build_matching_statement(
        user_id="user-123",
        latitude=49.8397,
        longitude=24.0297,
    )

    compiled = str(statement.compile())

    assert "ST_DWithin" in compiled
    assert "geography" in compiled
    assert "geozones.radius_m" in compiled
    assert "geozones.is_active" in compiled
    assert "ST_GeogFromText" in compiled or "ST_MakePoint" in compiled


@pytest.mark.asyncio
async def test_batch_matching_statement_uses_single_values_join() -> None:
    repository = GeozoneRepository()
    session = CaptureSession()
    locations = [
        LocationQueueItem(
            user_id="user-1",
            device_id="device-1",
            latitude=49.8397,
            longitude=24.0297,
            timestamp=datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc),
        ),
        LocationQueueItem(
            user_id="user-2",
            device_id="device-2",
            latitude=49.9,
            longitude=24.1,
            timestamp=datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]

    matches = await repository.find_matching_geozones_for_locations(session, locations=locations)

    assert matches == []
    assert session.statement is not None
    compiled = str(session.statement.compile())
    assert "incoming_locations" in compiled
    assert compiled.count("ST_DWithin") == 1
    assert "geozones.user_id" in compiled
    assert "geozones.is_active" in compiled
