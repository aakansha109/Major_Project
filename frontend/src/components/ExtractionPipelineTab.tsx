"use client";

import React, { useState } from "react";
import { IngestResponse, Episode, Fact } from "@/types";
import { 
  Zap, 
  Cpu, 
  Coins, 
  Timer, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  ShieldAlert, 
  ArrowRight, 
  Play, 
  RefreshCw,
  Terminal,
  Layers,
  Sparkles,
  Info
} from "lucide-react";

interface ExtractionPipelineTabProps {
  onIngest: (payload: { session_id?: string; speaker?: string; text: string; timestamp?: string }) => Promise<IngestResponse>;
  recentEpisodes: Episode[];
  facts: Fact[];
  onRefresh: () => void;
}

const TEST_SCENARIOS = [
  {
    label: "Rule Match: Framework Update",
    text: "I switched my backend framework to FastAPI.",
    category: "Deterministic Rule",
    expected: "Rule: framework_update"
  },
  {
    label: "Rule Match: Relocation",
    text: "Alice moved from Seattle to San Francisco in 2023.",
    category: "Deterministic Rule",
    expected: "Rule: relocation"
  },
  {
    label: "Rule Match: Employment",
    text: "Bob joined OpenAI in 2024 as a Research Scientist.",
    category: "Deterministic Rule",
    expected: "Rule: employment"
  },
  {
    label: "Complex Utterance: Temporal Change",
    text: "Previously I resided in Austin, but since last month I reside in Boston.",
    category: "Confidence-Gated Fallback",
    expected: "Rule or LLM Fallback"
  },
  {
    label: "Multi-Fact Statement",
    text: "Charlie works at Google and uses Kubernetes for orchestration.",
    category: "Multi-Fact",
    expected: "Hybrid Extraction"
  }
];

export const ExtractionPipelineTab: React.FC<ExtractionPipelineTabProps> = ({
  onIngest,
  recentEpisodes,
  facts,
  onRefresh
}) => {
  const [inputText, setInputText] = useState("");
  const [sessionId, setSessionId] = useState("session-pipeline-1");
  const [speaker, setSpeaker] = useState("User");
  const [loading, setLoading] = useState(false);
  const [lastTrace, setLastTrace] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunPipeline = async (textToUse?: string) => {
    const text = textToUse || inputText;
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      const resp = await onIngest({
        session_id: sessionId,
        speaker,
        text: text.trim(),
        timestamp: new Date().toISOString()
      });
      setLastTrace(resp);
      setInputText("");
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Pipeline execution failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
              Confidence-Gated Hybrid Extraction
            </span>
            <span className="text-xs text-slate-400 font-mono hidden sm:inline">
              Tier 1 Rules &rarr; Gate Threshold &rarr; Tier 2 Real LLM Fallback
            </span>
          </div>
          <span className="text-xs text-emerald-400 font-mono font-semibold">
            Zero-Token Rule Tier First
          </span>
        </div>
        <h2 className="text-xl font-bold tracking-tight text-white">
          Hybrid Fact Extraction & Contradiction Pipeline
        </h2>
        <p className="text-xs text-slate-400 max-w-3xl">
          Deterministic Python regex and pattern extraction rules execute first in under 2ms at zero token cost.
          Only unconfident or complex statements trigger the OpenAI-compatible LLM fallback with strict Pydantic validation.
        </p>
      </div>

      {/* Main Grid: Input & Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Sandbox & Test Scenarios (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>Extraction Test Sandbox</span>
            </h3>

            {/* Test Scenarios */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                Load Test Utterances:
              </span>
              <div className="space-y-1.5">
                {TEST_SCENARIOS.map((scenario, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputText(scenario.text);
                    }}
                    className="w-full text-left p-2 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/80 transition text-xs flex items-center justify-between group"
                  >
                    <div>
                      <span className="font-semibold text-slate-200 block">{scenario.label}</span>
                      <span className="text-[11px] text-slate-400 line-clamp-1">"{scenario.text}"</span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400 opacity-80 group-hover:opacity-100 flex-shrink-0 ml-2">
                      Load
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Textarea */}
            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              <label className="text-[11px] font-mono text-slate-400 block">
                Utterance Text to Extract:
              </label>
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Type or paste any conversation turn..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-cyan-500/60 focus:outline-none resize-none font-sans"
              />
            </div>

            {/* Run Button */}
            <button
              onClick={() => handleRunPipeline()}
              disabled={loading || !inputText.trim()}
              className="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition flex items-center justify-center gap-2 shadow-md shadow-cyan-600/20 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing Extraction Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Execute Extraction Pipeline</span>
                </>
              )}
            </button>

            {error && (
              <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-xs text-rose-300">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Right: Real Telemetry & Fact Results (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {lastTrace ? (
            <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white">Pipeline Execution Result</h3>
                </div>
                <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Strategy: {lastTrace.telemetry.strategy}
                </span>
              </div>

              {/* 4 Pipeline Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Total Latency</span>
                  <div className="text-lg font-bold font-mono text-cyan-400 mt-1">
                    {lastTrace.telemetry.total_latency_ms.toFixed(1)}ms
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Tokens Used</span>
                  <div className="text-lg font-bold font-mono text-indigo-300 mt-1">
                    {lastTrace.telemetry.tokens_consumed}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Estimated Cost</span>
                  <div className="text-lg font-bold font-mono text-amber-400 mt-1">
                    ${lastTrace.telemetry.cost_usd.toFixed(5)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Contradictions</span>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-1">
                    {lastTrace.telemetry.contradictions_resolved}
                  </div>
                </div>
              </div>

              {/* Tier Latencies Breakdown */}
              <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1.5 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Tier 1 Rule Latency:</span>
                  <span className="text-emerald-400 font-bold">{lastTrace.telemetry.tier1_latency_ms.toFixed(2)}ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Tier 2 LLM Latency:</span>
                  <span className={lastTrace.telemetry.tier2_latency_ms > 0 ? "text-indigo-400 font-bold" : "text-slate-500"}>
                    {lastTrace.telemetry.tier2_latency_ms > 0 ? `${lastTrace.telemetry.tier2_latency_ms.toFixed(2)}ms` : "0.00ms (Bypassed)"}
                  </span>
                </div>
              </div>

              {/* Extracted Facts */}
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block">
                  New Facts Stored ({lastTrace.extracted_facts.length}):
                </span>
                {lastTrace.extracted_facts.length === 0 ? (
                  <div className="p-3 rounded-xl bg-slate-950 text-slate-500 text-xs">
                    No structured facts met confidence thresholds.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {lastTrace.extracted_facts.map((f, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-slate-950/80 border border-emerald-500/30 flex items-center justify-between text-xs font-mono"
                      >
                        <div>
                          <span className="text-emerald-400 font-bold">({f.subject})</span>
                          <span className="text-cyan-300 mx-2">&mdash;[{f.predicate}]&rarr;</span>
                          <span className="text-white font-bold">({f.object})</span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/15 text-emerald-400">
                          Active &bull; {(f.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Invalidated / Contradicted Facts */}
              {lastTrace.invalidated_facts.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-mono text-amber-400 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Contradictions Resolved / Closed Intervals ({lastTrace.invalidated_facts.length}):</span>
                  </span>
                  <div className="space-y-1.5">
                    {lastTrace.invalidated_facts.map((f, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-slate-950/80 border border-amber-500/30 flex items-center justify-between text-xs font-mono"
                      >
                        <div>
                          <span className="text-slate-300">({f.subject})</span>
                          <span className="text-amber-400 mx-2">&mdash;[{f.predicate}]&rarr;</span>
                          <span className="text-slate-300">({f.object})</span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/15 text-amber-400">
                          Closed: {f.valid_to ? f.valid_to.split("T")[0] : "Now"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 space-y-2">
              <Zap className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No Pipeline Run Yet</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Select a test scenario on the left or enter a custom statement to trace rule matches, latencies, and token expenditures.
              </p>
            </div>
          )}

          {/* Historical Fact Logs from DB */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">
                Recent Extracted Facts Audit
              </h3>
              <span className="text-[10px] font-mono text-slate-400">
                {facts.length} facts in memory
              </span>
            </div>

            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {facts.slice(0, 6).map((f) => (
                <div
                  key={f.id}
                  className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs font-mono"
                >
                  <div className="truncate pr-2">
                    <span className="text-slate-300">({f.subject})</span>
                    <span className="text-cyan-400 mx-1.5">[{f.predicate}]</span>
                    <span className="text-slate-100">({f.object})</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[10px] text-slate-400">
                      {f.source || "rule"}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      f.is_current ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"
                    }`}>
                      {f.is_current ? "ACTIVE" : "CLOSED"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
