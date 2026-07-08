import asyncio

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
    worker_id: int | None = None,
) -> None:
    pending: list[QueuedLocation] = []
    deadline: float | None = None
    loop = asyncio.get_running_loop()
    worker_label = f"worker-{worker_id}" if worker_id is not None else "worker"

    async def flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        started = loop.time()
        batch = [item.payload for item in pending]
        pending = []

        async with session_factory() as session:
            try:
                await processor.process_batch(session, batch)
            except Exception:
                await session.rollback()
                logger.exception("location batch processing failed worker=%s", worker_label)
                raise
        elapsed_ms = (loop.time() - started) * 1000.0
        logger.info("flushed location batch worker=%s events=%s duration_ms=%.2f", worker_label, len(batch), elapsed_ms)

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

