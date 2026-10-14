import pytest
from datetime import datetime, timezone
from app.models.episode import EpisodeCreate
from app.services.episode_service import episode_service
from app.services.retrieval_service import retrieval_service
from app.services.inference_service import inference_service
from app.models.retrieval import RetrievalQuery
from app.models.inference import InferenceRequest
from app.db.graph_store import graph_store

@pytest.mark.asyncio
async def test_retrieval_and_inference_time_travel():
    graph_store.reset_database()

    # Ingest episode 1: Alice lived in Seattle in 2020
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_qa",
        speaker="user",
        text="Alice moved to Seattle in 2020.",
        timestamp=datetime(2020, 2, 1, tzinfo=timezone.utc)
    ))

    # Ingest episode 2: Alice moved to London in 2023
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_qa",
        speaker="user",
        text="Alice moved to London in 2023.",
        timestamp=datetime(2023, 4, 1, tzinfo=timezone.utc)
    ))

    # Historical Query: Where did Alice live in 2021?
    resp_2021 = inference_service.infer_answer(InferenceRequest(
        query="Where did Alice live?",
        as_of=datetime(2021, 6, 1, tzinfo=timezone.utc)
    ))
    assert "Seattle" in resp_2021.answer
    assert resp_2021.confidence > 0.8

    # Present Query: Where does Alice live now?
    resp_now = inference_service.infer_answer(InferenceRequest(
        query="Where does Alice live?",
        as_of=datetime(2026, 1, 1, tzinfo=timezone.utc)
    ))
    assert "London" in resp_now.answer

    # Semantic retrieval test
    ret_res = retrieval_service.retrieve(RetrievalQuery(
        query="Tell me about Alice's residence",
        top_k=5
    ))
    assert len(ret_res.matched_facts) >= 1
    assert ret_res.matched_facts[0].subject == "Alice"
    assert len(ret_res.subgraph.nodes) >= 2
