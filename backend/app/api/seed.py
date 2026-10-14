from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models.episode import EpisodeCreate
from app.services.episode_service import episode_service
from app.db.graph_store import graph_store

router = APIRouter(prefix="", tags=["Seed & Administration"])

SAMPLE_EPISODES = [
    # Demo Sequence 1: Developer Stack & Relocation Evolution (Flask -> FastAPI, Delhi -> Bangalore)
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="I moved to Delhi in 2021.",
        timestamp=datetime(2021, 2, 15, 11, 30, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="I switched my backend to FastAPI.",
        timestamp=datetime(2023, 4, 10, 14, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="I moved to Bangalore in 2023.",
        timestamp=datetime(2023, 8, 20, 16, 45, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="I now use PostgreSQL.",
        timestamp=datetime(2023, 9, 1, 9, 15, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),
    EpisodeCreate(
        session_id="session_developer_core",
        speaker="user",
        text="I joined Company B in 2024.",
        timestamp=datetime(2024, 1, 10, 10, 30, tzinfo=timezone.utc),
        metadata={"user_id": "u_dev"}
    ),

    # Demo Sequence 2: Alice's journey (Seattle -> London, Microsoft -> DeepMind)
    EpisodeCreate(
        session_id="session_alice",
        speaker="user",
        text="Alice moved to Seattle in 2020.",
        timestamp=datetime(2020, 2, 1, 10, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_001"}
    ),
    EpisodeCreate(
        session_id="session_alice",
        speaker="user",
        text="Alice joined Microsoft in 2020.",
        timestamp=datetime(2020, 3, 15, 11, 30, tzinfo=timezone.utc),
        metadata={"user_id": "u_001"}
    ),
    EpisodeCreate(
        session_id="session_alice",
        speaker="user",
        text="Alice moved to London in 2023.",
        timestamp=datetime(2023, 5, 10, 9, 15, tzinfo=timezone.utc),
        metadata={"user_id": "u_001"}
    ),
    EpisodeCreate(
        session_id="session_alice",
        speaker="user",
        text="Alice joined DeepMind in 2023.",
        timestamp=datetime(2023, 6, 1, 14, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_001"}
    ),

    # Demo Sequence 3: Bob's trajectory (Google -> OpenAI)
    EpisodeCreate(
        session_id="session_bob",
        speaker="user",
        text="Bob joined Google in 2019.",
        timestamp=datetime(2019, 7, 1, 10, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_002"}
    ),
    EpisodeCreate(
        session_id="session_bob",
        speaker="user",
        text="Bob moved to Zurich in 2021.",
        timestamp=datetime(2021, 4, 1, 12, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_002"}
    ),
    EpisodeCreate(
        session_id="session_bob",
        speaker="user",
        text="Bob joined OpenAI in 2024.",
        timestamp=datetime(2024, 1, 15, 16, 20, tzinfo=timezone.utc),
        metadata={"user_id": "u_002"}
    ),

    # Demo Sequence 4: Role promotion & tooling
    EpisodeCreate(
        session_id="session_team",
        speaker="user",
        text="Charlie became a Principal Engineer in 2022.",
        timestamp=datetime(2022, 8, 1, 11, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_003"}
    ),
    EpisodeCreate(
        session_id="session_team",
        speaker="user",
        text="Diana upgraded to a MacBook Pro M3.",
        timestamp=datetime(2024, 2, 10, 15, 0, tzinfo=timezone.utc),
        metadata={"user_id": "u_003"}
    )
]

@router.post("/seed")
async def seed_sample_data():
    """
    Seeds rich multi-turn temporal conversational episodes
    with verified contradictions, career progressions, tech stack migrations, and relocations.
    """
    results = []
    for ep in SAMPLE_EPISODES:
        episode, confirmed_facts, invalidated_facts, telemetry = await episode_service.ingest_episode(ep)
        results.append({
            "episode_id": episode.id,
            "text": episode.text,
            "facts": [f.model_dump() for f in confirmed_facts],
            "invalidated": [f.model_dump() for f in invalidated_facts],
            "telemetry": telemetry
        })
    status = graph_store.get_status()
    return {
        "status": "success",
        "message": f"Successfully seeded {len(SAMPLE_EPISODES)} temporal conversation episodes.",
        "episodes_seeded": len(results),
        "database_metrics": status["metrics"]
    }

@router.post("/reset")
def reset_database():
    """Clears all episodes, facts, and entities from memory for clean testing"""
    graph_store.reset_database()
    return {"status": "success", "message": "Chronos Memory cleared."}
