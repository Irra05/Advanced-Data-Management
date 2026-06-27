from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from db.neo4j import get_driver

router = APIRouter(
    prefix="/grid",
    tags=["Grid Topology"]
)


# =====================================================
# Response Models
# =====================================================

from models.graph import (
    AffectedNode,
    FaultImpactResponse
)


# =====================================================
# Endpoints
# =====================================================

@router.get(
    "/fault-impact/{node_id}",
    response_model=FaultImpactResponse
)
async def get_fault_impact(
    node_id: str,
    max_depth: int = 6
):
    """
    Return all nodes that would lose supply
    if node_id trips.
    """

    if not 1 <= max_depth <= 10:
        raise HTTPException(
            status_code=400,
            detail="max_depth must be between 1 and 10"
        )

    cypher = f"""
    MATCH (origin {{node_id: $node_id}})
    MATCH (origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..{max_depth}]->(downstream)

    RETURN
        labels(downstream)[0] AS node_type,
        downstream.node_id AS node_id,
        downstream.name AS name,
        length(
            shortestPath(
                (origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*]-(downstream)
            )
        ) AS depth

    ORDER BY depth
    """

    driver = get_driver()

    async with driver.session(database="neo4j") as session:

        result = await session.run(
            cypher,
            node_id=node_id
        )

        records = await result.data()

    if not records:

        exists = await _node_exists(driver, node_id)

        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Node '{node_id}' not found in topology graph"
            )

    affected = [
        AffectedNode(**record)
        for record in records
    ]

    return FaultImpactResponse(
        origin_id=node_id,
        affected_nodes=affected,
        total_affected=len(affected)
    )
    
    
class RestorePath(BaseModel):
    path_nodes: List[str]
    length: int

class RestorePathsResponse(BaseModel):
    faulted_node: str
    restore_paths: List[RestorePath]
    total_paths: int

@router.get("/restore-paths/{node_id}", response_model=RestorePathsResponse)
async def get_restore_paths(node_id: str, max_depth: int = 6):
    """
    Returns alternative path assuming node_id is out of service.
    """

    if not 1 <= max_depth <= 10:
        raise HTTPException(status_code=400, detail="max_depth must be between 1 and 10")

    cypher = f"""
        MATCH (target {{node_id: $node_id}})
        MATCH path = (source)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..{max_depth}]->(target)
        WHERE NOT (source)<-[:FEEDS|SUPPLIES|CONNECTS_TO]-()
           OR source:GridSupplyPoint
        RETURN [n IN nodes(path) | coalesce(n.node_id, n.gsp_id, n.substation_id, n.asset_id, n.meter_id)] AS path_nodes,
               length(path) AS length
        ORDER BY length
        LIMIT 10
    """

    driver = get_driver()

    async with driver.session(database="neo4j") as session:
        result = await session.run(cypher, node_id=node_id)
        records = await result.data()

    if not records:
        exists = await _node_exists(driver, node_id)
        if not exists:
            raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    paths = [RestorePath(**r) for r in records]

    return RestorePathsResponse(
        faulted_node=node_id,
        restore_paths=paths,
        total_paths=len(paths)
    )


# =====================================================
# Helper Functions
# =====================================================

async def _node_exists(
    driver,
    node_id: str
) -> bool:

    query = """
    MATCH (n {node_id: $node_id})
    RETURN count(n) AS cnt
    """

    async with driver.session(database="neo4j") as session:

        result = await session.run(
            query,
            node_id=node_id
        )

        record = await result.single()

    return record["cnt"] > 0