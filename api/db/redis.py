import os

import redis.asyncio as redis

_client = None


def get_redis():

    global _client

    if _client is None:

        host = os.getenv(
            "REDIS_HOST",
            "cache"
        )

        _client = redis.Redis(
            host=host,
            port=6379,
            decode_responses=True
        )

    return _client


async def close_redis():

    global _client

    if _client is not None:
        await _client.close()