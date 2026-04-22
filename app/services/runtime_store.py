import time
import logging
from collections import defaultdict, deque
from typing import Any, Protocol


class RateLimitStore(Protocol):
    async def is_limited(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        ...

    async def ping(self) -> bool:
        ...


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    async def is_limited(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        now = time.monotonic()
        bucket = self._events[key]

        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            return True

        bucket.append(now)
        return False

    async def ping(self) -> bool:
        return True


class CacheStore(Protocol):
    async def get(self, key: str) -> Any | None:
        ...

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def ping(self) -> bool:
        ...


class MemoryCacheStore:
    supports_complex_values = True

    def __init__(self) -> None:
        self._items: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None

        value, expires_at = item
        if expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None

        return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._items[key] = (value, time.monotonic() + ttl_seconds)

    async def delete(self, key: str) -> None:
        self._items.pop(key, None)

    async def ping(self) -> bool:
        return True


class RedisRuntimeStore:
    supports_complex_values = False
    supports_json_values = True

    def __init__(self, redis_url: str) -> None:
        try:
            from redis.asyncio import Redis
        except ImportError as error:
            raise RuntimeError(
                "Redis backend uchun 'redis' paketi o'rnatilishi kerak."
            ) from error

        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def is_limited(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        redis_key = f"rate:{key}"
        current = await self.redis.incr(redis_key)
        if current == 1:
            await self.redis.expire(redis_key, window_seconds)
        return int(current) > limit

    async def get(self, key: str) -> Any | None:
        return await self.redis.get(f"cache:{key}")

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self.redis.set(f"cache:{key}", str(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.redis.delete(f"cache:{key}")

    async def ping(self) -> bool:
        return bool(await self.redis.ping())


def build_runtime_stores(redis_url: str | None = None) -> tuple[RateLimitStore, CacheStore]:
    if redis_url:
        try:
            redis_store = RedisRuntimeStore(redis_url)
            return redis_store, redis_store
        except RuntimeError:
            logging.getLogger(__name__).warning(
                "Redis backend ishga tushmadi. Memory runtime store ishlatiladi.",
                exc_info=True,
            )

    return MemoryRateLimitStore(), MemoryCacheStore()


try:
    from app.core.config import REDIS_URL
except Exception:
    REDIS_URL = ""

rate_limit_store, cache_store = build_runtime_stores(REDIS_URL)
