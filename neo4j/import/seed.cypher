// ======================================================
// Constraints
// ======================================================

CREATE CONSTRAINT substation_id IF NOT EXISTS
FOR (s:Substation)
REQUIRE s.substation_id IS UNIQUE;

CREATE CONSTRAINT transformer_id IF NOT EXISTS
FOR (t:Transformer)
REQUIRE t.asset_id IS UNIQUE;

CREATE CONSTRAINT meter_id IF NOT EXISTS
FOR (m:SmartMeter)
REQUIRE m.meter_id IS UNIQUE;


// ======================================================
// Grid Supply Point
// ======================================================

MERGE (g:GridSupplyPoint {
    gsp_id: "GSP_NORTH"
})
SET
    g.node_id = "GSP_NORTH",
    g.name = "Northern Grid Supply Point",
    g.voltage_kV = 132,
    g.region = "North Metro";


// ======================================================
// Substation
// ======================================================

MERGE (s:Substation {
    substation_id: "SS_001"
})
SET
    s.node_id = "SS_001",
    s.name = "Volos Primary",
    s.voltage_kV = 11,
    s.lat = 39.358,
    s.lon = 22.938,
    s.commissioned_year = 1998;


// ======================================================
// Transformer
// ======================================================

MERGE (t:Transformer {
    asset_id: "TX_001_A"
})
SET
    t.node_id = "TX_001_A",
    t.name = "Transformer TX_001_A";


// ======================================================
// Smart Meter
// ======================================================

MERGE (m:SmartMeter {
    meter_id: "SM_00001"
})
SET
    m.node_id = "SM_00001",
    m.name = "Smart Meter 00001",
    m.premise_id = "PREM_10001";


// ======================================================
// Relationships
// ======================================================

MATCH (g:GridSupplyPoint {gsp_id:"GSP_NORTH"})
MATCH (s:Substation {substation_id:"SS_001"})
MERGE (g)-[:FEEDS {
    feeder_id:"F_001",
    voltage_kV:11,
    length_km:2.4
}]->(s);

MATCH (s:Substation {substation_id:"SS_001"})
MATCH (t:Transformer {asset_id:"TX_001_A"})
MERGE (s)-[:SUPPLIES {
    cable_id:"CB_001",
    distance_m:320
}]->(t);

MATCH (t:Transformer {asset_id:"TX_001_A"})
MATCH (m:SmartMeter {meter_id:"SM_00001"})
MERGE (t)-[:CONNECTS_TO]->(m);