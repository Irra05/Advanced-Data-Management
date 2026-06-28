from fastapi import APIRouter

from db.redis import get_redis

import json

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
    
    # Add to active list with a max size of 100 characters
    await redis_client.lpush("active_alerts", message)
    await redis_client.ltrim("active_alerts", 0, 99)

    # If the endpoint /latest is not needed, this code isn't needed either
    await redis_client.set(
        "latest_alert",
        message
    )

    return {
        "status": "published",
        "message": message
    }

#   Same as /latest but it gets a range with active alerts 
#   instead of just the latest alert
@router.get("/active")
async def get_active_alerts():

    redis = get_redis()
    alerts = await redis.lrange("active_alerts", 0, -1)

    return {
        "count": len(alerts),
        "alerts": alerts
    }


#!  Is this endpoint needed?

@router.get("/latest")
async def get_latest_alert():

    redis_client = get_redis()

    message = await redis_client.get(
        "latest_alert"
    )

    return {
        "latest_alert": message
    }