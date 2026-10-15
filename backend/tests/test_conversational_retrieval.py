import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.graph_store import graph_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db_before_test():
    """Reset the database before each test to ensure deterministic clean state."""
    graph_store.reset_database()
    yield
    graph_store.reset_database()

def test_health_endpoints():
    """Verify both /health and /api/health respond with 200 and report health metrics."""
    # 1. Root /health
    resp_root = client.get("/health")
    assert resp_root.status_code == 200
    data_root = resp_root.json()
    assert data_root["status"] == "healthy"
    assert "storage" in data_root

    # 2. Prefixed /api/health
    resp_api = client.get("/api/health")
    assert resp_api.status_code == 200
    assert resp_api.json()["status"] == "healthy"

def test_conversational_retrieval_current_and_past_states():
    """
    Ingests multiple sequential episodes and queries:
    1. 'What framework do I use now?' -> Returns active framework (FastAPI)
    2. 'What framework did I use before?' -> Returns prior superseded framework (Flask)
    3. 'What framework did I use in 2022?' -> Returns time-valid framework (Flask)
    4. 'Show the history of my backend framework.' -> Returns timeline (Flask -> FastAPI)
    """
    # Episode 1 (2021-01-10): Initial framework
    ep1_res = client.post("/api/episodes", json={
        "session_id": "conv_test_sess",
        "speaker": "user",
        "text": "My backend framework is Flask.",
        "timestamp": "2021-01-10T10:00:00Z"
    })
    assert ep1_res.status_code == 200
    ep1_data = ep1_res.json()
    ep1_id = ep1_data["episode"]["id"]
    assert len(ep1_data["extracted_facts"]) >= 1

    # Episode 2 (2024-03-01): Framework transition (supersedes Flask)
    ep2_res = client.post("/api/episodes", json={
        "session_id": "conv_test_sess",
        "speaker": "user",
        "text": "I switched my backend framework to FastAPI.",
        "timestamp": "2024-03-01T10:00:00Z"
    })
    assert ep2_res.status_code == 200
    ep2_data = ep2_res.json()
    ep2_id = ep2_data["episode"]["id"]
    assert len(ep2_data["extracted_facts"]) >= 1
    assert len(ep2_data["invalidated_facts"]) >= 1 # Flask was invalidated

    # Test GET /api/episodes/{episode_id}
    ep_get_res = client.get(f"/api/episodes/{ep1_id}")
    assert ep_get_res.status_code == 200
    ep_get_data = ep_get_res.json()
    assert ep_get_data["episode"]["id"] == ep1_id
    assert ep_get_data["fact_count"] >= 1

    # =========================================================================
    # Query 1: Current-state query
    # =========================================================================
    chat_now = client.post("/api/chat", json={
        "message": "What framework do I use now?",
        "session_id": "conv_test_sess"
    })
    assert chat_now.status_code == 200
    data_now = chat_now.json()
    assert data_now["grounded"] is True
    assert data_now["evidence_status"] == "verified_active"
    assert "FastAPI" in data_now["answer"]
    assert len(data_now["supporting_fact_ids"]) >= 1
    assert data_now["temporal_validity"]["is_current"] is True
    assert data_now["retrieval_method"] == "temporal_graph_active"

    # =========================================================================
    # Query 2: Historical previous-state query
    # CRITICAL: Must never answer a historical question using only the latest fact!
    # =========================================================================
    chat_before = client.post("/api/chat", json={
        "message": "What framework did I use before?",
        "session_id": "conv_test_sess"
    })
    assert chat_before.status_code == 200
    data_before = chat_before.json()
    assert data_before["grounded"] is True
    assert data_before["evidence_status"] == "verified_historical"
    assert "Flask" in data_before["answer"]
    assert "Previously" in data_before["answer"]
    assert data_before["temporal_validity"]["is_current"] is False
    assert data_before["retrieval_method"] == "temporal_graph_historical"
    # Ensure supporting fact is indeed the superseded fact
    assert len(data_before["supporting_facts"]) == 1
    assert data_before["supporting_facts"][0]["object"] == "Flask"
    assert data_before["supporting_facts"][0]["status"] == "superseded"

    # =========================================================================
    # Query 3: Point-in-time query
    # =========================================================================
    chat_pit = client.post("/api/chat", json={
        "message": "What was my backend framework in 2022?",
        "session_id": "conv_test_sess"
    })
    assert chat_pit.status_code == 200
    data_pit = chat_pit.json()
    assert data_pit["grounded"] is True
    assert data_pit["evidence_status"] == "verified_point_in_time"
    assert "Flask" in data_pit["answer"]
    assert "2022" in data_pit["answer"]
    assert data_pit["retrieval_method"] == "temporal_graph_point_in_time"

    # =========================================================================
    # Query 4: Timeline / History query
    # =========================================================================
    chat_history = client.post("/api/chat", json={
        "message": "Show the history of my backend framework.",
        "session_id": "conv_test_sess"
    })
    assert chat_history.status_code == 200
    data_history = chat_history.json()
    assert data_history["grounded"] is True
    assert data_history["evidence_status"] == "verified_historical"
    assert "Flask" in data_history["answer"]
    assert "FastAPI" in data_history["answer"]
    assert data_history["retrieval_method"] == "temporal_timeline"
    assert len(data_history["supporting_fact_ids"]) >= 2
    assert data_history["temporal_validity"]["transitions_count"] >= 1

def test_relocation_conversational_queries():
    """Verify relocation questions: 'Where do I live now?' vs 'Where did I live previously?'"""
    # 1. Ingest Seattle in 2020
    client.post("/api/episodes", json={
        "session_id": "alice_sess",
        "speaker": "Alice",
        "text": "Alice moved to Seattle in 2020.",
        "timestamp": "2020-02-01T10:00:00Z"
    })

    # 2. Ingest London in 2023
    client.post("/api/episodes", json={
        "session_id": "alice_sess",
        "speaker": "Alice",
        "text": "Alice moved to London in 2023.",
        "timestamp": "2023-04-15T10:00:00Z"
    })

    # Query current residence
    resp_cur = client.post("/api/chat", json={"message": "Where does Alice live now?"})
    assert resp_cur.status_code == 200
    data_cur = resp_cur.json()
    assert data_cur["grounded"] is True
    assert "London" in data_cur["answer"]

    # Query previous residence
    resp_prev = client.post("/api/chat", json={"message": "Where did Alice live previously?"})
    assert resp_prev.status_code == 200
    data_prev = resp_prev.json()
    assert data_prev["grounded"] is True
    assert "Seattle" in data_prev["answer"]
    assert data_prev["temporal_validity"]["is_current"] is False

    # Query point-in-time
    resp_pit = client.post("/api/chat", json={"message": "Where did Alice live in 2021?"})
    assert resp_pit.status_code == 200
    data_pit = resp_pit.json()
    assert data_pit["grounded"] is True
    assert "Seattle" in data_pit["answer"]

def test_ungrounded_query_rejection():
    """
    CRITICAL: Never claim an answer is grounded unless supporting records were retrieved.
    Queries about facts not in memory must be explicitly flagged as ungrounded.
    """
    resp = client.post("/api/chat", json={
        "message": "What is my favorite ice cream flavor?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounded"] is False
    assert data["confidence"] == 0.0
    assert data["evidence_status"] == "ungrounded"
    assert len(data["supporting_fact_ids"]) == 0
    assert len(data["source_episode_ids"]) == 0
    assert "do not have verified memory records" in data["answer"].lower()

def test_semantic_episode_retrieval_fallback():
    """
    When graph queries alone cannot resolve an open-domain conversational query,
    semantic episode retrieval is invoked and returns source episode IDs.
    """
    # Ingest a conversational episode that is descriptive
    client.post("/api/episodes", json={
        "session_id": "team_sync_sess",
        "speaker": "user",
        "text": "The team agreed that the product launch deadline is November 15th.",
        "timestamp": "2024-05-10T14:00:00Z"
    })

    resp = client.post("/api/chat", json={
        "message": "When is the product launch deadline?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounded"] is True
    assert len(data["source_episode_ids"]) >= 1
    assert data["retrieval_method"] in ["semantic_episode_retrieval", "semantic_graph_retrieval"]
    assert "November 15" in data["answer"] or "launch deadline" in data["answer"]

def test_memory_facts_and_history_endpoints():
    """Verify GET /api/memory/facts and GET /api/memory/history endpoints"""
    # Ingest evolution
    client.post("/api/episodes", json={
        "session_id": "hist_sess",
        "speaker": "user",
        "text": "Bob joined Google in 2019.",
        "timestamp": "2019-06-01T10:00:00Z"
    })
    client.post("/api/episodes", json={
        "session_id": "hist_sess",
        "speaker": "user",
        "text": "Bob joined OpenAI in 2024.",
        "timestamp": "2024-01-10T10:00:00Z"
    })

    # 1. GET /api/memory/facts
    facts_res = client.get("/api/memory/facts?subject=Bob")
    assert facts_res.status_code == 200
    facts = facts_res.json()
    assert len(facts) >= 2

    # 2. GET /api/memory/history
    hist_res = client.get("/api/memory/history?subject=Bob&predicate=works_at")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_events"] >= 2
    assert hist["transitions_count"] >= 1
    assert len(hist["timeline"]) >= 2
    assert hist["timeline"][0]["object"] == "Google"
    assert hist["timeline"][1]["object"] == "OpenAI"

def test_evaluation_results_endpoint():
    """Verify POST /api/evaluation/run and GET /api/evaluation/results"""
    run_res = client.post("/api/evaluation/run")
    assert run_res.status_code == 200

    results_res = client.get("/api/evaluation/results")
    assert results_res.status_code == 200
    data = results_res.json()
    assert "extraction_metrics" in data
    assert "cost_comparison" in data
