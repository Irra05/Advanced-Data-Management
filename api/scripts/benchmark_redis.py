import time
import statistics
import requests

URL="http://localhost:8000/sensors/SENSOR_001/summary"

ITERATIONS=500

def benchmark():

    latencies=[]

    for _ in range(ITERATIONS):

        start=time.perf_counter()

        requests.get(URL)

        elapsed=(time.perf_counter()-start)*1000

        latencies.append(elapsed)

    latencies.sort()

    return (
        statistics.median(latencies),
        latencies[int(len(latencies)*0.95)-1],
        latencies[int(len(latencies)*0.99)-1]
    )


print("----- Cold Cache -----")

cold=benchmark()

print(cold)

print("Waiting 31 seconds...")

time.sleep(31)

print("----- Warm Cache -----")

requests.get(URL)

warm=benchmark()

print(warm)