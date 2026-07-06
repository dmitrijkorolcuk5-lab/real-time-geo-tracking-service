from __future__ import annotations

import json

from redis.asyncio import Redis


class RedisBus:
    channel_name = "geo:events"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, event: dict) -> None:
        await self.redis.publish(self.channel_name, json.dumps(event, default=str))

    async def close(self) -> None:
        close = getattr(self.redis, "aclose", None)
        if close is not None:
            await close()
        else:
            await self.redis.close()

