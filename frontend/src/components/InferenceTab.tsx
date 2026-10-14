"use client";

import React, { useState } from "react";
import { InferenceResponse } from "@/types";
import { 
  BrainCircuit, 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  History, 
  ShieldCheck, 
  Zap, 
  Clock 
} from "lucide-react";

interface InferenceTabProps {
  onInfer: (payload: { query: string; as_of?: string | null }) => Promise<InferenceResponse>;
}

const SAMPLE_QUESTIONS = [
  { q: "Where does Alice live now?", label: "Alice Present Location" },
  { q: "Where did Alice live in 2021?", label: "Alice Past Location (2021)" },
  { q: "Where does Bob work now?", label: "Bob Current Job" },
  { q: "Where did Bob work in 2020?", label: "Bob Former Job (2020)" },
  { q: "What role does Charlie hold?", label: "Charlie Promotion" }
];

export const InferenceTab: React.FC<InferenceTabProps> = ({ onInfer }) => {
  const [query, setQuery] = useState("Where does Alice live now?");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<InferenceResponse | null>(null);

  const handleAsk = async (questionText?: string) => {
    const q = questionText || query;
    if (!q.trim()) return;

    setLoading(true);
    try {
      const resp = await onInfer({ query: q.trim() });
      setResponse(resp);
      setQuery(q);
    } catch (err: any) {
      alert(`Inference failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Question Prompt Card */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-indigo-400" />
            <span>Temporal Task Inference Engine</span>
          </h2>
          <span className="text-xs text-slate-400">Contextual Reasoning over Graph Interval States</span>
        </div>

        {/* Sample Question Chips */}
        <div className="mb-4">
          <span className="text-xs text-slate-400 block mb-2">Example Temporal Queries:</span>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleAsk(item.q)}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-900 border border-slate-750 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50 transition"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Query Input */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask questions requiring temporal reasoning..."
            className="flex-1 w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-750 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <button
            onClick={() => handleAsk()}
            disabled={loading || !query.trim()}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-400 hover:to-cyan-400 transition shadow-lg shadow-indigo-500/10 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Zap className="w-4 h-4 animate-spin" />
                <span>Synthesizing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Run Inference</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Inference Output View */}
      {response && (
        <div className="space-y-6">
          {/* Synthesized Answer Card */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 bg-gradient-to-br from-slate-900/90 to-slate-950/90 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase font-mono font-semibold tracking-wider text-cyan-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Grounded Temporal Answer
              </span>
              <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                <span>Confidence: <strong>{(response.confidence * 100).toFixed(0)}%</strong></span>
                <span>•</span>
                <span>Latency: <strong>{response.latency_ms}ms</strong></span>
              </div>
            </div>

            <p className="text-lg font-semibold text-white leading-relaxed mb-4">
              {response.answer}
            </p>

            {/* Reasoning Steps Chain */}
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-850 space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Temporal Reasoning Chain:
              </span>
              {response.reasoning_chain.map((step, idx) => (
                <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300 font-mono">
                  <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Supporting Facts vs Superseded Facts Side-by-Side Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Supporting Active Facts */}
            <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Supporting Valid Facts ({response.supporting_facts.length})</span>
              </h3>
              <div className="space-y-2.5">
                {response.supporting_facts.map((fact) => (
                  <div key={fact.id} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1">
                    <span className="font-mono text-emerald-300 font-bold block">
                      ({fact.subject}) &mdash;[{fact.predicate}]&rarr; ({fact.object})
                    </span>
                    <div className="text-[11px] text-slate-400 flex items-center gap-3">
                      <span>Effective: <strong className="text-slate-200">{fact.valid_from.slice(0, 10)}</strong></span>
                      <span>Source: <strong className="text-cyan-300">{fact.source}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Superseded / Invalidated Facts */}
            <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-2">
                <History className="w-4 h-4" />
                <span>Superseded Historical Facts ({response.superseded_facts.length})</span>
              </h3>
              {response.superseded_facts.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-4 text-center">
                  No prior conflicting facts superseded for this entity.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {response.superseded_facts.map((fact) => (
                    <div key={fact.id} className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1">
                      <span className="font-mono text-amber-300/80 font-bold line-through block">
                        ({fact.subject}) &mdash;[{fact.predicate}]&rarr; ({fact.object})
                      </span>
                      <div className="text-[11px] text-slate-400 flex items-center gap-3">
                        <span>Valid: {fact.valid_from.slice(0, 10)} &rarr; {fact.valid_to ? fact.valid_to.slice(0, 10) : "superseded"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
