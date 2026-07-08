from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_geozone_service, get_session
from app.api.v1.geozones import router as geozones_router
from app.schemas.geozone import GeozoneRead


CREATE_PAYLOAD = {
    "name": "Warehouse",
    "latitude": 49.8397,
    "longitude": 24.0297,
    "radius_m": 150,
    "is_active": True,
}


class FakeGeozoneService:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, UUID], GeozoneRead] = {}

    async def create(self, session, *, user_id: str, payload) -> GeozoneRead:
        geozone_id = uuid4()
        now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
        row = GeozoneRead(
            id=geozone_id,
            user_id=user_id,
            name=payload.name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_m=payload.radius_m,
            is_active=payload.is_active,
            created_at=now,
            updated_at=now,
        )
        self.rows[(user_id, geozone_id)] = row
        return row

    async def list(self, session, *, user_id: str) -> list[GeozoneRead]:
        return [row for (owner, _), row in self.rows.items() if owner == user_id]

    async def get(self, session, *, geozone_id: UUID, user_id: str) -> GeozoneRead | None:
        return self.rows.get((user_id, geozone_id))

    async def update(self, session, *, geozone_id: UUID, user_id: str, payload) -> GeozoneRead | None:
        row = self.rows.get((user_id, geozone_id))
        if row is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        updated = row.model_copy(update={**updates, "updated_at": datetime(2026, 7, 6, 12, 5, tzinfo=timezone.utc)})
        self.rows[(user_id, geozone_id)] = updated
        return updated

    async def delete(self, session, *, geozone_id: UUID, user_id: str) -> bool:
        return self.rows.pop((user_id, geozone_id), None) is not None


def build_client(service: FakeGeozoneService) -> TestClient:
    app = FastAPI()
    app.include_router(geozones_router, prefix="/api/v1")
    app.dependency_overrides[get_geozone_service] = lambda: service
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def test_geozone_crud_routes() -> None:
    service = FakeGeozoneService()
    client = build_client(service)
    headers = {"X-User-Id": "user-1"}

    create_response = client.post("/api/v1/geozones", json=CREATE_PAYLOAD, headers=headers)
    geozone_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert create_response.json()["user_id"] == "user-1"

    list_response = client.get("/api/v1/geozones", headers=headers)
    assert list_response.status_code == 200
    assert [row["id"] for row in list_response.json()] == [geozone_id]

    read_response = client.get(f"/api/v1/geozones/{geozone_id}", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "Warehouse"

    update_response = client.patch(f"/api/v1/geozones/{geozone_id}", json={"name": "Depot"}, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Depot"

    delete_response = client.delete(f"/api/v1/geozones/{geozone_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/geozones/{geozone_id}", headers=headers).status_code == 404


def test_geozone_routes_are_scoped_by_user_header() -> None:
    service = FakeGeozoneService()
    client = build_client(service)

    create_response = client.post("/api/v1/geozones", json=CREATE_PAYLOAD, headers={"X-User-Id": "user-1"})
    geozone_id = create_response.json()["id"]

    assert client.get(f"/api/v1/geozones/{geozone_id}", headers={"X-User-Id": "user-2"}).status_code == 404
    assert (
        client.patch(f"/api/v1/geozones/{geozone_id}", json={"name": "Other"}, headers={"X-User-Id": "user-2"}).status_code
        == 404
    )
    assert client.delete(f"/api/v1/geozones/{geozone_id}", headers={"X-User-Id": "user-2"}).status_code == 404
    assert client.get(f"/api/v1/geozones/{geozone_id}", headers={"X-User-Id": "user-1"}).status_code == 200
