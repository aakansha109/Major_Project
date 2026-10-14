"use client";

import React, { useState } from "react";
import { HealthResponse } from "@/types";
import { 
  Database, 
  Cpu, 
  Sparkles, 
  Trash2, 
  RefreshCw, 
  Clock, 
  DollarSign, 
  ShieldCheck, 
  Layers 
} from "lucide-react";

interface HeaderProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
  onSeed: () => Promise<void>;
  onReset: () => Promise<void>;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  loading,
  onRefresh,
  onSeed,
  onReset
}) => {
  const [seeding, setSeeding] = useState(false);
  const [resetting, setResetting] = useState(false);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await onSeed();
    } finally {
      setSeeding(false);
    }
  };

  const handleReset = async () => {
    if (confirm("Are you sure you want to clear all memory facts and episodes?")) {
      setResetting(true);
      try {
        await onReset();
      } finally {
        setResetting(false);
      }
    }
  };

  const isNeo4j = health?.storage.neo4j_connected;
  const metrics = health?.storage.metrics;

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Title and Badges */}
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 via-indigo-600 to-emerald-500 p-0.5 shadow-lg shadow-cyan-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Clock className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <span>CHRONOS MEMORY</span>
                </h1>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Major Project
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  v1.0.0
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Cost-Efficient Temporal Knowledge Graph Memory for Conversational AI Agents
              </p>
            </div>
          </div>

          {/* Real-time Telemetry & Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Backend Backend Status Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
              <span className={`w-2 h-2 rounded-full ${isNeo4j ? "bg-emerald-400 animate-pulse" : "bg-cyan-400"}`} />
              <span className="font-medium text-slate-200">
                {isNeo4j ? "Neo4j Graph Active" : "SQLite Resilient Mirror"}
              </span>
            </div>

            {/* Live Metrics Counts */}
            <div className="hidden lg:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <strong className="text-slate-200">{metrics?.fact_count ?? 0}</strong> Facts
              </span>
              <span className="text-slate-700">|</span>
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                <strong className="text-slate-200">{metrics?.episode_count ?? 0}</strong> Episodes
              </span>
            </div>

            {/* Seed Sample Data Button */}
            <button
              onClick={handleSeed}
              disabled={seeding || loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-cyan-300 bg-cyan-950/60 border border-cyan-800/60 hover:bg-cyan-900/60 transition disabled:opacity-50"
              title="Populate multi-year temporal benchmark scenarios"
            >
              <Sparkles className={`w-3.5 h-3.5 ${seeding ? "animate-spin" : ""}`} />
              <span>{seeding ? "Seeding..." : "Seed Demo"}</span>
            </button>

            {/* Reset Button */}
            <button
              onClick={handleReset}
              disabled={resetting || loading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 bg-slate-900 border border-slate-800 hover:text-rose-400 hover:border-rose-900/50 transition disabled:opacity-50"
              title="Clear all stored memory"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 rounded-lg text-slate-400 bg-slate-900 border border-slate-800 hover:text-slate-200 transition"
              title="Refresh status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
