# GridSense — Smart Power Grid Analytics & Fault Management

A polyglot-persistence platform for real-time monitoring, fault analysis, and billing of smart power grid infrastructure.

## Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Time-series | Apache Cassandra 4.1 | Sensor readings (50 K+) |
| Graph | Neo4j 5 Community | Network topology & fault traversal |
| Documents | MongoDB 7 | Equipment catalogue |
| Relational | PostgreSQL 15 | Consumer billing & accounts (ACID) |
| Cache / Pub-Sub | Redis 7 | Cached summaries, real-time alerts |
| API | FastAPI + Python 3.11 | Single REST gateway |

## Getting Started

```bash
# 1. Set up environment variables
cp .env.example .env
# Edit .env and fill in passwords

# 2. Start all services (first run: allow ~3–5 min for Cassandra to initialise)
docker compose up --build

# 3. Load seed data (in a separate terminal)
docker compose run --rm seed
```

The API will be available at `http://localhost:8000`  
Interactive docs (Swagger UI): `http://localhost:8000/docs`  
Neo4j Browser: `http://localhost:7474`

## API Endpoints

### Sensors — Cassandra
| Method | Path | Description |
|---|---|---|
| `POST` | `/sensors/readings` | Ingest a batch of sensor readings |
| `GET` | `/sensors/{sensor_id}/readings` | Retrieve last N readings for a sensor |
| `GET` | `/sensors/{sensor_id}/summary` | Cached min/max/avg summary (Redis TTL 30 s) |

### Grid Topology — Neo4j
| Method | Path | Description |
|---|---|---|
| `GET` | `/grid/fault-impact/{node_id}` | All downstream nodes that lose supply if node_id trips |
| `GET` | `/grid/restore-paths/{node_id}` | Alternative supply paths to a faulted node |
| `POST` | `/grid/nodes` | Add a node to the topology graph |
| `POST` | `/grid/relationships` | Add a directed relationship between two nodes |

### Equipment — MongoDB
| Method | Path | Description |
|---|---|---|
| `POST` | `/equipment/` | Register a new asset |
| `GET` | `/equipment/{asset_id}` | Retrieve an asset record |
| `PATCH` | `/equipment/{asset_id}` | Update asset fields |

### Billing — PostgreSQL
| Method | Path | Description |
|---|---|---|
| `GET` | `/billing/account/{premise_id}` | Retrieve a consumer account |
| `POST` | `/billing/invoice` | Generate an invoice (ACID transaction) |

### Alerts — Redis
| Method | Path | Description |
|---|---|---|
| `POST` | `/alerts/publish` | Publish an alert to Pub/Sub and active list |
| `GET` | `/alerts/active` | List currently active alerts |

## Usage Examples

```bash
# Ingest a sensor reading
curl -X POST http://localhost:8000/sensors/readings \
  -H "Content-Type: application/json" \
  -d '[{
        "sensor_id": "SENSOR_001",
        "reading_time": "2025-06-01T10:00:00Z",
        "metric_type": "voltage",
        "value": 231.4,
        "unit": "V",
        "quality_flag": 0
      }]'

# Get fault impact for a substation
curl http://localhost:8000/grid/fault-impact/SS_001

# Generate an invoice (ACID transaction)
curl -X POST http://localhost:8000/billing/invoice \
  -H "Content-Type: application/json" \
  -d '{
        "premise_id": "PREM_10001",
        "billing_period_start": "2025-05-01",
        "billing_period_end": "2025-05-31",
        "consumption_kwh": 312.5,
        "base_charge": 9.00,
        "energy_charge": 37.50,
        "regulatory_surcharge": 2.10,
        "time_of_use_adjustment": -1.50
      }'
```

## Project Structure

```
.
├── api/
│   ├── db/            # Database connection modules
│   ├── models/        # Pydantic request/response models
│   ├── routers/       # FastAPI route handlers
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── cql/
│   └── init.cql       # Cassandra keyspace & table definitions
├── neo4j/
│   └── import/
│       └── seed.cypher  # Neo4j constraints & representative subgraph
├── postgres/
│   └── init.sql       # PostgreSQL schema (accounts & invoices)
├── scripts/
│   └── seed.py        # Data seeder (50 K readings, 200 graph nodes, …)
├── docker-compose.yml
├── .env.example
└── README.md
```
