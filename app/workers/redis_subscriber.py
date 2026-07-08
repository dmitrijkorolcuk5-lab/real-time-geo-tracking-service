import asyncio
import json

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.services.websocket_manager import WebsocketManager

logger = get_logger(__name__)


async def run_redis_subscriber(*, redis: Redis, websocket_manager: WebsocketManager, channel_name: str = "geo:events") -> None:
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel_name)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            payload = json.loads(message["data"])
            event_type = payload.get("event_type")
            user_id = payload.get("user_id")
            event_payload = payload.get("payload", {})
            if event_type == "location_update" and user_id:
                await websocket_manager.broadcast_location(user_id, event_payload)
            elif event_type == "geozone_alert" and user_id:
                await websocket_manager.broadcast_alert(user_id, event_payload)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.close()

