import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.graph_store import graph_store

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chronos-temporal-memory"
    assert "storage" in data

def test_seed_and_query_flow():
    # 1. Reset
    resp_reset = client.post("/api/reset")
    assert resp_reset.status_code == 200

    # 2. Ingest episode via API
    resp_ep = client.post("/api/episodes", json={
        "session_id": "api_test_session",
        "speaker": "user",
        "text": "Bob joined Google in 2019."
    })
    assert resp_ep.status_code == 200
    data_ep = resp_ep.json()
    assert len(data_ep["extracted_facts"]) >= 1
    assert data_ep["extracted_facts"][0]["subject"] == "Bob"

    # 3. Retrieve facts
    resp_facts = client.get("/api/facts?subject=Bob")
    assert resp_facts.status_code == 200
    facts = resp_facts.json()
    assert len(facts) >= 1

    # 4. Graph endpoint
    resp_graph = client.get("/api/graph")
    assert resp_graph.status_code == 200
    graph = resp_graph.json()
    assert len(graph["nodes"]) >= 2

    # 5. Inference
    resp_inf = client.post("/api/inference", json={
        "query": "Where does Bob work?"
    })
    assert resp_inf.status_code == 200
    inf_data = resp_inf.json()
    assert "Google" in inf_data["answer"]

def test_evaluation_run():
    resp_eval = client.post("/api/evaluation/run")
    assert resp_eval.status_code == 200
    data = resp_eval.json()
    assert data["extraction_metrics"]["f1_score"] >= 0.8
    assert data["contradiction_metrics"]["accuracy_score"] >= 0.8
    assert data["cost_comparison"]["token_savings_percent"] > 50.0

def test_compare_strategies_api():
    resp_comp = client.post("/api/evaluation/compare-strategies")
    assert resp_comp.status_code == 200
    data = resp_comp.json()
    assert "strategy_a" in data
    assert "strategy_b" in data
    assert data["token_reduction_percent"] > 0
    assert "hypothesis_tested" in data
    assert "limitations" in data
    assert len(data["limitations"]) > 0

    resp_latest = client.get("/api/evaluation/comparison/latest")
    assert resp_latest.status_code == 200
    latest_data = resp_latest.json()
    assert latest_data["dataset_size"] == data["dataset_size"]
