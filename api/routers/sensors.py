from fastapi import APIRouter
from fastapi import HTTPException

from db.cassandra import get_session
from models.cassandra import SensorReading
from db.redis import get_redis

from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"]
)


@router.get("/{sensor_id}/summary")
async def get_sensor_summary(sensor_id: str):

    redis = get_redis()
    cache_key = f"summary:{sensor_id}"

    cached = await redis.get(cache_key)
    if cached:
        return {"source": "cache", "summary": json.loads(cached)}

    # Cache miss — calculate from Cassandra
    session = get_session()

    rows = list(session.execute(
        """
        SELECT value FROM gridsense.sensor_readings
        WHERE sensor_id = %s
        LIMIT 3600
        """,
        (sensor_id,)
    ))

    if not rows:
        raise HTTPException(status_code=404, detail="Sensor not found")

    values = [r.value for r in rows]
    summary = {
        "sensor_id": sensor_id,
        "count": len(values),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "avg": round(sum(values) / len(values), 4)
    }

    await redis.set(cache_key, json.dumps(summary), ex=30)  # TTL 30s

    return {"source": "db", "summary": summary}

@router.get("/{sensor_id}/readings")
async def get_sensor_readings(
    sensor_id: str,
    limit: int = 100,
    from_time: Optional[datetime] = None
):

    if limit > 1000:

        raise HTTPException(
            status_code=400,
            detail="limit cannot exceed 1000"
        )

    session = get_session()

    if from_time:
        query = """
        SELECT
            sensor_id,
            reading_time,
            metric_type,
            value,
            unit,
            quality_flag

        FROM gridsense.sensor_readings

        WHERE sensor_id = %s AND reading_time >= %s

        LIMIT %s
        """

        rows = session.execute(
            query,
            (sensor_id, from_time, limit)
        )
        
    else:
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
    
@router.post("/readings", status_code=201)
async def ingest_readings(readings: List[SensorReading]):

    if not readings:
        raise HTTPException(status_code=400, detail="Empty payload")

    session = get_session()

    insert = session.prepare("""
        INSERT INTO gridsense.sensor_readings
            (sensor_id, reading_time, metric_type, value, unit, quality_flag)
        VALUES (?, ?, ?, ?, ?, ?)
    """)

    for r in readings:
        session.execute(insert, (
            r.sensor_id,
            r.reading_time,
            r.metric_type,
            r.value,
            r.unit,
            r.quality_flag
        ))

    return {"inserted": len(readings)}
