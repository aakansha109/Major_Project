"use client";

import React, { useState } from "react";
import { Fact } from "@/types";
import { 
  Layers, 
  Search, 
  Filter, 
  Clock, 
  ShieldCheck, 
  History, 
  ExternalLink 
} from "lucide-react";

interface AuditTabProps {
  facts: Fact[];
  loading: boolean;
  onRefresh: () => void;
}

export const AuditTab: React.FC<AuditTabProps> = ({ facts, loading, onRefresh }) => {
  const [search, setSearch] = useState("");
  const [onlyCurrent, setOnlyCurrent] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<string>("all");

  const filteredFacts = facts.filter((f) => {
    if (onlyCurrent && !f.is_current) return false;
    if (sourceFilter !== "all" && f.source !== sourceFilter) return false;
    if (search.trim()) {
      const s = search.toLowerCase();
      return (
        f.subject.toLowerCase().includes(s) ||
        f.predicate.toLowerCase().includes(s) ||
        f.object.toLowerCase().includes(s) ||
        (f.raw_text && f.raw_text.toLowerCase().includes(s))
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter entities, relations, values..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-750 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 w-full md:w-auto">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyCurrent}
              onChange={(e) => setOnlyCurrent(e.target.checked)}
              className="rounded bg-slate-900 border-slate-750 text-cyan-500 focus:ring-0"
            />
            <span className="text-slate-300">Only Active Facts</span>
          </label>

          <div className="flex items-center gap-2">
            <span>Source:</span>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-750 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Sources</option>
              <option value="rule">Deterministic Rules</option>
              <option value="llm">LLM Fallback</option>
            </select>
          </div>

          <span className="text-slate-500 font-mono text-[11px]">
            Showing {filteredFacts.length} of {facts.length} facts
          </span>
        </div>
      </div>

      {/* Facts Table */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono">
                <th className="pb-3">Subject</th>
                <th className="pb-3">Predicate</th>
                <th className="pb-3">Object</th>
                <th className="pb-3">Valid From</th>
                <th className="pb-3">Valid To</th>
                <th className="pb-3">Status</th>
                <th className="pb-3">Source</th>
                <th className="pb-3">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {filteredFacts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                    No facts match current filters.
                  </td>
                </tr>
              ) : (
                filteredFacts.map((fact) => (
                  <tr key={fact.id} className="text-slate-300 hover:bg-slate-900/50">
                    <td className="py-3 font-semibold text-white">{fact.subject}</td>
                    <td className="py-3 font-mono text-cyan-400">{fact.predicate}</td>
                    <td className="py-3 font-medium text-slate-200">{fact.object}</td>
                    <td className="py-3 font-mono text-[11px] text-slate-400">{fact.valid_from.slice(0, 10)}</td>
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {fact.valid_to ? fact.valid_to.slice(0, 10) : <span className="text-emerald-400">Ongoing</span>}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${fact.is_current ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400 line-through"}`}>
                        {fact.is_current ? "Active" : "Superseded"}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${fact.source === "rule" ? "bg-cyan-500/20 text-cyan-300" : "bg-indigo-500/20 text-indigo-300"}`}>
                        {fact.source}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-slate-400">
                      {(fact.confidence * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
