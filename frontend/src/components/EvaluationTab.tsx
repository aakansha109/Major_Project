"use client";

import React, { useState, useEffect } from "react";
import { EvaluationResult, StrategyComparisonResult } from "@/types";
import { api } from "@/lib/api";
import { 
  BarChart3, 
  Play, 
  CheckCircle2, 
  Coins, 
  TrendingDown, 
  Zap, 
  Clock, 
  Percent, 
  ShieldCheck, 
  Cpu, 
  FileText,
  Layers,
  ArrowRight,
  AlertTriangle,
  Scale,
  Sparkles,
  Info
} from "lucide-react";

interface EvaluationTabProps {
  onRunEvaluation: () => Promise<EvaluationResult>;
  latestResult: EvaluationResult | null;
}

export const EvaluationTab: React.FC<EvaluationTabProps> = ({
  onRunEvaluation,
  latestResult
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"comparison" | "e2e">("comparison");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(latestResult);
  const [comparison, setComparison] = useState<StrategyComparisonResult | null>(null);

  useEffect(() => {
    api.getLatestComparison().then((res: any) => {
      if (res && res.strategy_a) {
        setComparison(res);
      }
    }).catch(() => {});
  }, []);

  const handleRunComparison = async () => {
    setRunning(true);
    try {
      const res = await api.compareStrategies();
      setComparison(res);
    } catch (err: any) {
      alert(`Strategy comparison failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await onRunEvaluation();
      setResult(res);
    } catch (err: any) {
      alert(`Benchmark execution failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  const cost = result?.cost_comparison;
  const ext = result?.extraction_metrics;
  const contra = result?.contradiction_metrics;
  const ret = result?.retrieval_metrics;
  const lat = result?.latency_breakdown;

  return (
    <div className="space-y-6">
      {/* Sub-navigation Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab("comparison")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeSubTab === "comparison"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Scale className="w-4 h-4 text-cyan-400" />
            <span>Research Contribution: Strategy Comparison</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 font-mono">Core</span>
          </button>

          <button
            onClick={() => setActiveSubTab("e2e")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeSubTab === "e2e"
                ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <span>Full System Benchmark</span>
          </button>
        </div>

        {activeSubTab === "comparison" ? (
          <button
            onClick={handleRunComparison}
            disabled={running}
            className="flex items-center justify-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 via-emerald-400 to-indigo-400 hover:from-cyan-300 hover:to-indigo-300 transition shadow-lg shadow-cyan-500/10 disabled:opacity-50"
          >
            {running ? (
              <>
                <Zap className="w-4 h-4 animate-spin text-slate-950" />
                <span>Comparing Strategies...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-slate-950" />
                <span>Execute Strategy Comparison (A vs B)</span>
              </>
            )}
          </button>
        ) : (
          <button
            onClick={handleRun}
            disabled={running}
            className="flex items-center justify-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 via-emerald-400 to-indigo-400 hover:from-cyan-300 hover:to-indigo-300 transition shadow-lg shadow-cyan-500/10 disabled:opacity-50"
          >
            {running ? (
              <>
                <Zap className="w-4 h-4 animate-spin text-slate-950" />
                <span>Running Test Suite...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-slate-950" />
                <span>Execute Live Benchmark</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* VIEW 1: STRATEGY COMPARISON (RESEARCH CONTRIBUTION) */}
      {activeSubTab === "comparison" && (
        <div className="space-y-6">
          {comparison ? (
            <>
              {/* Hypothesis Evaluation Card */}
              <div className={`glass-panel rounded-2xl p-6 border ${comparison.hypothesis_supported ? "border-emerald-500/40 bg-emerald-950/10" : "border-amber-500/40 bg-amber-950/10"}`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${comparison.hypothesis_supported ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"}`}>
                        {comparison.hypothesis_supported ? "Hypothesis Supported (40–60% Range)" : "Hypothesis Result"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">Dataset N={comparison.dataset_size}</span>
                    </div>
                    <p className="text-sm font-medium text-white">{comparison.hypothesis_summary}</p>
                    <p className="text-xs text-slate-400 italic">Target: "{comparison.hypothesis_tested}"</p>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-xs text-slate-400 uppercase font-mono">Token Reduction</div>
                      <div className="text-3xl font-extrabold text-cyan-400">{comparison.token_reduction_percent.toFixed(1)}%</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-slate-400 uppercase font-mono">Wall Latency Speedup</div>
                      <div className="text-3xl font-extrabold text-emerald-400">{comparison.latency_speedup_factor.toFixed(1)}x</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Side-by-Side Comparison Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Strategy A Card */}
                <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-rose-400" />
                        <span>Strategy A: 100% LLM on Every Episode</span>
                      </h3>
                      <p className="text-xs text-slate-400">Industry standard baseline (prompting LLM for every message turn)</p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300">Baseline</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Total Tokens</span>
                      <div className="text-xl font-bold text-white font-mono">{comparison.strategy_a.total_tokens.toLocaleString()}</div>
                      <div className="text-[10px] text-slate-500">In: {comparison.strategy_a.total_input_tokens} | Out: {comparison.strategy_a.total_output_tokens}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Estimated Cost</span>
                      <div className="text-xl font-bold text-rose-400 font-mono">${comparison.strategy_a.total_cost_usd.toFixed(5)}</div>
                      <div className="text-[10px] text-slate-500">{comparison.strategy_a.cost_pricing_basis.split(":")[0]}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Mean Wall Latency</span>
                      <div className="text-xl font-bold text-white font-mono">{comparison.strategy_a.mean_latency_ms.toFixed(1)} ms</div>
                      <div className="text-[10px] text-slate-500">Total: {comparison.strategy_a.total_latency_ms.toFixed(0)} ms</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Extraction F1 Score</span>
                      <div className="text-xl font-bold text-emerald-400 font-mono">{(comparison.strategy_a.f1_score * 100).toFixed(1)}%</div>
                      <div className="text-[10px] text-slate-500">Prec: {(comparison.strategy_a.precision * 100).toFixed(0)}% | Rec: {(comparison.strategy_a.recall * 100).toFixed(0)}%</div>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between py-1 border-t border-slate-800">
                      <span>LLM Call Rate:</span>
                      <strong className="text-white font-mono">100.0%</strong>
                    </div>
                    <div className="flex justify-between py-1 border-t border-slate-800">
                      <span>Token Usage Measurement:</span>
                      <span className="text-slate-300 font-mono">{comparison.strategy_a.tokens_are_measured ? "Direct API Measured" : "Simulated Payload"}</span>
                    </div>
                  </div>
                </div>

                {/* Strategy B Card */}
                <div className="glass-panel rounded-2xl p-6 border border-cyan-500/40 bg-gradient-to-b from-cyan-950/10 to-transparent space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-cyan-400" />
                        <span>Strategy B: Confidence-Gated Hybrid (Chronos)</span>
                      </h3>
                      <p className="text-xs text-slate-400">Rules first; routes to LLM only when confidence &lt; &tau; (0.80)</p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300">Chronos Core</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-slate-900 border border-cyan-500/20">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Total Tokens</span>
                      <div className="text-xl font-bold text-cyan-400 font-mono">{comparison.strategy_b.total_tokens.toLocaleString()}</div>
                      <div className="text-[10px] text-cyan-300 font-semibold font-mono">-{comparison.token_reduction_percent.toFixed(1)}% vs Strategy A</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-emerald-500/20">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Estimated Cost</span>
                      <div className="text-xl font-bold text-emerald-400 font-mono">${comparison.strategy_b.total_cost_usd.toFixed(5)}</div>
                      <div className="text-[10px] text-emerald-300 font-semibold font-mono">-{comparison.cost_reduction_percent.toFixed(1)}% savings</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Mean Wall Latency</span>
                      <div className="text-xl font-bold text-white font-mono">{comparison.strategy_b.mean_latency_ms.toFixed(1)} ms</div>
                      <div className="text-[10px] text-emerald-400 font-mono">{comparison.latency_speedup_factor.toFixed(1)}x faster</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Extraction F1 Score</span>
                      <div className="text-xl font-bold text-emerald-400 font-mono">{(comparison.strategy_b.f1_score * 100).toFixed(1)}%</div>
                      <div className="text-[10px] text-slate-500">Prec: {(comparison.strategy_b.precision * 100).toFixed(0)}% | Rec: {(comparison.strategy_b.recall * 100).toFixed(0)}%</div>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between py-1 border-t border-slate-800">
                      <span>Deterministic Rule Match Rate (0 tokens):</span>
                      <strong className="text-emerald-400 font-mono">{(comparison.strategy_b.rule_extraction_rate * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="flex justify-between py-1 border-t border-slate-800">
                      <span>Empirical LLM Fallback Rate:</span>
                      <strong className="text-cyan-400 font-mono">{(comparison.strategy_b.fallback_call_rate * 100).toFixed(1)}%</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Research Limitations & Threats to Validity */}
              <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Info className="w-4 h-4 text-cyan-400" />
                  <span>Research Limitations & Threats to Validity</span>
                </h4>
                <ul className="space-y-2 text-xs text-slate-400 list-disc list-inside">
                  {comparison.limitations.map((lim, idx) => (
                    <li key={idx} className="leading-relaxed">{lim}</li>
                  ))}
                </ul>
              </div>

              {/* Detailed Per-Episode Comparison Ledger */}
              <div className="glass-panel rounded-2xl p-5 border border-slate-800">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span>Comparative Extraction Ledger ({comparison.detailed_episodes.length} Episodes)</span>
                </h3>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-mono">
                        <th className="pb-2.5">ID</th>
                        <th className="pb-2.5">Input Utterance</th>
                        <th className="pb-2.5">Strategy A (100% LLM)</th>
                        <th className="pb-2.5">Strategy B (Hybrid)</th>
                        <th className="pb-2.5">Tokens (A / B)</th>
                        <th className="pb-2.5">Decision Reason (Strategy B)</th>
                        <th className="pb-2.5 text-right">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-850">
                      {comparison.detailed_episodes.map((ep) => (
                        <tr key={ep.case_id} className="text-slate-300 hover:bg-slate-900/50">
                          <td className="py-2.5 font-mono text-cyan-400">{ep.case_id}</td>
                          <td className="py-2.5 max-w-xs truncate" title={ep.input_text}>{ep.input_text}</td>
                          <td className="py-2.5 font-mono text-slate-400">{ep.strategy_a.tokens} tok ({ep.strategy_a.latency_ms}ms)</td>
                          <td className="py-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${ep.strategy_b.fallback_triggered ? "bg-indigo-500/20 text-indigo-300" : "bg-emerald-500/20 text-emerald-300"}`}>
                              {ep.strategy_b.method}
                            </span>
                          </td>
                          <td className="py-2.5 font-mono text-cyan-300">{ep.strategy_a.tokens} &rarr; <span className="font-bold text-emerald-400">{ep.strategy_b.tokens}</span></td>
                          <td className="py-2.5 max-w-sm truncate text-[11px] text-slate-400" title={ep.strategy_b.decision_reason}>
                            {ep.strategy_b.decision_reason}
                          </td>
                          <td className="py-2.5 text-right font-mono">
                            {ep.strategy_b.matched ? (
                              <span className="text-emerald-400 font-bold">MATCH</span>
                            ) : (
                              <span className="text-slate-500">N/A / MISS</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-panel rounded-2xl p-12 border border-slate-800 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 mx-auto flex items-center justify-center">
                <Scale className="w-7 h-7 text-cyan-400" />
              </div>
              <h3 className="text-base font-semibold text-white">No Strategy Comparison Run Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Click "Execute Strategy Comparison (A vs B)" above to run both Strategy A (100% LLM extraction) and Strategy B (Chronos confidence-gated hybrid extraction) on the same dataset, verifying token savings and empirical performance.
              </p>
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: FULL SYSTEM END-TO-END BENCHMARK */}
      {activeSubTab === "e2e" && (
        <div className="space-y-6">
          {result ? (
            <div className="space-y-6">
              {/* Key Evaluation Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Extraction F1 Score */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span className="font-semibold uppercase tracking-wider">Extraction F1</span>
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {(ext!.f1_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400 flex items-center justify-between">
                    <span>Precision: {(ext!.precision * 100).toFixed(0)}%</span>
                    <span>Recall: {(ext!.recall * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Token Savings vs Pure LLM */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span className="font-semibold uppercase tracking-wider">Token Savings</span>
                    <TrendingDown className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-cyan-400">
                    {cost!.token_savings_percent.toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">
                    Chronos: <strong className="text-slate-200">{cost!.chronos_tokens_total}</strong> vs Pure LLM: <strong className="text-slate-200">{cost!.pure_llm_tokens_total}</strong>
                  </div>
                </div>

                {/* Cost Reduction */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span className="font-semibold uppercase tracking-wider">Dollar Cost Saved</span>
                    <Coins className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-emerald-400">
                    {cost!.cost_reduction_percent.toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">
                    ${cost!.chronos_cost_usd.toFixed(5)} vs ${cost!.pure_llm_cost_usd.toFixed(5)}
                  </div>
                </div>

                {/* Contradiction Resolution Accuracy */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span className="font-semibold uppercase tracking-wider">Contradiction Acc.</span>
                    <CheckCircle2 className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-indigo-400">
                    {(contra!.accuracy_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">
                    {contra!.passed_cases} of {contra!.total_test_cases} supersessions verified
                  </div>
                </div>
              </div>

              {/* Latency & Architectural Efficiency Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-cyan-400" />
                    <span>Latency Breakdown by Stage (Milliseconds)</span>
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Tier 1 Rule Extraction</span>
                        <strong className="text-emerald-400 font-mono">{lat!.mean_rule_extraction_ms} ms</strong>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full bg-emerald-400 rounded-full" style={{ width: "15%" }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Graph Neighborhood Write & Contradiction Resolution</span>
                        <strong className="text-cyan-400 font-mono">{lat!.mean_graph_write_ms} ms</strong>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full bg-cyan-400 rounded-full" style={{ width: "25%" }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Point-in-Time Vector & Graph Retrieval</span>
                        <strong className="text-indigo-400 font-mono">{lat!.mean_retrieval_ms} ms</strong>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full bg-indigo-400 rounded-full" style={{ width: "35%" }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Task Inference Synthesis</span>
                        <strong className="text-amber-400 font-mono">{lat!.mean_inference_ms} ms</strong>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full bg-amber-400 rounded-full" style={{ width: "45%" }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Cost Efficiency Comparison Box */}
                <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <Coins className="w-4 h-4 text-emerald-400" />
                    <span>Cost & Extraction Efficiency Analysis</span>
                  </h3>

                  <div className="space-y-3 text-xs text-slate-300">
                    <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                      <span>Deterministic Rule Hit Rate (Zero LLM Tokens):</span>
                      <strong className="text-emerald-400 text-sm font-mono">
                        {(cost!.rule_extraction_ratio * 100).toFixed(0)}%
                      </strong>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                      <span>LLM Fallback Invocation Rate:</span>
                      <strong className="text-indigo-400 text-sm font-mono">
                        {(cost!.llm_fallback_ratio * 100).toFixed(0)}%
                      </strong>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                      <span>Historical Point-in-Time QA Accuracy:</span>
                      <strong className="text-cyan-400 text-sm font-mono">
                        {(ret!.accuracy_score * 100).toFixed(0)}%
                      </strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Detailed Test Case Audit Ledger */}
              <div className="glass-panel rounded-2xl p-5 border border-slate-800">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span>Benchmark Case Execution Log ({result.detailed_results.length} cases)</span>
                </h3>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-mono">
                        <th className="pb-2.5">Case ID</th>
                        <th className="pb-2.5">Input Utterance</th>
                        <th className="pb-2.5">Strategy</th>
                        <th className="pb-2.5">Tokens</th>
                        <th className="pb-2.5">Cost</th>
                        <th className="pb-2.5">Latency</th>
                        <th className="pb-2.5 text-right">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-850">
                      {result.detailed_results.map((item) => (
                        <tr key={item.case_id} className="text-slate-300 hover:bg-slate-900/50">
                          <td className="py-2.5 font-mono text-cyan-400">{item.case_id}</td>
                          <td className="py-2.5 max-w-xs truncate">{item.input}</td>
                          <td className="py-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${item.strategy === "rule_only" ? "bg-emerald-500/20 text-emerald-300" : "bg-indigo-500/20 text-indigo-300"}`}>
                              {item.strategy}
                            </span>
                          </td>
                          <td className="py-2.5 font-mono">{item.tokens}</td>
                          <td className="py-2.5 font-mono text-emerald-400">${item.cost_usd.toFixed(4)}</td>
                          <td className="py-2.5 font-mono text-cyan-300">{item.latency_ms} ms</td>
                          <td className="py-2.5 text-right font-mono">
                            {item.matched ? (
                              <span className="text-emerald-400 font-bold">MATCH</span>
                            ) : (
                              <span className="text-rose-400 font-bold">MISS</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl p-12 border border-slate-800 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 mx-auto flex items-center justify-center">
                <BarChart3 className="w-7 h-7 text-cyan-400" />
              </div>
              <h3 className="text-base font-semibold text-white">No Evaluation Run Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Click "Execute Live Benchmark" above to test the temporal knowledge graph engine against the empirical dataset, measuring precision, recall, contradiction resolution, and token cost savings.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
