import argparse
import asyncio
import random
import time
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class DeviceState:
    device_id: str
    latitude: float
    longitude: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async load generator for real-time geo tracking")
    parser.add_argument("--devices", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--api-url", type=str, default="http://localhost:8000")
    parser.add_argument("--user-id", type=str, default="load-test-user")
    parser.add_argument("--concurrency", type=int, default=20)
    return parser.parse_args()


def build_devices(count: int) -> list[DeviceState]:
    base_latitude = 49.8397
    base_longitude = 24.0297
    devices = []
    for index in range(count):
        devices.append(
            DeviceState(
                device_id=f"device-{index:05d}",
                latitude=base_latitude + random.uniform(-0.02, 0.02),
                longitude=base_longitude + random.uniform(-0.02, 0.02),
            )
        )
    return devices


def drift_device(device: DeviceState) -> None:
    device.latitude = max(-90.0, min(90.0, device.latitude + random.uniform(-0.0008, 0.0008)))
    device.longitude = max(-180.0, min(180.0, device.longitude + random.uniform(-0.0008, 0.0008)))


def chunked(items: list[DeviceState], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


async def send_batch(client: httpx.AsyncClient, api_url: str, user_id: str, batch: list[DeviceState]) -> bool:
    payload = {
        "locations": [
            {
                "device_id": device.device_id,
                "latitude": device.latitude,
                "longitude": device.longitude,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            for device in batch
        ]
    }
    response = await client.post(f"{api_url.rstrip('/')}/api/v1/locations/batch", json=payload, headers={"X-User-Id": user_id})
    return response.status_code < 400


async def send_batches_with_limit(
    client: httpx.AsyncClient,
    api_url: str,
    user_id: str,
    batches: list[list[DeviceState]],
    concurrency: int,
) -> tuple[int, int]:
    queue: asyncio.Queue[list[DeviceState]] = asyncio.Queue()
    for batch in batches:
        queue.put_nowait(batch)

    async def worker() -> tuple[int, int]:
        requests = 0
        failures = 0
        while True:
            try:
                batch = queue.get_nowait()
            except asyncio.QueueEmpty:
                return requests, failures
            try:
                ok = await send_batch(client, api_url, user_id, batch)
                requests += 1
                if not ok:
                    failures += 1
            except Exception:
                requests += 1
                failures += 1
            finally:
                queue.task_done()

    worker_count = min(max(1, concurrency), max(1, len(batches)))
    results = await asyncio.gather(*(worker() for _ in range(worker_count)))
    return sum(requests for requests, _ in results), sum(failures for _, failures in results)


async def run_generator(args: argparse.Namespace) -> None:
    devices = build_devices(args.devices)
    total_sent = 0
    total_failed = 0
    tick = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            tick += 1
            started = time.perf_counter()
            for device in devices:
                drift_device(device)
            batches = list(chunked(devices, args.batch_size))
            requests, failures = await send_batches_with_limit(
                client,
                args.api_url,
                args.user_id,
                batches,
                args.concurrency,
            )
            total_sent += len(devices)
            total_failed += failures * args.batch_size
            elapsed = max(time.perf_counter() - started, 0.001)
            rps = requests / elapsed
            print(
                f"tick={tick} sent_events={len(devices)} requests={requests} failed_requests={failures} rps={rps:.2f} total_sent={total_sent} total_failed={total_failed}",
                flush=True,
            )
            await asyncio.sleep(args.interval)


def main() -> None:
    args = parse_args()
    asyncio.run(run_generator(args))


if __name__ == "__main__":
    main()
