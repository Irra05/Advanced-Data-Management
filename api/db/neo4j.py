import os

from neo4j import AsyncGraphDatabase

_driver = None


def init_driver():

    global _driver

    if _driver is None:

        uri = os.getenv(
            "NEO4J_URI",
            "bolt://graph-db:7687"
        )

        password = os.getenv(
            "NEO4J_PASSWORD",
            "admin123"
        )

        _driver = AsyncGraphDatabase.driver(
            uri,
            auth=("neo4j", password)
        )

    return _driver


def get_driver():

    return init_driver()


async def close_driver():

    global _driver

    if _driver is not None:
        await _driver.close()
        _driver = None