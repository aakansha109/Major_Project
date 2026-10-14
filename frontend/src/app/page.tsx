"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { OverviewTab } from "@/components/OverviewTab";
import { ConversationLabTab } from "@/components/ConversationLabTab";
import { TemporalGraphTab } from "@/components/TemporalGraphTab";
import { ExtractionPipelineTab } from "@/components/ExtractionPipelineTab";
import { EvaluationTab } from "@/components/EvaluationTab";
import { NextSprintTab } from "@/components/NextSprintTab";
import { api } from "@/lib/api";
import { 
  HealthResponse, 
  Episode, 
  Fact, 
  EvaluationResult,
  Subgraph 
} from "@/types";
import { 
  LayoutDashboard,
  MessageSquare, 
  Network, 
  Zap, 
  BarChart3, 
  Rocket,
  AlertCircle
} from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "conversation" | "graph" | "pipeline" | "evaluation" | "sprint"
  >("overview");

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [latestEval, setLatestEval] = useState<EvaluationResult | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  const fetchSystemData = async () => {
    setHealthLoading(true);
    setInitError(null);
    try {
      const h = await api.getHealth();
      setHealth(h);

      const [eps, fcts, ev] = await Promise.all([
        api.getEpisodes(undefined, 50).catch(() => []),
        api.getFacts({ limit: 200 }).catch(() => []),
        api.getLatestEvaluation().catch(() => null)
      ]);

      setEpisodes(eps);
      setFacts(fcts);
      if (ev && "run_id" in ev) {
        setLatestEval(ev as EvaluationResult);
      }
    } catch (err: any) {
      console.warn("Backend not yet connected:", err.message);
      setInitError("Connecting to Chronos Backend API... (Ensure backend is running on http://127.0.0.1:8000)");
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemData();
    const interval = setInterval(fetchSystemData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSeed = async () => {
    await api.seedSampleData();
    await fetchSystemData();
  };

  const handleReset = async () => {
    await api.resetDatabase();
    await fetchSystemData();
  };

  const handleIngest = async (payload: { session_id?: string; speaker?: string; text: string; timestamp?: string }) => {
    const res = await api.ingestEpisode(payload);
    await fetchSystemData();
    return res;
  };

  const handleFetchGraph = async (asOf?: string): Promise<Subgraph> => {
    return await api.getGraph(asOf);
  };

  const handleRunEvaluation = async (): Promise<EvaluationResult> => {
    const res = await api.runEvaluation();
    setLatestEval(res);
    await fetchSystemData();
    return res;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Global Header */}
      <Header
        health={health}
        loading={healthLoading}
        onRefresh={fetchSystemData}
        onSeed={handleSeed}
        onReset={handleReset}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {initError && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-xs text-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>{initError}</span>
            </div>
            <button
              onClick={fetchSystemData}
              className="px-2.5 py-1 rounded bg-amber-900/60 hover:bg-amber-800 text-[11px] font-semibold text-amber-100 transition"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* 6 Required Tab Navigation Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-800/80 no-scrollbar">
          {/* Tab 1: Overview */}
          <button
            onClick={() => setActiveTab("overview")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "overview"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <LayoutDashboard className="w-4 h-4 text-cyan-400" />
            <span>Overview</span>
          </button>

          {/* Tab 2: Conversation Lab */}
          <button
            onClick={() => setActiveTab("conversation")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "conversation"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <span>Conversation Lab</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 font-mono">Live</span>
          </button>

          {/* Tab 3: Knowledge Graph */}
          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "graph"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Network className="w-4 h-4 text-emerald-400" />
            <span>Knowledge Graph</span>
          </button>

          {/* Tab 4: Extraction Pipeline */}
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "pipeline"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Zap className="w-4 h-4 text-amber-400" />
            <span>Extraction Pipeline</span>
          </button>

          {/* Tab 5: Evaluation */}
          <button
            onClick={() => setActiveTab("evaluation")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "evaluation"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <span>Evaluation</span>
          </button>

          {/* Tab 6: Next Sprint */}
          <button
            onClick={() => setActiveTab("sprint")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === "sprint"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Rocket className="w-4 h-4 text-purple-400" />
            <span>Next Sprint</span>
          </button>
        </div>

        {/* Tab Viewport */}
        <div>
          {/* Page 1: Overview */}
          {activeTab === "overview" && (
            <OverviewTab
              health={health}
              loading={healthLoading}
              facts={facts}
              episodes={episodes}
              onRefresh={fetchSystemData}
              onSeed={handleSeed}
              onReset={handleReset}
              onNavigateToTab={(tab: string) => setActiveTab(tab as any)}
            />
          )}

          {/* Page 2: Conversation Lab */}
          {activeTab === "conversation" && (
            <ConversationLabTab
              episodes={episodes}
              onMemoryChange={fetchSystemData}
            />
          )}

          {/* Page 3: Knowledge Graph */}
          {activeTab === "graph" && (
            <TemporalGraphTab
              onFetchGraph={handleFetchGraph}
            />
          )}

          {/* Page 4: Extraction Pipeline */}
          {activeTab === "pipeline" && (
            <ExtractionPipelineTab
              onIngest={handleIngest}
              recentEpisodes={episodes}
              facts={facts}
              onRefresh={fetchSystemData}
            />
          )}

          {/* Page 5: Evaluation */}
          {activeTab === "evaluation" && (
            <EvaluationTab
              onRunEvaluation={handleRunEvaluation}
              latestResult={latestEval}
            />
          )}

          {/* Page 6: Next Sprint */}
          {activeTab === "sprint" && (
            <NextSprintTab />
          )}
        </div>
      </main>
    </div>
  );
}
