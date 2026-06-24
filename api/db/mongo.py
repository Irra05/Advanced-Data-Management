import os

from motor.motor_asyncio import AsyncIOMotorClient

_client = None
_database = None


def get_database():

    global _client
    global _database

    if _database is None:

        user = os.getenv("MONGO_USER", "admin")
        password = os.getenv("MONGO_PASSWORD", "admin123")
        host = os.getenv("MONGO_HOST", "catalog-db")

        uri = (
            f"mongodb://{user}:{password}"
            f"@{host}:27017"
        )

        _client = AsyncIOMotorClient(uri)

        _database = _client["gridsense"]

    return _database


async def close_mongo():

    global _client

    if _client:
        _client.close()