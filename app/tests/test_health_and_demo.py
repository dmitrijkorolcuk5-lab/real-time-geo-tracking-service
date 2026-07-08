import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app, health


class FakeConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def execute(self, statement) -> None:
        return None


class FakeEngine:
    def connect(self) -> FakeConnection:
        return FakeConnection()


class FakeRedis:
    async def ping(self) -> bool:
        return True


def test_demo_page_renders_with_api_prefix_and_reconnect_feedback() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Live device tracking with geozone alerts" in response.text
    assert "API prefix: /api/v1" in response.text
    assert "/api/v1/ws?user_id=" in response.text
    assert "Already connected as" in response.text


@pytest.mark.asyncio
async def test_health_reports_worker_count_and_queue_shards() -> None:
    queues = [asyncio.Queue(maxsize=2), asyncio.Queue(maxsize=3)]
    queues[0].put_nowait(object())
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                engine=FakeEngine(),
                redis=FakeRedis(),
                location_queues=queues,
            )
        )
    )

    payload = await health(request)

    assert payload["status"] == "ok"
    assert payload["worker_count"] == 2
    assert payload["queue_size"] == 1
    assert payload["queue_shards"] == [
        {"shard": 0, "size": 1, "maxsize": 2},
        {"shard": 1, "size": 0, "maxsize": 3},
    ]
