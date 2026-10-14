from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from app.models.fact import Fact
from app.db.graph_store import graph_store

router = APIRouter(prefix="/facts", tags=["Facts"])

@router.get("", response_model=List[Fact])
def get_facts(
    as_of: Optional[datetime] = Query(None, description="Point-in-time timestamp filter"),
    subject: Optional[str] = Query(None, description="Filter by subject entity"),
    predicate: Optional[str] = Query(None, description="Filter by predicate/relation"),
    only_current: bool = Query(False, description="Filter to only ongoing active facts"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Retrieve facts from Temporal Knowledge Graph with bi-temporal filters:
    - as_of: Point-in-time query returning facts where valid_from <= as_of < valid_to
    - only_current: Returns only presently active facts
    """
    return graph_store.get_facts(
        as_of=as_of,
        subject=subject,
        predicate=predicate,
        only_current=only_current,
        limit=limit
    )

@router.get("/{fact_id}", response_model=Fact)
def get_fact_by_id(fact_id: str):
    """Get single fact by ID with provenance"""
    facts = graph_store.get_facts(limit=1000)
    for f in facts:
        if f.id == fact_id:
            return f
    raise HTTPException(status_code=404, detail="Fact not found")
