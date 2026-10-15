from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from app.models.retrieval import Subgraph
from app.db.graph_store import graph_store

router = APIRouter(prefix="/graph", tags=["Graph"])

@router.get("", response_model=Subgraph)
def get_graph(
    as_of: Optional[datetime] = Query(None, description="Time slice filter"),
    limit: int = Query(250, ge=10, le=1000)
):
    """
    Returns graph nodes and edges for visual rendering.
    Supports point-in-time time-slider scrubbing.
    """
    return graph_store.get_full_graph(as_of=as_of, limit=limit)
