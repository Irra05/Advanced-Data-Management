from fastapi import APIRouter
from fastapi import HTTPException

from db.cassandra import get_session

router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"]
)


@router.get("/{sensor_id}/readings")
async def get_sensor_readings(
    sensor_id: str,
    limit: int = 100
):

    if limit > 1000:

        raise HTTPException(
            status_code=400,
            detail="limit cannot exceed 1000"
        )

    session = get_session()

    query = """
    SELECT
        sensor_id,
        reading_time,
        metric_type,
        value,
        unit,
        quality_flag

    FROM gridsense.sensor_readings

    WHERE sensor_id = %s

    LIMIT %s
    """

    rows = session.execute(
        query,
        (sensor_id, limit)
    )

    result = []

    for row in rows:

        result.append({
            "sensor_id": row.sensor_id,
            "reading_time": row.reading_time,
            "metric_type": row.metric_type,
            "value": row.value,
            "unit": row.unit,
            "quality_flag": row.quality_flag
        })

    return {
        "sensor_id": sensor_id,
        "count": len(result),
        "readings": result
    }