from contextlib import asynccontextmanager

from fastapi import FastAPI

from router.sensors import router as sensors_router
from router.grid import router as grid_router
from router.equipment import router as equipment_router
from router.billing import router as billing_router
from router.alerts import router as alerts_router

from db.neo4j import close_driver


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield

    await close_driver()


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