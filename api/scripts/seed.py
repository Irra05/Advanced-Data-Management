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