"""Redis connection manager."""

import redis.asyncio as redis

from app.config import settings

# Global Redis connection pool
redis_pool: redis.ConnectionPool = None
redis_client: redis.Redis = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection pool."""
    global redis_pool, redis_client
    redis_pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    return redis_client


async def close_redis() -> None:
    """Close Redis connections."""
    global redis_client, redis_pool
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()


def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client
