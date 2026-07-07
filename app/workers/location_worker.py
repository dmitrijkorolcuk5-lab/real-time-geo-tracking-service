from __future__ import annotations

import asyncio
from collections import defaultdict

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import get_logger
from app.services.location_processor import LocationProcessor
from app.services.location_ingestion_service import QueuedLocation

logger = get_logger(__name__)


async def run_location_worker(
    *,
    queue: asyncio.Queue[QueuedLocation],
    session_factory: async_sessionmaker,
    processor: LocationProcessor,
    batch_size: int,
    flush_interval_seconds: float,
) -> None:
    pending: list[QueuedLocation] = []
    deadline: float | None = None
    loop = asyncio.get_running_loop()

    async def flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        started = loop.time()
        grouped: dict[str, list] = defaultdict(list)
        for item in pending:
            grouped[item.user_id].append(item.payload)
        pending = []

        async with session_factory() as session:
            for user_id, payloads in grouped.items():
                try:
                    await processor.process_batch(session, [(user_id, payload) for payload in payloads])
                except Exception:
                    await session.rollback()
                    logger.exception("location batch processing failed for user_id=%s", user_id)
        elapsed_ms = (loop.time() - started) * 1000.0
        logger.info("flushed location batch events=%s users=%s duration_ms=%.2f", sum(len(items) for items in grouped.values()), len(grouped), elapsed_ms)

    while True:
        timeout = None if deadline is None else max(0.0, deadline - loop.time())
        try:
            item = await asyncio.wait_for(queue.get(), timeout=timeout)
            pending.append(item)
            queue.task_done()
            if deadline is None:
                deadline = loop.time() + flush_interval_seconds
            if len(pending) >= batch_size:
                await flush_pending()
                deadline = None
        except asyncio.TimeoutError:
            await flush_pending()
            deadline = None
        except asyncio.CancelledError:
            break

