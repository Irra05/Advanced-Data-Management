import time
import statistics
import requests
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:8000/grid/fault-impact/SS_001"

ITERATIONS = 30

results = []

for depth in range(1,9):

    latencies = []

    print(f"Testing depth {depth}")

    for _ in range(ITERATIONS):

        start = time.perf_counter()

        response = requests.get(
            BASE_URL,
            params={
                "max_depth": depth
            }
        )

        elapsed = (time.perf_counter()-start)*1000

        if response.status_code == 200:
            latencies.append(elapsed)

    median = statistics.median(latencies)

    latencies.sort()

    p95 = latencies[int(len(latencies)*0.95)-1]

    results.append((depth,median,p95))

print()

print("Depth | Median | P95")

for r in results:

    print(
        f"{r[0]:>5} | {r[1]:>7.2f} | {r[2]:>7.2f}"
    )

depths=[r[0] for r in results]
medians=[r[1] for r in results]
p95=[r[2] for r in results]

plt.plot(depths,medians,label="Median")
plt.plot(depths,p95,label="P95")

plt.xlabel("Max Depth")
plt.ylabel("Latency (ms)")
plt.title("Neo4j Traversal Latency")

plt.legend()

plt.grid(True)

plt.savefig("neo4j_latency.png")

plt.show()