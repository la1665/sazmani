from redis import asyncio as aioredis
from contextlib import asynccontextmanager
from typing import Optional
import json
import hashlib
import os

from settings import settings

class RedisCache:
    def __init__(self):
        self.redis = None

    async def init_cache(self):
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    @asynccontextmanager
    async def get_connection(self):
        if not self.redis:
            await self.init_cache()
        yield self.redis

    async def generate_key(self, *args) -> str:
        key_str = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[dict]:
        async with self.get_connection() as conn:
            data = await conn.get(key)
            return json.loads(data) if data else None

    async def set(self, key: str, value: dict, ttl: int = None):
        async with self.get_connection() as conn:
            await conn.set(
                key,
                json.dumps(value),
                ex=ttl or settings.CACHE_TTL
            )

    async def invalidate_model(self, model: str):
        async with self.get_connection() as conn:
            keys = await conn.keys(f"search:{model}:*")
            if keys:
                await conn.delete(*keys)

redis_cache = RedisCache()
