from fastapi import APIRouter
from fastapi import HTTPException

from db.cassandra import get_session
from models.cassandra import SensorReading
from typing import List, Optional
from datetime import datetime


router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"]
)


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
