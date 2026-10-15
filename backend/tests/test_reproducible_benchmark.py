import pytest
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from benchmarks.dataset_loader import load_benchmark_dataset, BenchmarkDataset
from benchmarks.engine import BenchmarkEngine
from benchmarks.baselines.chronos_hybrid import ChronosHybridStrategy
from benchmarks.baselines.always_llm import AlwaysLLMStrategy
from benchmarks.baselines.mem0_adapter import Mem0BaselineStrategy
from benchmarks.baselines.graphiti_adapter import GraphitiBaselineStrategy
from benchmarks.metrics import (
    calculate_set_precision_recall_f1,
    check_stale_fact_errors,
    compute_distribution_metrics
)

client = TestClient(app)

def test_dataset_schema_and_scenarios_count():
    """Verify that dataset contains at least 30 scenarios and all required categories."""
    dataset = load_benchmark_dataset()
    assert len(dataset.scenarios) >= 30, f"Expected >= 30 scenarios, found {len(dataset.scenarios)}"
    assert dataset.target_total_capacity >= 150
    
    categories = set(s.category for s in dataset.scenarios)
    required_categories = {
        "software_stacks",
        "location_changes",
        "employment",
        "projects",
        "non_conflicting_additions",
        "repeated_facts",
        "ambiguous_inputs",
        "adversarial"
    }
    missing = required_categories - categories
    assert not missing, f"Missing required categories in benchmark dataset: {missing}"
    
    for s in dataset.scenarios:
        assert s.scenario_id.startswith("scen_")
        assert len(s.episode_sequence) >= 1
        assert isinstance(s.expected_active_facts, list)
        assert isinstance(s.expected_historical_facts, list)
        assert len(s.expected_test_queries) >= 1
        for q in s.expected_test_queries:
            assert q.target_temporal_state in ["current", "historical", "point_in_time", "evolution"]

def test_stale_fact_detection():
    """Verify that stale fact detection flags forbidden keywords."""
    res1 = check_stale_fact_errors(
        answer="Your current framework is FastAPI (previously Flask).",
        target_temporal_state="current",
        expected_keywords=["FastAPI"],
        forbidden_keywords=["Flask is your current"]
    )
    assert res1["passed"] is True
    assert res1["stale_fact_error"] is False

    res2 = check_stale_fact_errors(
        answer="Flask is your current backend framework.",
        target_temporal_state="current",
        expected_keywords=["FastAPI"],
        forbidden_keywords=["Flask is your current"]
    )
    assert res2["passed"] is False
    assert res2["stale_fact_error"] is True

def test_metric_calculations():
    """Verify precision, recall, and F1 calculations."""
    extracted = [
        {"subject": "User", "predicate": "backend_framework", "object": "FastAPI"}
    ]
    expected = [
        {"subject": "User", "predicate": "backend_framework", "object": "FastAPI"}
    ]
    metrics = calculate_set_precision_recall_f1(extracted, expected)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0

    dist = compute_distribution_metrics([10.0, 20.0, 30.0, 40.0, 50.0])
    assert dist["mean_ms"] == 30.0
    assert dist["median_ms"] == 30.0

@pytest.mark.asyncio
async def test_unavailable_baselines_reported_truthfully():
    """Verify that unavailable external baselines report not_run without inventing results."""
    mem0 = Mem0BaselineStrategy()
    is_avail, reason = mem0.is_available()
    assert is_avail is False
    assert "mem0ai" in reason or "OPENAI_API_KEY" in reason

    graphiti = GraphitiBaselineStrategy()
    is_avail_g, reason_g = graphiti.is_available()
    assert is_avail_g is False
    assert "graphiti-core" in reason_g or "OPENAI_API_KEY" in reason

@pytest.mark.asyncio
async def test_benchmark_engine_run_subset(tmp_path):
    """Run benchmark engine on 3 scenarios and verify result structures and exports."""
    dataset = load_benchmark_dataset()
    engine = BenchmarkEngine(
        dataset=dataset,
        strategies=[ChronosHybridStrategy(), AlwaysLLMStrategy(), Mem0BaselineStrategy()],
        output_dir=str(tmp_path)
    )
    results = await engine.run(limit=3)
    
    assert results["total_scenarios_evaluated"] == 3
    assert "chronos_hybrid" in results["strategies_evaluated"]
    assert "always_llm" in results["strategies_evaluated"]
    assert "mem0" in results["strategies_evaluated"]
    
    # Mem0 should be not_run
    assert results["strategies_evaluated"]["mem0"]["status"] == "not_run"
    
    # Chronos should be completed
    chronos_res = results["strategies_evaluated"]["chronos_hybrid"]
    assert chronos_res["status"] == "completed"
    assert "summary_metrics" in chronos_res
    assert chronos_res["summary_metrics"]["tokens"]["total_tokens"] >= 0
    
    # Verify exported files exist
    assert os.path.exists(results["exported_files"]["json"])
    assert os.path.exists(results["exported_files"]["csv"])

def test_benchmark_api_endpoints():
    """Verify API endpoints for scenario inspection and latest benchmark results."""
    resp = client.get("/api/evaluation/benchmark/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_scenarios"] >= 30
    assert len(data["scenarios"]) >= 30

    resp_latest = client.get("/api/evaluation/benchmark/latest")
    assert resp_latest.status_code == 200
    latest_data = resp_latest.json()
    assert "strategies_evaluated" in latest_data or "status" in latest_data
