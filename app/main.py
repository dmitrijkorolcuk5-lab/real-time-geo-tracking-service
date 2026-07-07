from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.lifespan import lifespan

settings = get_settings()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    queue = getattr(request.app.state, "location_queue", None)
    health_payload: dict[str, object] = {
        "status": "ok",
        "api": "ok",
        "database": "ok",
        "redis": "ok",
        "queue_size": queue.qsize() if queue is not None else None,
    }

    try:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        health_payload["status"] = "degraded"
        health_payload["database"] = f"error:{exc.__class__.__name__}"

    try:
        await request.app.state.redis.ping()
    except Exception as exc:
        health_payload["status"] = "degraded"
        health_payload["redis"] = f"error:{exc.__class__.__name__}"

    if health_payload["status"] != "ok":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_payload)

    return health_payload

