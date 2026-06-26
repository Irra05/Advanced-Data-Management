import os
import asyncpg

_pool = None


async def get_pool():

    global _pool

    if _pool is None:

        _pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "billing-db"),
            database=os.getenv("POSTGRES_DB", "gridsense"),
            user=os.getenv("POSTGRES_USER", "admin"),
            password=os.getenv("POSTGRES_PASSWORD", "admin123"),
            min_size=1,
            max_size=5
        )

    return _pool


async def close_pool():

    global _pool

    if _pool:
        await _pool.close()

    _pool = None