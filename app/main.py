from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.lifespan import lifespan

settings = get_settings()
templates = Jinja2Templates(directory="templates")

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def demo_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"api_prefix": "/api/v1"},
    )
    


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    queues = getattr(request.app.state, "location_queues", None) or []
    queue_sizes = [{"shard": index, "size": queue.qsize(), "maxsize": queue.maxsize} for index, queue in enumerate(queues)]
    health_payload: dict[str, object] = {
        "status": "ok",
        "api": "ok",
        "database": "ok",
        "redis": "ok",
        "worker_count": len(queues),
        "queue_size": sum(item["size"] for item in queue_sizes) if queue_sizes else None,
        "queue_shards": queue_sizes,
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

