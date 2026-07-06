from __future__ import annotations

import asyncio

import pytest

from app.services.websocket_manager import WebsocketManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent = []
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload) -> None:
        self.sent.append(payload)

    async def close(self, code: int | None = None) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_websocket_manager_supports_multiple_sessions_per_user() -> None:
    manager = WebsocketManager(update_queue_size=10, alert_queue_size=10)
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    session1 = await manager.connect(ws1, user_id="user-123")
    session2 = await manager.connect(ws2, user_id="user-123")

    await manager.broadcast_location(
        "user-123",
        {"type": "location_update", "device_id": "device-1", "latitude": 1.0, "longitude": 2.0, "timestamp": "2026-07-06T12:00:00Z"},
    )
    await manager.broadcast_alert(
        "user-123",
        {"type": "geozone_alert", "user_id": "user-123", "device_id": "device-1", "geozone_id": "zone-1", "geozone_name": "Zone", "latitude": 1.0, "longitude": 2.0, "timestamp": "2026-07-06T12:00:00Z"},
    )

    await asyncio.sleep(0.05)

    assert manager.active_session_count("user-123") == 2
    assert ws1.sent and ws2.sent
    assert any(message["type"] == "geozone_alert" for message in ws1.sent)
    assert any(message["type"] == "geozone_alert" for message in ws2.sent)

    await manager.disconnect(session1)
    await manager.disconnect(session2)
