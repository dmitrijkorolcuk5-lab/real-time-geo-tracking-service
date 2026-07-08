import asyncio
import sys

import pytest

import generator


def test_generator_defaults_to_10000_devices(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["generator.py"])

    args = generator.parse_args()

    assert args.devices == 10000
    assert args.batch_size == 500
    assert args.concurrency == 20


def test_chunked_respects_batch_size() -> None:
    devices = [
        generator.DeviceState(device_id=f"device-{index}", latitude=49.0, longitude=24.0)
        for index in range(5)
    ]

    batches = list(generator.chunked(devices, 2))

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_drift_device_changes_coordinates(monkeypatch) -> None:
    monkeypatch.setattr(generator.random, "uniform", lambda low, high: 0.0005)
    device = generator.DeviceState(device_id="device-1", latitude=49.0, longitude=24.0)

    generator.drift_device(device)

    assert device.latitude == 49.0005
    assert device.longitude == 24.0005


@pytest.mark.asyncio
async def test_send_batches_with_limit_caps_concurrent_requests(monkeypatch) -> None:
    active_requests = 0
    max_active_requests = 0

    async def fake_send_batch(client, api_url: str, user_id: str, batch: list[generator.DeviceState]) -> bool:
        nonlocal active_requests, max_active_requests
        active_requests += 1
        max_active_requests = max(max_active_requests, active_requests)
        await asyncio.sleep(0.01)
        active_requests -= 1
        return True

    monkeypatch.setattr(generator, "send_batch", fake_send_batch)
    batches = [
        [generator.DeviceState(device_id=f"device-{index}", latitude=49.0, longitude=24.0)]
        for index in range(10)
    ]

    requests, failures = await generator.send_batches_with_limit(
        client=None,
        api_url="http://example.test",
        user_id="user-1",
        batches=batches,
        concurrency=3,
    )

    assert requests == 10
    assert failures == 0
    assert max_active_requests <= 3
