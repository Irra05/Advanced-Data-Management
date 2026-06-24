from datetime import datetime
from pydantic import BaseModel


class SensorReading(BaseModel):

    sensor_id: str

    reading_time: datetime

    metric_type: str

    value: float

    unit: str

    quality_flag: int