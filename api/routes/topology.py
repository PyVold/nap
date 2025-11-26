"""
Network Topology Discovery API - Placeholder
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.deps import get_db

router = APIRouter(prefix="/topology", tags=["topology"])


@router.get("/graph")
def get_topology_graph():
    """Get topology graph - Placeholder"""
    return {
        "nodes": [],
        "links": [],
        "total_nodes": 0,
        "total_links": 0
    }


@router.get("/nodes")
def list_nodes():
    """List nodes - Placeholder"""
    return []


@router.post("/discover")
def start_discovery(seed_device_ids: list, max_depth: int = 5):
    """Start discovery - Placeholder"""
    return {
        "session_id": "placeholder",
        "status": "initiated",
        "message": "Topology discovery not yet implemented"
    }


@router.get("/discovery/{session_id}")
def get_discovery_status(session_id: str):
    """Get discovery status - Placeholder"""
    return {
        "session_id": session_id,
        "status": "not_implemented",
        "progress_percentage": 0,
        "nodes_discovered": 0,
        "links_discovered": 0
    }
