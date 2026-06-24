from fastapi import APIRouter

from db.redis import get_redis

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.post("/publish")
async def publish_alert(
    message: str
):

    redis_client = get_redis()

    await redis_client.publish(
        "grid_alerts",
        message
    )

    await redis_client.set(
        "latest_alert",
        message
    )

    return {
        "status": "published",
        "message": message
    }


@router.get("/latest")
async def get_latest_alert():

    redis_client = get_redis()

    message = await redis_client.get(
        "latest_alert"
    )

    return {
        "latest_alert": message
    }