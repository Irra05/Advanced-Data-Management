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