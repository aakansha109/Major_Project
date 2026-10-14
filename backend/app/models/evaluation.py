from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BenchmarkTestCase(BaseModel):
    id: str
    category: str # "temporal_extraction", "contradiction_resolution", "historical_qa", "cost_efficiency"
    input_text: str
    event_timestamp: str # ISO format
    expected_triplets: List[Dict[str, Any]]
    expected_contradiction: bool = False
    expected_answer: Optional[str] = None
    query: Optional[str] = None
    as_of: Optional[str] = None

class MetricSummary(BaseModel):
    total_test_cases: int
    passed_cases: int
    accuracy_score: float
    precision: float
    recall: float
    f1_score: float

class CostComparison(BaseModel):
    chronos_tokens_total: int
    chronos_cost_usd: float
    pure_llm_tokens_total: int
    pure_llm_cost_usd: float
    token_savings_percent: float
    cost_reduction_percent: float
    rule_extraction_ratio: float
    llm_fallback_ratio: float

class LatencyBreakdown(BaseModel):
    mean_rule_extraction_ms: float
    mean_llm_extraction_ms: float
    mean_graph_write_ms: float
    mean_retrieval_ms: float
    mean_inference_ms: float

class EvaluationRunResult(BaseModel):
    run_id: str
    timestamp: datetime
    sample_size: int
    extraction_metrics: MetricSummary
    contradiction_metrics: MetricSummary
    retrieval_metrics: MetricSummary
    cost_comparison: CostComparison
    latency_breakdown: LatencyBreakdown
    detailed_results: List[Dict[str, Any]]

class StrategyMetrics(BaseModel):
    strategy_name: str
    sample_size: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    tokens_are_measured: bool
    mean_latency_ms: float
    total_latency_ms: float
    total_cost_usd: float
    cost_pricing_basis: str
    fallback_call_rate: float
    rule_extraction_rate: float
    decision_counts: Dict[str, int]

class StrategyComparisonResult(BaseModel):
    dataset_size: int
    strategy_a: StrategyMetrics
    strategy_b: StrategyMetrics
    token_reduction_percent: float
    cost_reduction_percent: float
    latency_speedup_factor: float
    hypothesis_tested: str = "Rules-first confidence-gated extraction achieves 40–60% lower extraction token usage than LLM-on-every-episode."
    hypothesis_supported: bool
    hypothesis_summary: str
    limitations: List[str]
    detailed_episodes: List[Dict[str, Any]]
