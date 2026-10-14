"use client";

import React, { useState } from "react";
import { HealthResponse, Fact, Episode } from "@/types";
import { 
  Database, 
  Layers, 
  Cpu, 
  GitCommit, 
  ShieldAlert, 
  Sparkles, 
  Trash2, 
  Activity, 
  CheckCircle2, 
  Clock, 
  FileText, 
  ArrowRight,
  TrendingDown,
  Terminal,
  Zap,
  Info
} from "lucide-react";

interface OverviewTabProps {
  health: HealthResponse | null;
  loading: boolean;
  facts: Fact[];
  episodes: Episode[];
  onRefresh: () => void;
  onSeed: () => Promise<void>;
  onReset: () => Promise<void>;
  onNavigateToTab: (tab: string) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  health,
  loading,
  facts,
  episodes,
  onRefresh,
  onSeed,
  onReset,
  onNavigateToTab,
}) => {
  const [resetting, setResetting] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const metrics = health?.storage.metrics;
  const entityCount = metrics?.entity_count ?? 0;
  const activeFactsCount = metrics?.active_facts_count ?? facts.filter(f => f.is_current).length;
  const supersededFactsCount = metrics?.superseded_facts_count ?? facts.filter(f => !f.is_current).length;
  const extractionCallsCount = metrics?.extraction_calls_count ?? (metrics?.episode_count ?? episodes.length);
  const totalTokens = metrics?.total_tokens_used ?? 0;
  const totalCost = metrics?.total_cost_usd ?? 0;
  const isNeo4j = health?.storage.neo4j_connected ?? false;

  const handleResetWithConfirm = async () => {
    const confirmed = window.confirm(
      "CONFIRM DATABASE RESET:\n\nAre you sure you want to purge all conversation episodes, entities, active facts, and superseded temporal edges?\n\nThis will call POST /api/reset on the backend."
    );
    if (!confirmed) return;

    setResetting(true);
    try {
      await onReset();
    } finally {
      setResetting(false);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await onSeed();
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / System Title */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-indigo-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-full bg-gradient-to-l from-cyan-500/5 to-transparent pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                System Overview
              </span>
              <span className="text-xs text-slate-400 font-mono">
                B.Tech Major Project (AI & ML)
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Chronos Temporal Memory Dashboard
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl">
              Real-time bi-temporal graph telemetry with confidence-gated extraction, historical fact resolution, and zero fabricated metrics.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleSeed}
              disabled={seeding || loading}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-cyan-300 bg-cyan-950/80 border border-cyan-700/60 hover:bg-cyan-900/80 transition shadow-sm disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${seeding ? "animate-spin" : ""}`} />
              <span>{seeding ? "Seeding Scenarios..." : "Seed Benchmark Scenarios"}</span>
            </button>

            <button
              onClick={handleResetWithConfirm}
              disabled={resetting || loading}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-300 bg-rose-950/40 border border-rose-800/60 hover:bg-rose-900/50 hover:text-rose-200 transition shadow-sm disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              <span>{resetting ? "Resetting..." : "Reset Memory Store"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Core Real Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Entities */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition relative group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Total Entities
            </span>
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-bold font-mono text-white tracking-tight">
              {entityCount}
            </div>
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span>Distinct graph entities</span>
            </p>
          </div>
        </div>

        {/* Metric 2: Active Facts */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/30 transition relative group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Active Facts
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-bold font-mono text-emerald-400 tracking-tight">
              {activeFactsCount}
            </div>
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span>Currently valid knowledge</span>
            </p>
          </div>
        </div>

        {/* Metric 3: Superseded Facts */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-amber-500/30 transition relative group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Superseded Facts
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:scale-105 transition">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-bold font-mono text-amber-400 tracking-tight">
              {supersededFactsCount}
            </div>
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span>Historical closed intervals</span>
            </p>
          </div>
        </div>

        {/* Metric 4: Extraction Calls */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/30 transition relative group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Extraction Calls
            </span>
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-bold font-mono text-indigo-300 tracking-tight">
              {extractionCallsCount}
            </div>
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span>Hybrid pipeline executions</span>
            </p>
          </div>
        </div>
      </div>

      {/* Secondary Telemetry: Backend Engines & Extraction Efficiency */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Persistence & Graph Engine Status */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <span>Storage Architecture</span>
            </h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold ${
              isNeo4j 
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" 
                : "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
            }`}>
              {isNeo4j ? "Neo4j Active" : "SQLite Mirror"}
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Primary Graph Store</span>
              <span className="font-mono text-slate-200">{health?.storage.graph_backend || "Resilient SQLite"}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Neo4j Bolt URI</span>
              <span className="font-mono text-slate-300 truncate max-w-[180px]">{health?.storage.neo4j_uri || "bolt://localhost:7687"}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Total Episodes Stored</span>
              <span className="font-mono font-semibold text-slate-100">{metrics?.episode_count ?? episodes.length}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Total Facts in Memory</span>
              <span className="font-mono font-semibold text-slate-100">{metrics?.fact_count ?? facts.length}</span>
            </div>
          </div>
        </div>

        {/* Cost & Token Consumption */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Extraction Telemetry</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">Live Counters</span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Deterministic Rule Extractions</span>
              <span className="font-mono font-bold text-emerald-400">{metrics?.rule_extractions_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">LLM Fallback Extractions</span>
              <span className="font-mono font-bold text-indigo-400">{metrics?.llm_extractions_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Measured Tokens Consumed</span>
              <span className="font-mono font-bold text-slate-200">{totalTokens.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Estimated API Cost (USD)</span>
              <span className="font-mono font-bold text-amber-400">${totalCost.toFixed(5)}</span>
            </div>
          </div>
        </div>

        {/* LLM Engine Configuration */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>Extractor Engine</span>
            </h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
              health?.llm_fallback_enabled 
                ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30" 
                : "bg-slate-800 text-slate-400"
            }`}>
              {health?.llm_fallback_enabled ? "Fallback Active" : "Rules Only"}
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">LLM Provider API</span>
              <span className={`font-mono ${health?.llm_api_configured ? "text-emerald-400" : "text-slate-400"}`}>
                {health?.llm_api_configured ? "Configured" : "Offline / Unset"}
              </span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Model Name</span>
              <span className="font-mono text-slate-200">{health?.llm_model || "None"}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">API Health Status</span>
              <span className="font-mono text-emerald-400 capitalize">{health?.status || "operational"}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400">Uptime</span>
              <span className="font-mono text-slate-300">
                {health?.uptime_seconds ? `${Math.floor(health.uptime_seconds / 60)}m ${Math.floor(health.uptime_seconds % 60)}s` : "Online"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Facts Snapshot */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">
              Memory Graph State (Recent Facts)
            </h3>
            <p className="text-xs text-slate-400">
              Live snapshot of latest temporal facts stored in the knowledge graph.
            </p>
          </div>
          <button
            onClick={() => onNavigateToTab("graph")}
            className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold transition"
          >
            <span>Open Graph Inspector</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {facts.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-950/40 border border-slate-800/80">
            <Info className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-300">No memory facts stored yet</p>
            <p className="text-xs text-slate-500 mt-1">
              Ingest a message in Conversation Lab or click "Seed Benchmark Scenarios" above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 font-mono uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Subject</th>
                  <th className="py-2.5 px-3">Predicate</th>
                  <th className="py-2.5 px-3">Object</th>
                  <th className="py-2.5 px-3">Valid From</th>
                  <th className="py-2.5 px-3">Valid To</th>
                  <th className="py-2.5 px-3">Extractor</th>
                  <th className="py-2.5 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {facts.slice(0, 8).map((f) => (
                  <tr key={f.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-2.5 px-3">
                      {f.is_current ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          SUPERSEDED
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-200">{f.subject}</td>
                    <td className="py-2.5 px-3 font-mono text-cyan-300">{f.predicate}</td>
                    <td className="py-2.5 px-3 text-slate-200">{f.object}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">
                      {f.valid_from ? f.valid_from.split("T")[0] : "-"}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">
                      {f.valid_to ? f.valid_to.split("T")[0] : <span className="text-emerald-400 font-semibold">Open / Now</span>}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-mono text-[11px] text-slate-400">
                        {f.source || "rule"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">
                      {(f.confidence * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
