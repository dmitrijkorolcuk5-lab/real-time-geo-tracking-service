from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_location_ingestion_service
from app.api.v1.locations import router as locations_router
from app.services.location_ingestion_service import LocationQueueFull


LOCATION_PAYLOAD = {
    "device_id": "device-1",
    "latitude": 49.8397,
    "longitude": 24.0297,
    "timestamp": "2026-07-06T12:00:00Z",
}


class FakeLocationIngestionService:
    def __init__(self, *, full: bool = False, batch_result: tuple[int, int] | None = None) -> None:
        self.full = full
        self.batch_result = batch_result
        self.enqueued = []
        self.batches = []

    async def enqueue(self, *, user_id: str, payload) -> None:
        if self.full:
            raise LocationQueueFull
        self.enqueued.append((user_id, payload))

    async def enqueue_batch(self, *, user_id: str, payloads: list) -> tuple[int, int]:
        self.batches.append((user_id, payloads))
        return self.batch_result or (len(payloads), 0)


def build_client(service: FakeLocationIngestionService) -> TestClient:
    app = FastAPI()
    app.include_router(locations_router, prefix="/api/v1")
    app.dependency_overrides[get_location_ingestion_service] = lambda: service
    return TestClient(app)


def test_ingest_location_accepts_single_payload() -> None:
    service = FakeLocationIngestionService()
    client = build_client(service)

    response = client.post("/api/v1/locations", json=LOCATION_PAYLOAD, headers={"X-User-Id": "user-1"})

    assert response.status_code == 202
    assert response.json() == {"accepted": 1, "rejected": 0}
    assert service.enqueued[0][0] == "user-1"
    assert service.enqueued[0][1].timestamp == datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)


def test_ingest_location_rejects_invalid_payload_before_enqueue() -> None:
    service = FakeLocationIngestionService()
    client = build_client(service)
    invalid_payload = {**LOCATION_PAYLOAD, "latitude": 91.0}

    response = client.post("/api/v1/locations", json=invalid_payload, headers={"X-User-Id": "user-1"})

    assert response.status_code == 422
    assert service.enqueued == []


def test_ingest_location_returns_503_when_queue_is_full() -> None:
    service = FakeLocationIngestionService(full=True)
    client = build_client(service)

    response = client.post("/api/v1/locations", json=LOCATION_PAYLOAD, headers={"X-User-Id": "user-1"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Ingestion queue is full"


def test_ingest_locations_batch_returns_acceptance_counts() -> None:
    service = FakeLocationIngestionService(batch_result=(1, 1))
    client = build_client(service)
    batch_payload = {"locations": [LOCATION_PAYLOAD, {**LOCATION_PAYLOAD, "device_id": "device-2"}]}

    response = client.post("/api/v1/locations/batch", json=batch_payload, headers={"X-User-Id": "user-1"})

    assert response.status_code == 202
    assert response.json() == {"accepted": 1, "rejected": 1}
    assert service.batches[0][0] == "user-1"
    assert len(service.batches[0][1]) == 2


def test_ingest_locations_batch_rejects_invalid_payload_before_enqueue() -> None:
    service = FakeLocationIngestionService()
    client = build_client(service)
    batch_payload = {"locations": [{**LOCATION_PAYLOAD, "longitude": 181.0}]}

    response = client.post("/api/v1/locations/batch", json=batch_payload, headers={"X-User-Id": "user-1"})

    assert response.status_code == 422
    assert service.batches == []
