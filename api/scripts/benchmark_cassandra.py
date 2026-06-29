import time
import random
from datetime import datetime

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel

cluster = Cluster(["localhost"])
session = cluster.connect("gridsense")

consistency_levels = {
    "ONE": ConsistencyLevel.ONE,
    "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
    "ALL": ConsistencyLevel.ALL,
}

NUM_WRITES = 5000

for name, level in consistency_levels.items():

    statement = SimpleStatement(
        """
        INSERT INTO sensor_readings
        (
            sensor_id,
            reading_time,
            metric_type,
            value,
            unit,
            quality_flag
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        consistency_level=level
    )

    latencies = []

    errors = 0

    start = time.time()

    for i in range(NUM_WRITES):

        try:

            t0 = time.time()

            session.execute(
                statement,
                (
                    f"BENCH_{random.randint(1,20)}",
                    datetime.now(),
                    "voltage",
                    random.uniform(220,240),
                    "V",
                    0
                )
            )

            latencies.append(
                (time.time()-t0)*1000
            )

        except Exception:

            errors += 1

    total = time.time()-start

    throughput = NUM_WRITES/total

    latencies.sort()

    p50 = latencies[int(len(latencies)*0.50)]

    p95 = latencies[int(len(latencies)*0.95)]

    print("="*50)
    print(name)
    print(f"Throughput : {throughput:.2f} events/s")
    print(f"P50 latency: {p50:.2f} ms")
    print(f"P95 latency: {p95:.2f} ms")
    print(f"Errors      : {errors}")

cluster.shutdown()