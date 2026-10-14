import os
import sys
import platform
import json
import csv
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from benchmarks.dataset_loader import BenchmarkDataset, Scenario, load_benchmark_dataset
from benchmarks.baselines.base import BaseMemoryStrategy
from benchmarks.baselines.chronos_hybrid import ChronosHybridStrategy
from benchmarks.baselines.always_llm import AlwaysLLMStrategy
from benchmarks.baselines.mem0_adapter import Mem0BaselineStrategy
from benchmarks.baselines.graphiti_adapter import GraphitiBaselineStrategy
from benchmarks.metrics import (
    calculate_set_precision_recall_f1,
    check_stale_fact_errors,
    compute_distribution_metrics
)
from app.core.config import settings

logger = logging.getLogger("chronos.benchmarks.engine")

def get_environment_metadata() -> Dict[str, Any]:
    """Capture runtime environment metadata for scientific reproducibility."""
    import importlib.metadata
    
    packages_to_check = [
        "fastapi", "pydantic", "neo4j", "httpx", "uvicorn", 
        "pytest", "numpy", "mem0ai", "graphiti-core"
    ]
    pkg_versions = {}
    for pkg in packages_to_check:
        try:
            pkg_versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            pkg_versions[pkg] = "not_installed"
            
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "package_versions": pkg_versions,
        "llm_model": settings.OPENAI_MODEL,
        "llm_provider_url": settings.OPENAI_API_BASE,
        "neo4j_uri": settings.NEO4J_URI,
        "confidence_threshold": settings.EXTRACTION_CONFIDENCE_THRESHOLD,
        "pricing_basis": settings.COST_PRICING_BASIS_DESC
    }

class BenchmarkEngine:
    def __init__(
        self,
        dataset: Optional[BenchmarkDataset] = None,
        strategies: Optional[List[BaseMemoryStrategy]] = None,
        output_dir: Optional[str] = None,
        canonical_name: str = "iteration2_results"
    ):
        self.dataset = dataset or load_benchmark_dataset()
        self.strategies = strategies or [
            ChronosHybridStrategy(),
            AlwaysLLMStrategy(),
            Mem0BaselineStrategy(),
            GraphitiBaselineStrategy()
        ]
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "results")
        self.canonical_name = canonical_name
        os.makedirs(self.output_dir, exist_ok=True)

    async def run(
        self,
        limit: Optional[int] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes benchmark across all configured strategies on identical scenarios.
        """
        env_meta = get_environment_metadata()
        scenarios = self.dataset.scenarios
        
        if category:
            scenarios = [s for s in scenarios if s.category == category]
            
        if limit and limit > 0:
            scenarios = scenarios[:limit]
            
        logger.info("Executing benchmark on %d scenarios across %d strategies...", 
                    len(scenarios), len(self.strategies))
        
        results: Dict[str, Any] = {
            "metadata": env_meta,
            "total_scenarios_evaluated": len(scenarios),
            "strategies_evaluated": {}
        }

        for strategy in self.strategies:
            strat_name = strategy.name
            is_avail, avail_reason = strategy.is_available()
            
            if not is_avail:
                logger.warning("Baseline strategy '%s' is unavailable: %s. Reporting as NOT RUN.", strat_name, avail_reason)
                results["strategies_evaluated"][strat_name] = {
                    "status": "not_run",
                    "reason": avail_reason,
                    "is_live_provider": strategy.is_live,
                    "scenario_count": 0,
                    "summary_metrics": {}
                }
                continue

            logger.info("Running strategy '%s' (is_live=%s)...", strat_name, strategy.is_live)
            strat_results = await self._evaluate_strategy(strategy, scenarios)
            results["strategies_evaluated"][strat_name] = strat_results

        # Export raw results
        export_paths = self._export_results(results)
        results["exported_files"] = export_paths
        
        return results

    async def _evaluate_strategy(
        self,
        strategy: BaseMemoryStrategy,
        scenarios: List[Scenario]
    ) -> Dict[str, Any]:
        scenario_records = []
        all_ingest_latencies = []
        all_query_latencies = []
        
        total_in_tokens = 0
        total_out_tokens = 0
        total_tokens = 0
        total_cost_usd = 0.0
        tokens_measured_flag = True
        
        total_active_tp = 0
        total_active_fp = 0
        total_active_fn = 0
        
        total_hist_tp = 0
        total_hist_fp = 0
        total_hist_fn = 0
        
        stale_fact_error_count = 0
        total_queries_evaluated = 0
        passed_queries_count = 0
        
        rule_extractions_count = 0
        llm_fallback_count = 0

        for sc in scenarios:
            await strategy.setup()
            sc_start_time = datetime.now(timezone.utc)
            
            sc_tokens = 0
            sc_cost = 0.0
            
            # 1. Ingest episode turns
            for turn in sc.episode_sequence:
                turn_time = datetime.fromisoformat(turn.timestamp.replace("Z", "+00:00"))
                ingest_res = await strategy.ingest_episode(
                    session_id=turn.session_id,
                    speaker=turn.speaker,
                    text=turn.text,
                    timestamp=turn_time
                )
                all_ingest_latencies.append(ingest_res.get("latency_ms", 0.0))
                
                t_in = ingest_res.get("input_tokens", 0)
                t_out = ingest_res.get("output_tokens", 0)
                t_tot = ingest_res.get("total_tokens", 0)
                c_usd = ingest_res.get("cost_usd", 0.0)
                
                total_in_tokens += t_in
                total_out_tokens += t_out
                total_tokens += t_tot
                sc_tokens += t_tot
                total_cost_usd += c_usd
                sc_cost += c_usd
                
                if not ingest_res.get("tokens_is_measured", True):
                    tokens_measured_flag = False
                    
                if ingest_res.get("fallback_triggered", False):
                    llm_fallback_count += 1
                else:
                    rule_extractions_count += 1

            # 2. Extract final knowledge graph facts
            extracted_active = await strategy.get_active_facts()
            extracted_hist = await strategy.get_historical_facts()
            
            exp_active = [f.model_dump() for f in sc.expected_active_facts]
            exp_hist = [f.model_dump() for f in sc.expected_historical_facts]
            
            active_f1_res = calculate_set_precision_recall_f1(extracted_active, exp_active)
            hist_f1_res = calculate_set_precision_recall_f1(extracted_hist, exp_hist)
            
            total_active_tp += active_f1_res["tp"]
            total_active_fp += active_f1_res["fp"]
            total_active_fn += active_f1_res["fn"]
            
            total_hist_tp += hist_f1_res["tp"]
            total_hist_fp += hist_f1_res["fp"]
            total_hist_fn += hist_f1_res["fn"]

            # 3. Answer test queries
            query_results = []
            for tq in sc.expected_test_queries:
                total_queries_evaluated += 1
                q_ans = await strategy.answer_query(tq.query, session_id=sc.episode_sequence[0].session_id)
                all_query_latencies.append(q_ans.get("latency_ms", 0.0))
                
                eval_res = check_stale_fact_errors(
                    answer=q_ans.get("answer", ""),
                    target_temporal_state=tq.target_temporal_state,
                    expected_keywords=tq.expected_keywords,
                    forbidden_keywords=tq.forbidden_keywords
                )
                
                if eval_res["stale_fact_error"]:
                    stale_fact_error_count += 1
                if eval_res["passed"]:
                    passed_queries_count += 1
                    
                query_results.append({
                    "query": tq.query,
                    "target_temporal_state": tq.target_temporal_state,
                    "model_answer": q_ans.get("answer", ""),
                    "passed": eval_res["passed"],
                    "stale_fact_error": eval_res["stale_fact_error"],
                    "reasons": eval_res["reasons"]
                })

            await strategy.teardown()
            
            scenario_records.append({
                "scenario_id": sc.scenario_id,
                "category": sc.category,
                "title": sc.title,
                "active_f1": active_f1_res["f1"],
                "historical_f1": hist_f1_res["f1"],
                "tokens_used": sc_tokens,
                "cost_usd": round(sc_cost, 6),
                "queries_evaluated": len(query_results),
                "queries_passed": sum(1 for q in query_results if q["passed"]),
                "stale_errors": sum(1 for q in query_results if q["stale_fact_error"]),
                "query_details": query_results
            })

        # Calculate macro and micro F1
        active_prec = total_active_tp / (total_active_tp + total_active_fp) if (total_active_tp + total_active_fp) > 0 else 0.0
        active_rec = total_active_tp / (total_active_tp + total_active_fn) if (total_active_tp + total_active_fn) > 0 else 0.0
        active_f1 = 2 * (active_prec * active_rec) / (active_prec + active_rec) if (active_prec + active_rec) > 0 else 0.0
        
        hist_prec = total_hist_tp / (total_hist_tp + total_hist_fp) if (total_hist_tp + total_hist_fp) > 0 else 0.0
        hist_rec = total_hist_tp / (total_hist_tp + total_hist_fn) if (total_hist_tp + total_hist_fn) > 0 else 0.0
        hist_f1 = 2 * (hist_prec * hist_rec) / (hist_prec + hist_rec) if (hist_prec + hist_rec) > 0 else 0.0
        
        overall_prec = (total_active_tp + total_hist_tp) / max(1, (total_active_tp + total_hist_tp + total_active_fp + total_hist_fp))
        overall_rec = (total_active_tp + total_hist_tp) / max(1, (total_active_tp + total_hist_tp + total_active_fn + total_hist_fn))
        overall_f1 = 2 * (overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0

        query_accuracy = passed_queries_count / max(1, total_queries_evaluated)
        stale_error_rate = stale_fact_error_count / max(1, total_queries_evaluated)

        return {
            "status": "completed",
            "is_live_provider": strategy.is_live,
            "scenario_count": len(scenarios),
            "summary_metrics": {
                "active_facts_precision": round(active_prec, 4),
                "active_facts_recall": round(active_rec, 4),
                "active_facts_f1": round(active_f1, 4),
                "historical_facts_precision": round(hist_prec, 4),
                "historical_facts_recall": round(hist_rec, 4),
                "historical_facts_f1": round(hist_f1, 4),
                "overall_f1": round(overall_f1, 4),
                "total_queries": total_queries_evaluated,
                "passed_queries": passed_queries_count,
                "query_accuracy": round(query_accuracy, 4),
                "stale_fact_error_count": stale_fact_error_count,
                "stale_fact_error_rate": round(stale_error_rate, 4),
                "rule_extractions_count": rule_extractions_count,
                "llm_fallback_count": llm_fallback_count,
                "rule_bypass_rate": round(rule_extractions_count / max(1, rule_extractions_count + llm_fallback_count), 4),
                "tokens": {
                    "input_tokens": total_in_tokens,
                    "output_tokens": total_out_tokens,
                    "total_tokens": total_tokens,
                    "tokens_is_measured": tokens_measured_flag
                },
                "total_cost_usd": round(total_cost_usd, 6),
                "ingest_latency": compute_distribution_metrics(all_ingest_latencies),
                "query_latency": compute_distribution_metrics(all_query_latencies)
            },
            "scenarios": scenario_records
        }

    def _export_results(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Exports raw benchmark results to JSON and CSV formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"benchmark_run_{timestamp}.json"
        csv_filename = f"benchmark_run_{timestamp}.csv"
        
        json_path = os.path.join(self.output_dir, json_filename)
        csv_path = os.path.join(self.output_dir, csv_filename)
        
        # 1. Export JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        # 2. Export CSV summary table
        fieldnames = [
            "strategy", "status", "is_live_provider", "scenarios_count",
            "active_f1", "historical_f1", "overall_f1", "query_accuracy",
            "stale_fact_errors", "total_tokens", "tokens_is_measured",
            "cost_usd", "mean_ingest_ms", "p95_ingest_ms", "rule_bypass_rate"
        ]
        
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for strat_name, strat_data in results["strategies_evaluated"].items():
                if strat_data.get("status") != "completed":
                    writer.writerow({
                        "strategy": strat_name,
                        "status": strat_data.get("status", "not_run"),
                        "is_live_provider": strat_data.get("is_live_provider", False),
                        "scenarios_count": 0,
                        "active_f1": 0.0,
                        "historical_f1": 0.0,
                        "overall_f1": 0.0,
                        "query_accuracy": 0.0,
                        "stale_fact_errors": 0,
                        "total_tokens": 0,
                        "tokens_is_measured": False,
                        "cost_usd": 0.0,
                        "mean_ingest_ms": 0.0,
                        "p95_ingest_ms": 0.0,
                        "rule_bypass_rate": 0.0
                    })
                else:
                    m = strat_data["summary_metrics"]
                    writer.writerow({
                        "strategy": strat_name,
                        "status": "completed",
                        "is_live_provider": strat_data.get("is_live_provider", False),
                        "scenarios_count": strat_data.get("scenario_count", 0),
                        "active_f1": m.get("active_facts_f1", 0.0),
                        "historical_f1": m.get("historical_facts_f1", 0.0),
                        "overall_f1": m.get("overall_f1", 0.0),
                        "query_accuracy": m.get("query_accuracy", 0.0),
                        "stale_fact_errors": m.get("stale_fact_error_count", 0),
                        "total_tokens": m.get("tokens", {}).get("total_tokens", 0),
                        "tokens_is_measured": m.get("tokens", {}).get("tokens_is_measured", True),
                        "cost_usd": m.get("total_cost_usd", 0.0),
                        "mean_ingest_ms": m.get("ingest_latency", {}).get("mean_ms", 0.0),
                        "p95_ingest_ms": m.get("ingest_latency", {}).get("p95_ms", 0.0),
                        "rule_bypass_rate": m.get("rule_bypass_rate", 0.0)
                    })

        # Also write canonical iteration files so results are directly accessible
        canonical_json = os.path.join(self.output_dir, f"{self.canonical_name}.json")
        canonical_csv = os.path.join(self.output_dir, f"{self.canonical_name}.csv")
        with open(canonical_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        with open(canonical_csv, "w", newline="", encoding="utf-8") as f:
            with open(csv_path, "r", encoding="utf-8") as src:
                f.write(src.read())

        return {
            "json": json_path,
            "csv": csv_path,
            "canonical_json": canonical_json,
            "canonical_csv": canonical_csv
        }
