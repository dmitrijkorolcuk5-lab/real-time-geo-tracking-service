from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis, from_url
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import build_engine, build_session_factory
from app.services.geozone_service import GeozoneService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.location_processor import LocationProcessor
from app.services.redis_bus import RedisBus
from app.services.websocket_manager import WebsocketManager
from app.workers.location_worker import run_location_worker
from app.workers.redis_subscriber import run_redis_subscriber

logger = get_logger(__name__)


async def _wait_for_database(engine, attempts: int = 30, delay_seconds: float = 1.0) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(delay_seconds)
    raise RuntimeError("database is not reachable") from last_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    await _wait_for_database(engine)

    redis: Redis = from_url(settings.redis_url, decode_responses=True)
    websocket_manager = WebsocketManager(
        update_queue_size=settings.websocket_update_queue_size,
        alert_queue_size=settings.websocket_alert_queue_size,
    )
    redis_bus = RedisBus(redis)
    location_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.queue_maxsize)
    location_ingestion_service = LocationIngestionService(location_queue)
    geozone_service = GeozoneService()
    location_processor = LocationProcessor(redis_bus=redis_bus)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis = redis
    app.state.websocket_manager = websocket_manager
    app.state.redis_bus = redis_bus
    app.state.location_queue = location_queue
    app.state.location_ingestion_service = location_ingestion_service
    app.state.geozone_service = geozone_service

    worker_task = asyncio.create_task(
        run_location_worker(
            queue=location_queue,
            session_factory=session_factory,
            processor=location_processor,
            batch_size=settings.batch_max_size,
            flush_interval_seconds=settings.batch_flush_interval_seconds,
        )
    )
    subscriber_task = asyncio.create_task(
        run_redis_subscriber(redis=redis, websocket_manager=websocket_manager)
    )
    app.state.background_tasks = [worker_task, subscriber_task]

    try:
        yield
    finally:
        for task in app.state.background_tasks:
            task.cancel()
        await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
        await redis_bus.close()
        await engine.dispose()

