import asyncio
import hashlib
from dataclasses import dataclass

from app.core.logging import get_logger
from app.schemas.location import LocationIngest, LocationQueueItem

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class QueuedLocation:
    payload: LocationQueueItem


class LocationQueueFull(Exception):
    pass


def compute_location_shard(user_id: str, device_id: str, worker_count: int) -> int:
    if worker_count < 1:
        raise ValueError("worker_count must be at least 1")
    digest = hashlib.sha256(f"{user_id}:{device_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % worker_count


class LocationIngestionService:
    def __init__(self, queues: list[asyncio.Queue[QueuedLocation]]) -> None:
        self.queues = queues

    async def enqueue(self, *, user_id: str, payload: LocationIngest) -> None:
        if not self.queues:
            raise ValueError("at least one location queue is required")
        item = QueuedLocation(
            payload=LocationQueueItem(
                user_id=user_id,
                device_id=payload.device_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
                timestamp=payload.timestamp,
            )
        )
        shard_index = compute_location_shard(user_id, payload.device_id, len(self.queues))
        queue = self.queues[shard_index]
        try:
            queue.put_nowait(item)
            logger.debug("accepted location update user_id=%s device_id=%s", user_id, payload.device_id)
        except asyncio.QueueFull as exc:
            logger.warning("rejected location update due to full queue user_id=%s device_id=%s", user_id, payload.device_id)
            raise LocationQueueFull from exc

    async def enqueue_batch(self, *, user_id: str, payloads: list[LocationIngest]) -> tuple[int, int]:
        accepted = 0
        rejected = 0
        for payload in payloads:
            try:
                await self.enqueue(user_id=user_id, payload=payload)
                accepted += 1
            except LocationQueueFull:
                rejected += 1
        logger.info("ingested batch user_id=%s accepted=%s rejected=%s", user_id, accepted, rejected)
        return accepted, rejected
