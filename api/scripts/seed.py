import os
import random
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
    "NEO4J_PASSWORD",
    "admin123"
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
        "MONGO_USER",
        "admin"
    )

    mongo_password = os.getenv(
        "MONGO_PASSWORD",
        "admin123"
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
        password=os.getenv("POSTGRES_PASSWORD", "admin123")
    )

    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS consumer_accounts (
        account_id SERIAL PRIMARY KEY,
        customer_name TEXT,
        email TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id SERIAL PRIMARY KEY,
        account_id INTEGER REFERENCES consumer_accounts(account_id),
        amount NUMERIC,
        status TEXT
    )
    """)

    conn.commit()

    for i in range(100):

        name = fake.name()
        email = f"user{i}@gridsense.com"

        cur.execute("""
        INSERT INTO consumer_accounts (
            customer_name,
            email
        )
        VALUES (%s,%s)
        ON CONFLICT (email) DO NOTHING
        """,
        (name, email))

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
            amount,
            status
        )
        SELECT %s,%s,%s
        WHERE NOT EXISTS (
            SELECT 1
            FROM invoices
            WHERE account_id=%s
        )
        """,
        (
            account_id,
            round(random.uniform(20, 300), 2),
            random.choice(
                ["PAID", "PENDING", "OVERDUE"]
            ),
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

    session.execute("""
    CREATE KEYSPACE IF NOT EXISTS gridsense
    WITH replication = {
        'class':'SimpleStrategy',
        'replication_factor':1
    }
    """)

    session.set_keyspace("gridsense")

    session.execute("""
    CREATE TABLE IF NOT EXISTS sensor_readings (

        sensor_id TEXT,

        reading_time TIMESTAMP,

        metric_type TEXT,

        value FLOAT,

        unit TEXT,

        quality_flag TINYINT,

        PRIMARY KEY (
            (sensor_id),
            reading_time
        )

    ) WITH CLUSTERING ORDER BY (
        reading_time DESC
    )
    """)

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