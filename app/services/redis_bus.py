import json

from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisBus:
    channel_name = "geo:events"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, event: dict) -> None:
        try:
            await self.redis.publish(self.channel_name, json.dumps(event, default=str))
        except Exception:
            logger.exception("redis publish failed channel=%s event_type=%s", self.channel_name, event.get("event_type"))
            raise

    async def close(self) -> None:
        close = getattr(self.redis, "aclose", None)
        if close is not None:
            await close()
        else:
            await self.redis.close()

