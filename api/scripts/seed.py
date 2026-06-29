import os
import random
import json
from datetime import datetime, timedelta

from faker import Faker

from neo4j import GraphDatabase

from cassandra.cluster import Cluster

from pymongo import MongoClient

import psycopg2

fake = Faker()

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://graph-db:7687"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD"
)

def seed_neo4j():

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=("neo4j", NEO4J_PASSWORD)
    )

    with driver.session() as session:

        session.run("""
        MERGE (g:GridSupplyPoint {
            gsp_id:'GSP_NORTH'
        })
        """)

        for s in range(1, 11):

            substation_id = f"SS_{s:03d}"

            session.run("""
            MERGE (s:Substation {
                substation_id:$id
            })
            SET s.node_id=$id,
                s.name=$name
            """,
            id=substation_id,
            name=f"Substation {s}")

            session.run("""
            MATCH (g:GridSupplyPoint {
                gsp_id:'GSP_NORTH'
            })
            MATCH (s:Substation {
                substation_id:$id
            })
            MERGE (g)-[:FEEDS]->(s)
            """,
            id=substation_id)

        for t in range(1, 41):

            tx_id = f"TX_{t:03d}"

            session.run("""
            MERGE (t:Transformer {
                asset_id:$id
            })
            SET t.node_id=$id,
                t.name=$name
            """,
            id=tx_id,
            name=f"Transformer {t}")

            substation = f"SS_{((t-1)//4)+1:03d}"

            session.run("""
            MATCH (s:Substation {
                substation_id:$sid
            })
            MATCH (t:Transformer {
                asset_id:$tid
            })
            MERGE (s)-[:SUPPLIES]->(t)
            """,
            sid=substation,
            tid=tx_id)

        for m in range(1, 201):

            meter_id = f"SM_{m:05d}"

            session.run("""
            MERGE (m:SmartMeter {
                meter_id:$id
            })
            SET m.node_id=$id,
                m.name=$name
            """,
            id=meter_id,
            name=f"Meter {m}")

            tx = f"TX_{((m-1)//5)+1:03d}"

            session.run("""
            MATCH (t:Transformer {
                asset_id:$tid
            })
            MATCH (m:SmartMeter {
                meter_id:$mid
            })
            MERGE (t)-[:CONNECTS_TO]->(m)
            """,
            tid=tx,
            mid=meter_id)

    driver.close()



def seed_mongo():

    mongo_user = os.getenv(
        "MONGO_USER"
    )

    mongo_password = os.getenv(
        "MONGO_PASSWORD"
    )

    mongo_host = os.getenv(
        "MONGO_HOST",
        "catalog-db"
    )

    client = MongoClient(
        f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:27017"
    )

    db = client["gridsense"]

    equipment = db["equipment"]

    for i in range(1, 11):

        asset_id = f"TX_{i:03d}"

        equipment.update_one(
            {"asset_id": asset_id},
            {
                "$set": {
                    "asset_id": asset_id,
                    "equipment_type": "transformer",
                    "manufacturer": random.choice(
                        ["ABB", "Siemens", "GE"]
                    ),
                    "rating_kVA": random.choice(
                        [250, 400, 630]
                    )
                }
            },
            upsert=True
        )

    for i in range(1, 11):

        asset_id = f"RELAY_{i:03d}"

        equipment.update_one(
            {"asset_id": asset_id},
            {
                "$set": {
                    "asset_id": asset_id,
                    "equipment_type": "relay",
                    "trip_count": random.randint(0, 50),
                    "firmware": f"v{random.randint(1,5)}.{random.randint(0,9)}"
                }
            },
            upsert=True
        )

    for i in range(1, 11):

        asset_id = f"SM_{i:05d}"

        equipment.update_one(
            {"asset_id": asset_id},
            {
                "$set": {
                    "asset_id": asset_id,
                    "equipment_type": "smart_meter",
                    "phase": random.choice(
                        ["single", "three"]
                    ),
                    "installation_year": random.randint(
                        2018,
                        2025
                    )
                }
            },
            upsert=True
        )

    client.close()



def seed_postgres():

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "billing-db"),
        database=os.getenv("POSTGRES_DB", "gridsense"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS consumer_accounts (
        account_id SERIAL PRIMARY KEY,
        premise_id TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        tariff_rules JSONB DEFAULT '{}'
    )
    """)
    
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tariff_gin
    ON consumer_accounts USING GIN (tariff_rules)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id             SERIAL PRIMARY KEY,
        account_id             INTEGER REFERENCES consumer_accounts(account_id),
        billing_period_start   DATE,
        billing_period_end     DATE,
        consumption_kwh        NUMERIC,
        base_charge            NUMERIC,
        energy_charge          NUMERIC,
        regulatory_surcharge   NUMERIC,
        time_of_use_adjustment NUMERIC,
        total_amount           NUMERIC,
        status                 TEXT DEFAULT 'PENDING'
    )
    """)

    conn.commit()

    for i in range(100):

        premise_id = f"PREM_{i+10001}"
        name = fake.name()
        email = f"user{i}@gridsense.com"
        tariff_rules = json.dumps({
            "band": random.choice(["A","B","C"]), 
            "tou_enabled": random.choice([True, False])
        })

        cur.execute("""
        INSERT INTO consumer_accounts (
            premise_id, customer_name, email, tariff_rules
        )
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (email) DO NOTHING
        """,
        (premise_id, name, email, tariff_rules))

    conn.commit()

    cur.execute("""
    SELECT account_id
    FROM consumer_accounts
    """)

    accounts = cur.fetchall()

    for account in accounts:

        account_id = account[0]

        cur.execute("""
        INSERT INTO invoices (
            account_id,
            billing_period_start,
            billing_period_end,
            consumption_kwh,
            base_charge,
            energy_charge,
            regulatory_surcharge,
            time_of_use_adjustment,
            total_amount,
            status
        )
        SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1 
            FROM invoices 
            WHERE account_id = %s
        )
        """,
        (
            account_id,
            fake.date_between(start_date="-3m", end_date="-1m"),
            fake.date_between(start_date="-1m", end_date="today"),
            round(random.uniform(50, 500), 2),
            9.00,
            round(random.uniform(10, 80), 2),
            round(random.uniform(1, 5), 2),
            round(random.uniform(-5, 5), 2),
            round(random.uniform(20, 300), 2),
            random.choice(["PAID", "PENDING", "OVERDUE"]),
            account_id
        ))

    conn.commit()

    cur.close()
    conn.close()



def seed_cassandra():

    cluster = Cluster(
        [os.getenv(
            "CASSANDRA_HOST",
            "timeseries-db"
        )]
    )

    session = cluster.connect()

    
    session.set_keyspace("gridsense")


    insert_query = session.prepare("""
    INSERT INTO sensor_readings (
        sensor_id,
        reading_time,
        metric_type,
        value,
        unit,
        quality_flag
    )
    VALUES (
        ?, ?, ?, ?, ?, ?
    )
    """)

    sensor_ids = [
        f"SENSOR_{i:03d}"
        for i in range(1, 21)
    ]

    base_time = datetime.now()

    for sensor_id in sensor_ids:

        existing = session.execute(
            """
            SELECT COUNT(*)
            FROM sensor_readings
            WHERE sensor_id=%s
            """,
            [sensor_id]
        )

        count = existing.one()[0]

        if count >= 2500:
            continue

        for i in range(2500):

            reading_time = (
                base_time -
                timedelta(minutes=i)
            )

            session.execute(
                insert_query,
                (
                    sensor_id,
                    reading_time,
                    random.choice([
                        "voltage",
                        "current",
                        "temperature",
                        "power_factor"
                    ]),
                    round(
                        random.uniform(
                            10,
                            250
                        ),
                        2
                    ),
                    "unit",
                    0
                )
            )

    cluster.shutdown()





def main():

    print("Seeding Neo4j...")
    seed_neo4j()

    print("Seeding MongoDB...")
    seed_mongo()

    print("Seeding PostgreSQL...")
    seed_postgres()

    print("Seeding Cassandra...")
    seed_cassandra()

    print("Seed completed.")


if __name__ == "__main__":
    main()