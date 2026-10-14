#!/usr/bin/env python3
"""
Chronos Memory: Reproducible Benchmark Runner
Command-line interface to execute empirical evaluations on labelled scenarios.

Usage:
    python -m benchmarks.run_benchmark [OPTIONS]
    python run_benchmark.py [OPTIONS]

Options:
    --dataset PATH        Path to scenarios JSON file (default: benchmarks/dataset/scenarios.json)
    --output-dir PATH     Directory to store results (default: benchmarks/results)
    --limit INT           Evaluate only the first N scenarios (default: all)
    --category STR        Filter scenarios by category (e.g., software_stacks, location_changes)
    --strategies LIST     Comma-separated list of strategies (chronos_hybrid,always_llm,mem0,graphiti)
    --verbose             Print detailed per-query evaluations
"""

import sys
import os
import asyncio
import argparse
import logging
from typing import List

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from benchmarks.dataset_loader import load_benchmark_dataset
from benchmarks.engine import BenchmarkEngine
from benchmarks.baselines.base import BaseMemoryStrategy
from benchmarks.baselines.chronos_hybrid import ChronosHybridStrategy
from benchmarks.baselines.always_llm import AlwaysLLMStrategy
from benchmarks.baselines.mem0_adapter import Mem0BaselineStrategy
from benchmarks.baselines.graphiti_adapter import GraphitiBaselineStrategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chronos.benchmark")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Chronos Memory Reproducible Research Benchmark Runner"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to scenarios JSON file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save JSON and CSV results"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of scenarios to evaluate"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter scenarios by category (e.g. software_stacks, adversarial)"
    )
    parser.add_argument(
        "--strategies",
        type=str,
        default="all",
        help="Comma-separated strategy names: chronos_hybrid,always_llm,mem0,graphiti or 'all'"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed scenario query outcomes"
    )
    return parser.parse_args()

def build_strategies(strategy_names_str: str) -> List[BaseMemoryStrategy]:
    all_map = {
        "chronos_hybrid": ChronosHybridStrategy,
        "always_llm": AlwaysLLMStrategy,
        "mem0": Mem0BaselineStrategy,
        "graphiti": GraphitiBaselineStrategy
    }
    
    if strategy_names_str.strip().lower() == "all":
        return [cls() for cls in all_map.values()]
        
    requested = [s.strip().lower() for s in strategy_names_str.split(",") if s.strip()]
    strategies = []
    for r in requested:
        if r in all_map:
            strategies.append(all_map[r]())
        else:
            logger.warning("Unknown strategy requested: '%s'. Available: %s", r, list(all_map.keys()))
            
    if not strategies:
        strategies = [ChronosHybridStrategy(), AlwaysLLMStrategy()]
    return strategies

def print_summary_table(results: dict):
    print("\n" + "="*86)
    print("       CHRONOS MEMORY: REPRODUCIBLE RESEARCH BENCHMARK RESULTS")
    print("="*86)
    
    meta = results.get("metadata", {})
    print(f" Timestamp (UTC): {meta.get('timestamp_utc')}")
    print(f" Python Version:  {meta.get('python_version').split()[0]}")
    print(f" Platform:        {meta.get('platform')}")
    print(f" LLM Model:       {meta.get('llm_model')}")
    print(f" Pricing Basis:   {meta.get('pricing_basis')}")
    print(f" Scenarios Eval:  {results.get('total_scenarios_evaluated')}")
    print("-" * 86)
    
    header = f"{'Strategy':<18} | {'Status':<10} | {'F1':<6} | {'Accuracy':<8} | {'Stale':<5} | {'Tokens':<8} | {'Cost ($)':<9} | {'Mean Lat':<9}"
    print(header)
    print("-" * 86)
    
    strat_evals = results.get("strategies_evaluated", {})
    chronos_tok = 0
    llm_tok = 0
    chronos_lat = 0.0
    llm_lat = 0.0

    for name, data in strat_evals.items():
        status = data.get("status", "not_run")
        if status != "completed":
            print(f"{name:<18} | {status:<10} | {'N/A':<6} | {'N/A':<8} | {'N/A':<5} | {'N/A':<8} | {'N/A':<9} | {'N/A':<9}")
            print(f"   -> Reason: {data.get('reason')}")
            continue
            
        m = data.get("summary_metrics", {})
        f1 = f"{m.get('overall_f1', 0.0)*100:.1f}%"
        acc = f"{m.get('query_accuracy', 0.0)*100:.1f}%"
        stale = str(m.get("stale_fact_error_count", 0))
        toks = f"{m.get('tokens', {}).get('total_tokens', 0):,}"
        cost = f"${m.get('total_cost_usd', 0.0):.5f}"
        lat = f"{m.get('ingest_latency', {}).get('mean_ms', 0.0):.1f} ms"
        
        if name == "chronos_hybrid":
            chronos_tok = m.get('tokens', {}).get('total_tokens', 0)
            chronos_lat = m.get('ingest_latency', {}).get('mean_ms', 0.0)
        elif name == "always_llm":
            llm_tok = m.get('tokens', {}).get('total_tokens', 0)
            llm_lat = m.get('ingest_latency', {}).get('mean_ms', 0.0)
            
        print(f"{name:<18} | {status:<10} | {f1:<6} | {acc:<8} | {stale:<5} | {toks:<8} | {cost:<9} | {lat:<9}")

    print("-" * 86)
    
    # Hypothesis verification
    if chronos_tok > 0 and llm_tok > 0:
        reduction = (1.0 - (chronos_tok / llm_tok)) * 100
        speedup = (llm_lat / chronos_lat) if chronos_lat > 0 else 1.0
        print(f" Empirical Token Reduction (Chronos vs Pure LLM): {reduction:.1f}% (Hypothesis: 40-60%)")
        print(f" Ingestion Latency Speedup Factor:                {speedup:.1f}x")
        print("-" * 86)

    files = results.get("exported_files", {})
    print(f" JSON Raw Results:  {files.get('canonical_json')}")
    print(f" CSV Summary Table: {files.get('canonical_csv')}")
    print("="*86 + "\n")

async def main():
    args = parse_args()
    dataset = load_benchmark_dataset(args.dataset)
    strategies = build_strategies(args.strategies)
    
    engine = BenchmarkEngine(
        dataset=dataset,
        strategies=strategies,
        output_dir=args.output_dir
    )
    
    results = await engine.run(limit=args.limit, category=args.category)
    print_summary_table(results)

if __name__ == "__main__":
    asyncio.run(main())
