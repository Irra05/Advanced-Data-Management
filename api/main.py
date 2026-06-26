from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers.sensors import router as sensors_router
from routers.grid import router as grid_router
from routers.equipment import router as equipment_router
from routers.billing import router as billing_router
from routers.alerts import router as alerts_router

from db.neo4j import close_driver
from db.mongo import close_mongo
from db.postgres import close_pool
from db.cassandra import close_session
from db.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield

    await close_driver()
    await close_mongo()
    await close_pool()
    close_session()
    await close_redis()


app = FastAPI(
    title="GridSense API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(sensors_router)
app.include_router(grid_router)
app.include_router(equipment_router)
app.include_router(billing_router)
app.include_router(alerts_router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "GridSense API"
    }