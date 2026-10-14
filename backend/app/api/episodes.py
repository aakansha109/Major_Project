from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.models.episode import Episode, EpisodeCreate
from app.models.fact import Fact
from app.services.episode_service import episode_service

router = APIRouter(prefix="/episodes", tags=["Episodes"])

@router.post("")
async def create_episode(payload: EpisodeCreate):
    """
    Ingests a conversation utterance into Chronos Memory:
    1. Stores episode node with provenance
    2. Runs hybrid fact extraction (rules first, LLM fallback)
    3. Resolves temporal contradictions against active facts
    4. Commits facts with validity intervals to Temporal Knowledge Graph
    """
    try:
        episode, confirmed_facts, invalidated_facts, telemetry = await episode_service.ingest_episode(payload)
        return {
            "episode": episode,
            "extracted_facts": confirmed_facts,
            "invalidated_facts": invalidated_facts,
            "telemetry": telemetry
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest episode: {str(e)}")

@router.get("", response_model=List[Episode])
def list_episodes(
    session_id: Optional[str] = Query(None, description="Filter by conversation session"),
    limit: int = Query(50, ge=1, le=200)
):
    """List conversation episodes ordered by timestamp"""
    if session_id:
        return episode_service.get_session_episodes(session_id=session_id, limit=limit)
    return episode_service.get_all_episodes(limit=limit)

@router.get("/{episode_id}")
def get_episode(episode_id: str):
    """Retrieve an episode by ID with its associated facts and provenance"""
    result = episode_service.get_episode_with_facts(episode_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")
    return result

