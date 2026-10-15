import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("chronos.benchmarks.dataset")

DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "dataset", "scenarios.json"
)

class FactExpectation(BaseModel):
    subject: str
    predicate: str
    object: str

class TestQuery(BaseModel):
    query: str
    target_temporal_state: str  # 'current' | 'historical' | 'point_in_time' | 'evolution'
    expected_keywords: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)

class EpisodeTurn(BaseModel):
    session_id: str
    speaker: str
    text: str
    timestamp: str

class Scenario(BaseModel):
    scenario_id: str
    category: str
    title: str
    description: str
    difficulty: str = "standard"
    episode_sequence: List[EpisodeTurn]
    expected_active_facts: List[FactExpectation]
    expected_historical_facts: List[FactExpectation]
    expected_contradictions: int = 0
    expected_test_queries: List[TestQuery]

class BenchmarkDataset(BaseModel):
    version: str
    description: str
    target_total_capacity: int = 150
    scenarios: List[Scenario]

def load_benchmark_dataset(path: Optional[str] = None) -> BenchmarkDataset:
    target_path = path or DEFAULT_DATASET_PATH
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Benchmark dataset not found at: {target_path}")
    
    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    dataset = BenchmarkDataset.model_validate(raw_data)
    logger.info("Loaded benchmark dataset v%s with %d scenarios from %s", 
                dataset.version, len(dataset.scenarios), target_path)
    return dataset
