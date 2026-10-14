from fastapi import APIRouter, HTTPException
from app.models.evaluation import EvaluationRunResult, StrategyComparisonResult
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.post("/run", response_model=EvaluationRunResult)
async def run_benchmark():
    """
    Executes live quantitative evaluation against the benchmark dataset:
    - Calculates true precision, recall, and F1 on temporal extraction
    - Verifies contradiction resolution success rate
    - Computes real token count & Dollar cost savings vs Pure LLM baseline
    - Profiles latency breakdown across pipeline stages
    """
    try:
        return await evaluation_service.run_evaluation()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.post("/compare-strategies", response_model=StrategyComparisonResult)
async def compare_extraction_strategies():
    """
    Research Contribution Comparative Evaluation:
    Evaluates Strategy A (LLM on every episode) vs Strategy B (Rules-first with confidence-gated LLM fallback)
    on the exact same benchmark dataset.
    Measures:
    - Precision, recall, and F1 score
    - Actual measured input and output tokens
    - Empirical fallback call rate
    - Wall-clock latency
    - Estimated cost under explicit pricing assumptions
    - Tests the research hypothesis of 40-60% token reduction
    """
    try:
        return await evaluation_service.compare_strategies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparative evaluation failed: {str(e)}")

@router.get("/comparison/latest")
def get_latest_comparison():
    """Returns the most recent Strategy A vs Strategy B comparison run"""
    if not evaluation_service.last_comparison:
        return {"status": "no_comparison_yet", "message": "Trigger POST /api/evaluation/compare-strategies to run research comparison."}
    return evaluation_service.last_comparison

@router.get("/results")
def get_evaluation_results():
    """Returns the most recent evaluation run (alias for /latest)"""
    if not evaluation_service.last_result:
        return {"status": "no_runs_yet", "message": "Trigger /api/evaluation/run to execute benchmark."}
    return evaluation_service.last_result

@router.get("/latest")
def get_latest_results():
    """Returns the most recent evaluation run"""
    if not evaluation_service.last_result:
        return {"status": "no_runs_yet", "message": "Trigger /api/evaluation/run to execute benchmark."}
    return evaluation_service.last_result

@router.post("/benchmark")
async def run_reproducible_benchmark(
    limit: int = 35,
    category: str = None,
    strategies: str = "all"
):
    """
    Executes the reproducible evaluation benchmark across labelled scenarios (software stacks,
    locations, employment, projects, additions, repeated facts, ambiguous inputs, adversarial).
    Compares Chronos Hybrid, Always LLM, Mem0, and Graphiti baselines under identical conditions.
    Exports results to JSON and CSV.
    """
    import os
    import sys
    from benchmarks.dataset_loader import load_benchmark_dataset
    from benchmarks.engine import BenchmarkEngine
    from benchmarks.run_benchmark import build_strategies
    
    try:
        dataset = load_benchmark_dataset()
        strat_objs = build_strategies(strategies)
        engine = BenchmarkEngine(dataset=dataset, strategies=strat_objs)
        return await engine.run(limit=limit, category=category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reproducible benchmark failed: {str(e)}")

@router.get("/benchmark/latest")
def get_latest_benchmark_file():
    """Returns the latest exported canonical benchmark results from disk."""
    import os
    import json
    results_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "benchmarks", "results", "preliminary_results.json")
    if not os.path.exists(results_path):
        return {"status": "no_benchmark_run_yet", "message": "Trigger POST /api/evaluation/benchmark to generate results."}
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/benchmark/scenarios")
def get_benchmark_scenarios():
    """Returns all labelled scenarios in the benchmark dataset."""
    from benchmarks.dataset_loader import load_benchmark_dataset
    dataset = load_benchmark_dataset()
    return {
        "version": dataset.version,
        "description": dataset.description,
        "total_scenarios": len(dataset.scenarios),
        "target_total_capacity": dataset.target_total_capacity,
        "scenarios": dataset.scenarios
    }

