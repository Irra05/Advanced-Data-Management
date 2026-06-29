#!/usr/bin/env python3
"""
GridSense — Part C.4 benchmark: MongoDB vs PostgreSQL JSONB
-----------------------------------------------------------
Loads the SAME 30 heterogeneous equipment records into a MongoDB collection
and into a PostgreSQL table with a single metadata JSONB column, then times
the three required queries (mean of N runs each) on both engines.

Run against your GridSense docker-compose stack:

    pip install pymongo psycopg2-binary
    python benchmark_c4.py                 # 30 records (assignment spec)
    python benchmark_c4.py --n 100000      # optional scale test
    python benchmark_c4.py --explain       # also print query plans

Connection settings come from environment variables (keep them in your .env):
    PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD
    MONGO_URI   (or MONGO_HOST / MONGO_PORT)
Defaults assume the script runs on the docker host (localhost) with the
ports your compose file publishes (5432, 27017). Adjust if needed.
"""
import argparse
import os
import statistics
import time

# ── The canonical 30 records: 3 equipment types, each a different shape ──────
# SmartMeter  -> firmware_version, rated_voltage, phase, tariff_class
# Transformer -> rating_kVA, manufacturer, cooling, (some) firmware_version
# Switchgear  -> switch_type, insulation, max_current_A
BASE_RECORDS = []

# 15 SmartMeters — mix of firmware "3.x"/"2.x"/none, rated_voltage above/below 230
_sm = [
    ("SM_0001", "3.2.1", 240, "single", "residential"),
    ("SM_0002", "3.0.7", 230, "single", "residential"),
    ("SM_0003", "2.9.0", 250, "three",  "commercial"),
    ("SM_0004", "3.1.4", 400, "three",  "industrial"),
    ("SM_0005", "2.4.1", 120, "single", "residential"),
    ("SM_0006", "3.5.0", 240, "single", "residential"),
    ("SM_0007", None,    230, "single", "residential"),
    ("SM_0008", "3.2.1", 415, "three",  "commercial"),
    ("SM_0009", "2.1.0", 240, "single", "residential"),
    ("SM_0010", "3.0.0", 230, "single", "residential"),
    ("SM_0011", "3.3.2", 240, "single", "residential"),
    ("SM_0012", "2.8.5", 250, "three",  "commercial"),
    ("SM_0013", "3.1.0", 110, "single", "residential"),
    ("SM_0014", None,    240, "single", "residential"),
    ("SM_0015", "3.4.1", 240, "single", "residential"),
]
for mid, fw, rv, phase, tariff in _sm:
    rec = {"asset_id": mid, "type": "SmartMeter", "rated_voltage": rv,
           "phase": phase, "tariff_class": tariff}
    if fw is not None:
        rec["firmware_version"] = fw
    BASE_RECORDS.append(rec)

# 8 Transformers — different shape; a couple carry firmware_version
_tx = [
    ("TX_0001", 400, "ABB",        "ONAN", "3.0.2"),
    ("TX_0002", 630, "Siemens",    "ONAF", None),
    ("TX_0003", 250, "Schneider",  "ONAN", "2.2.0"),
    ("TX_0004", 1000, "ABB",       "OFAF", None),
    ("TX_0005", 400, "Hyundai",    "ONAN", "3.7.1"),
    ("TX_0006", 800, "Siemens",    "ONAF", None),
    ("TX_0007", 315, "Schneider",  "ONAN", None),
    ("TX_0008", 500, "ABB",        "ONAF", "3.1.9"),
]
for aid, kva, man, cool, fw in _tx:
    rec = {"asset_id": aid, "type": "Transformer", "rating_kVA": kva,
           "manufacturer": man, "cooling": cool}
    if fw is not None:
        rec["firmware_version"] = fw
    BASE_RECORDS.append(rec)

# 7 Switchgear — yet another shape; no rated_voltage field at all
_sw = [
    ("SW_0001", "vacuum",  "SF6",  1250),
    ("SW_0002", "air",     "air",   630),
    ("SW_0003", "vacuum",  "SF6",  2000),
    ("SW_0004", "gas",     "SF6",  1600),
    ("SW_0005", "vacuum",  "SF6",  1250),
    ("SW_0006", "air",     "air",   800),
    ("SW_0007", "gas",     "SF6",  3150),
]
for aid, st, ins, amps in _sw:
    BASE_RECORDS.append({"asset_id": aid, "type": "Switchgear",
                         "switch_type": st, "insulation": ins,
                         "max_current_A": amps})

assert len(BASE_RECORDS) == 30


def build_records(n):
    """Return exactly the 30 base records, or pad to n for a scale test."""
    if n <= 30:
        return [dict(r) for r in BASE_RECORDS[:n]]
    out = [dict(r) for r in BASE_RECORDS]
    i = 0
    while len(out) < n:
        clone = dict(BASE_RECORDS[i % 30])
        clone["asset_id"] = f"{clone['asset_id']}_g{len(out)}"
        out.append(clone)
        i += 1
    return out


def time_query(fn, runs):
    """Run fn() `runs` times, return (mean_ms, result_of_last_run)."""
    times = []
    result = None
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.mean(times), result


# ── MongoDB ──────────────────────────────────────────────────────────────────
def run_mongo(records, runs, explain):
    from pymongo import MongoClient
    uri = os.environ.get("MONGO_URI")
    if not uri:
        host = os.environ.get("MONGO_HOST", "localhost")
        port = os.environ.get("MONGO_PORT", "27017")
        uri = f"mongodb://{host}:{port}"
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    coll = client["gridsense_bench"]["equipment"]
    coll_name = f"equipment_{int(time.time())}" # Don't need to use coll.drop()
    coll = client["gridsense_bench"][coll_name]
    #coll.delete_many({})                      # idempotent: clean slate each run
    coll.insert_many([dict(r) for r in records])

    q1 = lambda: list(coll.find({"firmware_version": {"$regex": "^3\\."}}))
    q2 = lambda: list(coll.find({"type": "SmartMeter",
                                 "rated_voltage": {"$gt": 230}}))
    q3 = lambda: list(coll.aggregate([{"$group": {"_id": "$type",
                                                   "count": {"$sum": 1}}}]))

    out = {}
    for name, fn in (("Q1", q1), ("Q2", q2), ("Q3", q3)):
        mean_ms, res = time_query(fn, runs)
        out[name] = (mean_ms, len(res))
    if explain:
        print("\n[Mongo] Q1 plan:",
              coll.find({"firmware_version": {"$regex": "^3\\."}})
                  .explain()["queryPlanner"]["winningPlan"].get("stage"))
        print("[Mongo] Q2 plan:",
              coll.find({"type": "SmartMeter", "rated_voltage": {"$gt": 230}})
                  .explain()["queryPlanner"]["winningPlan"].get("stage"))
    client.close()
    return out


# ── PostgreSQL JSONB ──────────────────────────────────────────────────────────
def run_postgres(records, runs, explain):
    import json
    import psycopg2
    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "gridsense"),
        user=os.environ.get("PGUSER", "gridsense"),
        password=os.environ.get("PGPASSWORD", "gridsense"),
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS equipment_bench;")
    cur.execute("CREATE TABLE equipment_bench (id serial PRIMARY KEY, metadata jsonb);")
    cur.executemany("INSERT INTO equipment_bench (metadata) VALUES (%s);",
                    [(json.dumps(r),) for r in records])

    Q1 = "SELECT count(*) FROM equipment_bench WHERE metadata->>'firmware_version' LIKE '3.%';"
    Q2 = ("SELECT count(*) FROM equipment_bench "
          "WHERE metadata->>'type' = 'SmartMeter' "
          "AND (metadata->>'rated_voltage')::numeric > 230;")
    Q3 = "SELECT metadata->>'type' AS t, count(*) FROM equipment_bench GROUP BY t;"

    def make(sql):
        def fn():
            cur.execute(sql)
            return cur.fetchall()
        return fn

    out = {}
    for name, sql in (("Q1", Q1), ("Q2", Q2), ("Q3", Q3)):
        mean_ms, res = time_query(make(sql), runs)
        # row count for Q1/Q2 is the count value; for Q3 it's number of groups
        n = res[0][0] if name in ("Q1", "Q2") else len(res)
        out[name] = (mean_ms, n)
    if explain:
        for name, sql in (("Q1", Q1), ("Q2", Q2)):
            cur.execute("EXPLAIN " + sql)
            plan = " | ".join(r[0].strip() for r in cur.fetchall())
            print(f"\n[Postgres] {name} plan: {plan}")
    cur.close()
    conn.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="records to load (>=30 pads)")
    ap.add_argument("--runs", type=int, default=10, help="timed runs per query")
    ap.add_argument("--explain", action="store_true", help="print query plans")
    args = ap.parse_args()

    records = build_records(args.n)
    print(f"Loading {len(records)} records into MongoDB and PostgreSQL, "
          f"timing {args.runs} runs per query...\n")

    mongo = pg = None
    try:
        mongo = run_mongo(records, args.runs, args.explain)
    except Exception as e:
        print(f"!! MongoDB step failed: {e}")
    try:
        pg = run_postgres(records, args.runs, args.explain)
    except Exception as e:
        print(f"!! PostgreSQL step failed: {e}")

    print("\n" + "=" * 64)
    print(f"{'Query':<34}{'Mongo (ms)':>14}{'PG JSONB (ms)':>16}")
    print("-" * 64)
    labels = {
        "Q1": "Q1  firmware_version LIKE '3.%'",
        "Q2": "Q2  SmartMeter & rated_voltage>230",
        "Q3": "Q3  count GROUP BY type",
    }
    for k in ("Q1", "Q2", "Q3"):
        m = f"{mongo[k][0]:.3f}" if mongo else "n/a"
        p = f"{pg[k][0]:.3f}" if pg else "n/a"
        print(f"{labels[k]:<34}{m:>14}{p:>16}")
    print("=" * 64)
    if mongo and pg:
        print(f"Result rows  -> Q1: mongo={mongo['Q1'][1]} pg={pg['Q1'][1]} | "
              f"Q2: mongo={mongo['Q2'][1]} pg={pg['Q2'][1]} | "
              f"Q3 groups: mongo={mongo['Q3'][1]} pg={pg['Q3'][1]}")
        print("(Q1 and Q2 row counts should match across engines; "
              "if they don't, the data shapes diverged.)")


if __name__ == "__main__":
    main()
