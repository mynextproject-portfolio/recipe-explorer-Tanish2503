"""
Redis-backed cache for external API responses.

The cache is a module-level singleton; call connect() at app startup and
close() at shutdown. All operations degrade gracefully — if Redis is
unavailable the get/set methods are no-ops, and the caller falls through
to the real API.
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

CACHE_TTL_SECONDS = 86400  # 24 hours
REDIS_URL_DEFAULT = "redis://localhost:6379"

logger = logging.getLogger("recipe_explorer.cache")


class RecipeCache:
    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None

    async def connect(self, url: str = REDIS_URL_DEFAULT) -> None:
        client = redis.from_url(url, decode_responses=True)
        try:
            await client.ping()
            self._client = client
            logger.info("Redis connected at %s", url)
        except Exception as exc:
            await client.aclose()
            logger.warning("Redis unavailable at %s: %s — caching disabled", url, exc)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.warning("Redis GET failed for %r: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
        if not self._client:
            return
        try:
            await self._client.set(key, json.dumps(value), ex=ttl)
        except Exception as exc:
            logger.warning("Redis SET failed for %r: %s", key, exc)


recipe_cache = RecipeCache()
