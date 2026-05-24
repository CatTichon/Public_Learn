from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import get_settings


async def get_redis() -> AsyncGenerator[Redis, None]:
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()
