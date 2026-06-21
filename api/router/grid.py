# api/routers/grid.py (excerpt)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from db.neo4j import get_driver

router = APIRouter(prefix="/grid", tags=["Grid Topology"])

class AffectedNode(BaseModel):
    node_id: str
    node_type: str
    name: str
    depth: int
class FaultImpactResponse(BaseModel):
    origin_id: str
    affected_nodes: List[AffectedNode]
    total_affected: int
    
@router.get("/fault-impact/{node_id}", response_model=FaultImpactResponse)
async def get_fault_impact(node_id: str, max_depth: int = 6):
    """
    Return all nodes that would lose supply if node_id trips.
    Uses variable-length Cypher traversal — depth is bounded to prevent
    accidental full-graph scans on malformed input.
    """
    if max_depth > 10:
        raise HTTPException(status_code=400,
            detail="max_depth cannot exceed 10 to protect query performance")
        
    cypher = """
        MATCH (origin {node_id: $node_id})
        MATCH (origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..$depth]->(downstream)
        RETURN labels(downstream)[0] AS node_type,
        downstream.node_id AS node_id,
        downstream.name
        AS name,
        length(
            shortestPath((origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*]-(downstream))
        ) AS depth
        ORDER BY depth
    """
    
    driver = get_driver()
    async with driver.session(database="neo4j") as session:
        result = await session.run(cypher,
            node_id=node_id, depth=max_depth)
        records = await result.data()
        
    if not records and not await _node_exists(driver, node_id):
        raise HTTPException(status_code=404,
            detail=f"Node '{node_id}' not found in topology graph")
        
    affected = [AffectedNode(**r) for r in records]
    return FaultImpactResponse(
        origin_id=node_id,
        affected_nodes=affected,
        total_affected=len(affected)
    )
