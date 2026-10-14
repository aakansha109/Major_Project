"use client";

import React, { useState } from "react";
import { IngestResponse, Episode } from "@/types";
import { 
  Send, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  Zap, 
  Coins, 
  Timer, 
  ShieldAlert, 
  ArrowRight,
  MessageSquare
} from "lucide-react";

interface IngestionTabProps {
  onIngest: (payload: { session_id?: string; speaker?: string; text: string; timestamp?: string }) => Promise<IngestResponse>;
  recentEpisodes: Episode[];
}

const PRESET_UTTERANCES = [
  { text: "Alice moved to Seattle in 2020.", time: "2020-02-01T10:00:00Z", label: "Alice Relocation 2020" },
  { text: "Alice moved to London in 2023.", time: "2023-05-10T14:00:00Z", label: "Alice Relocation 2023 (Contradiction)" },
  { text: "Bob joined Google in 2019.", time: "2019-07-01T09:00:00Z", label: "Bob Career 2019" },
  { text: "Bob joined OpenAI in 2024.", time: "2024-01-15T11:00:00Z", label: "Bob Career 2024 (Contradiction)" },
  { text: "Charlie became a Principal Engineer in 2022.", time: "2022-08-01T10:00:00Z", label: "Charlie Promotion" },
  { text: "Diana upgraded to a MacBook Pro M3.", time: "2024-02-10T16:00:00Z", label: "Diana Hardware" }
];

export const IngestionTab: React.FC<IngestionTabProps> = ({ onIngest, recentEpisodes }) => {
  const [text, setText] = useState("");
  const [speaker, setSpeaker] = useState<"user" | "assistant">("user");
  const [customTime, setCustomTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<IngestResponse | null>(null);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    try {
      const resp = await onIngest({
        speaker,
        text: text.trim(),
        timestamp: customTime ? new Date(customTime).toISOString() : new Date().toISOString()
      });
      setLastResponse(resp);
      setText("");
    } catch (err: any) {
      alert(`Ingestion failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = (preset: typeof PRESET_UTTERANCES[0]) => {
    setText(preset.text);
    setCustomTime(preset.time.slice(0, 16));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left Input & Presets Column */}
      <div className="lg:col-span-7 space-y-5">
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              <span>Conversation Episode Ingestion</span>
            </h2>
            <span className="text-xs text-slate-400">Deterministic Rules First + LLM Fallback</span>
          </div>

          {/* Quick Presets */}
          <div className="mb-4">
            <label className="text-xs font-medium text-slate-400 mb-2 block">
              Quick Temporal Test Scenarios:
            </label>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_UTTERANCES.map((p, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleApplyPreset(p)}
                  className="px-2.5 py-1 text-xs rounded-md bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-300 hover:text-cyan-300 transition"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Ingestion Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
                <span>Utterance Text</span>
                <div className="flex items-center gap-2">
                  <span>Speaker:</span>
                  <button
                    type="button"
                    onClick={() => setSpeaker("user")}
                    className={`px-2 py-0.5 rounded text-[11px] ${speaker === "user" ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "text-slate-400"}`}
                  >
                    User
                  </button>
                  <button
                    type="button"
                    onClick={() => setSpeaker("assistant")}
                    className={`px-2 py-0.5 rounded text-[11px] ${speaker === "assistant" ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40" : "text-slate-400"}`}
                  >
                    Assistant
                  </button>
                </div>
              </div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="e.g., Alice moved to London in 2023. She joined DeepMind in 2023."
                rows={3}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-slate-750 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <span className="text-xs text-slate-400">Timestamp:</span>
                <input
                  type="datetime-local"
                  value={customTime}
                  onChange={(e) => setCustomTime(e.target.value)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-750 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !text.trim()}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 transition shadow-lg shadow-cyan-500/10 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Zap className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Processing Ingestion...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Ingest Episode</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Live Conversation Stream */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Recent Conversation History ({recentEpisodes.length} episodes)
          </h3>
          <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
            {recentEpisodes.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-4 text-center">
                No episodes ingested yet. Use the presets above or click "Seed Demo".
              </p>
            ) : (
              recentEpisodes.slice().reverse().map((ep) => (
                <div
                  key={ep.id}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-start justify-between gap-3 hover:border-slate-700 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${ep.speaker === "user" ? "bg-cyan-500/20 text-cyan-300" : "bg-indigo-500/20 text-indigo-300"}`}>
                        {ep.speaker}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {new Date(ep.timestamp).toLocaleDateString()} {new Date(ep.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200">{ep.text}</p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 shrink-0">
                    {ep.id.slice(0, 8)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Ingestion Telemetry & Contradiction Resolution Card */}
      <div className="lg:col-span-5 space-y-5">
        {lastResponse ? (
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Ingestion Pipeline Telemetry</span>
              </h3>
              <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${lastResponse.telemetry.strategy === "rule_only" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"}`}>
                {lastResponse.telemetry.strategy === "rule_only" ? "Deterministic Rule" : "LLM Fallback"}
              </span>
            </div>

            {/* Cost & Efficiency KPI Badges */}
            <div className="grid grid-cols-3 gap-2.5">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide block">Cost</span>
                <strong className={`text-base font-bold ${lastResponse.telemetry.cost_usd === 0 ? "text-emerald-400" : "text-amber-400"}`}>
                  ${lastResponse.telemetry.cost_usd.toFixed(4)}
                </strong>
                <span className="text-[10px] text-slate-500 block">USD</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide block">Tokens</span>
                <strong className={`text-base font-bold ${lastResponse.telemetry.tokens_consumed === 0 ? "text-emerald-400" : "text-indigo-400"}`}>
                  {lastResponse.telemetry.tokens_consumed}
                </strong>
                <span className="text-[10px] text-slate-500 block">Tokens</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide block">Latency</span>
                <strong className="text-base font-bold text-cyan-400">
                  {lastResponse.telemetry.total_latency_ms.toFixed(1)}
                </strong>
                <span className="text-[10px] text-slate-500 block">ms</span>
              </div>
            </div>

            {/* Contradiction Alert Banner if applicable */}
            {lastResponse.invalidated_facts.length > 0 && (
              <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/50 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-rose-300">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>Temporal Contradiction Detected & Resolved!</span>
                </div>
                <div className="text-xs text-rose-200/80 space-y-1">
                  {lastResponse.invalidated_facts.map((inf) => (
                    <div key={inf.id} className="font-mono text-[11px] bg-rose-950/60 p-2 rounded border border-rose-900/40">
                      Superseded: <strong>({inf.subject} &rarr; {inf.predicate} &rarr; {inf.object})</strong><br />
                      Invalidated as of new fact effective time.
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Facts List */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Extracted Bi-temporal Facts ({lastResponse.extracted_facts.length})
              </h4>
              <div className="space-y-2">
                {lastResponse.extracted_facts.map((fact) => (
                  <div
                    key={fact.id}
                    className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-cyan-300 font-semibold">
                        ({fact.subject}) &mdash;[{fact.predicate}]&rarr; ({fact.object})
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                        Active
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span>Valid From: <strong className="text-slate-300">{fact.valid_from.slice(0, 10)}</strong></span>
                      <span>Confidence: <strong className="text-slate-300">{(fact.confidence * 100).toFixed(0)}%</strong></span>
                      {fact.rule_name && (
                        <span className="text-slate-500 font-mono text-[10px]">[{fact.rule_name}]</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-panel rounded-2xl p-8 border border-slate-800 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 mx-auto flex items-center justify-center">
              <Zap className="w-6 h-6 text-cyan-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">Live Pipeline Telemetry</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
              Ingest an utterance or click any of the preset scenarios on the left to see deterministic rule matching, zero-token cost tracking, and temporal contradiction supersession.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
