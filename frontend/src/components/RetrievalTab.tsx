"use client";

import React, { useState } from "react";
import { RetrievalResult } from "@/types";
import { 
  Search, 
  Clock, 
  Calendar, 
  CheckCircle2, 
  Zap, 
  Layers, 
  ArrowRight,
  MessageSquare,
  HelpCircle
} from "lucide-react";

interface RetrievalTabProps {
  onRetrieve: (payload: { query: string; as_of?: string | null }) => Promise<RetrievalResult>;
}

export const RetrievalTab: React.FC<RetrievalTabProps> = ({ onRetrieve }) => {
  const [query, setQuery] = useState("Where did Alice live?");
  const [asOfDate, setAsOfDate] = useState("2021-06-01");
  const [useAsOf, setUseAsOf] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RetrievalResult | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const resp = await onRetrieve({
        query: query.trim(),
        as_of: useAsOf && asOfDate ? `${asOfDate}T00:00:00Z` : null
      });
      setResult(resp);
    } catch (err: any) {
      alert(`Retrieval failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Bar & Time Snapshot Controls */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask or search temporal facts (e.g. 'Where did Alice live?')"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-750 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 transition shadow-lg shadow-cyan-500/10 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Zap className="w-4 h-4 animate-spin text-slate-950" />
                  <span>Searching Memory...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Search Memory</span>
                </>
              )}
            </button>
          </div>

          {/* Temporal Point-in-Time Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs text-slate-400 border-t border-slate-800/60">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useAsOf}
                  onChange={(e) => setUseAsOf(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                />
                <span className="text-slate-300 font-medium">Apply Point-in-Time Snapshot Filter</span>
              </label>

              {useAsOf && (
                <div className="flex items-center gap-2">
                  <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                  <input
                    type="date"
                    value={asOfDate}
                    onChange={(e) => setAsOfDate(e.target.value)}
                    className="px-2 py-1 rounded bg-slate-900 border border-slate-750 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 text-[11px]">
              <span>Sample Time Travel:</span>
              <button
                type="button"
                onClick={() => { setUseAsOf(true); setAsOfDate("2021-06-01"); }}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Mid-2021
              </button>
              <button
                type="button"
                onClick={() => { setUseAsOf(true); setAsOfDate("2024-06-01"); }}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Mid-2024
              </button>
              <button
                type="button"
                onClick={() => setUseAsOf(false)}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Present Day
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Results View */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Matched Facts Column */}
          <div className="lg:col-span-7 space-y-4">
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Temporally Valid Matched Facts ({result.matched_facts.length})</span>
                </h3>
                <span className="text-xs font-mono text-cyan-400">
                  Latency: {result.latency_ms}ms
                </span>
              </div>

              {result.matched_facts.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-6 text-center">
                  No facts were valid at this requested point in time.
                </p>
              ) : (
                <div className="space-y-3">
                  {result.matched_facts.map((fact) => (
                    <div
                      key={fact.id}
                      className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/40 transition space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-mono font-bold text-white">
                          ({fact.subject}) &mdash;[{fact.predicate}]&rarr; ({fact.object})
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${fact.is_current ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                          {fact.is_current ? "Active" : "Historical"}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
                        <span>Valid From: <strong className="text-slate-200">{fact.valid_from.slice(0, 10)}</strong></span>
                        <span>Valid To: <strong className="text-slate-200">{fact.valid_to ? fact.valid_to.slice(0, 10) : "Present (Ongoing)"}</strong></span>
                        <span>Source: <strong className="text-cyan-300 font-mono">{fact.source}</strong></span>
                      </div>

                      {fact.raw_text && (
                        <div className="p-2 rounded-lg bg-slate-950/60 border border-slate-850 text-xs text-slate-400 italic">
                          "{fact.raw_text}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Matched Episodes & Provenance Column */}
          <div className="lg:col-span-5 space-y-4">
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <h3 className="text-sm font-semibold text-white mb-4 pb-2 border-b border-slate-800 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-indigo-400" />
                <span>Conversation Episode Provenance</span>
              </h3>

              {result.matched_episodes.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-6 text-center">
                  No source conversation utterances linked.
                </p>
              ) : (
                <div className="space-y-3">
                  {result.matched_episodes.map((ep) => (
                    <div
                      key={ep.id}
                      className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-slate-500 font-mono text-[10px]">
                        <span>Episode: {ep.id.slice(0, 8)}</span>
                        <span>{new Date(ep.timestamp).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-200 font-sans text-xs">"{ep.text}"</p>
                    </div>
                  ))}
                </div>
              )}

              {/* 1-Hop Neighborhood Nodes */}
              {result.subgraph.nodes.length > 0 && (
                <div className="mt-5 pt-3 border-t border-slate-800">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                    Retrieved 1-Hop Neighborhood Subgraph
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {result.subgraph.nodes.map((node) => (
                      <span
                        key={node.id}
                        className="px-2.5 py-1 text-xs rounded-lg bg-slate-900 border border-slate-750 text-cyan-300 font-mono"
                      >
                        {node.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
