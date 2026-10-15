"use client";

import React, { useState } from "react";
import { ChatResponse } from "@/types";
import { api } from "@/lib/api";
import { 
  MessageSquare, 
  Send, 
  Sparkles, 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  History, 
  Database, 
  Cpu, 
  Zap, 
  Layers, 
  CheckCircle2, 
  HelpCircle,
  ArrowRight
} from "lucide-react";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  responseMeta?: ChatResponse;
  timestamp: Date;
}

const SAMPLE_QUESTIONS = [
  { text: "What framework do I use now?", category: "Current State" },
  { text: "What framework did I use before?", category: "Previous State" },
  { text: "Where do I live now?", category: "Current State" },
  { text: "Where did I live previously?", category: "Previous State" },
  { text: "Where did Alice live in 2021?", category: "Point-in-Time" },
  { text: "Show the history of my backend framework.", category: "Timeline / Evolution" },
  { text: "Where did Bob work in 2020?", category: "Point-in-Time" },
  { text: "What is my favorite ice cream flavor?", category: "Ungrounded Guard" }
];

export const ChatTab: React.FC = () => {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hello! I am your Chronos Temporal Memory Assistant. I retrieve verified facts from your temporal knowledge graph and conversation history. You can ask about your current state, previous historical states, point-in-time facts on specific dates, or request a complete history timeline.",
      timestamp: new Date()
    }
  ]);

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: textToSend.trim(),
      timestamp: new Date()
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await api.chat({ message: textToSend.trim() });
      const assistantMsg: ChatMessage = {
        id: `assistant_${Date.now()}`,
        sender: "assistant",
        text: resp.answer,
        responseMeta: resp,
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "assistant",
        text: `Error connecting to conversational memory engine: ${err.message}`,
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Sample Chips */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-cyan-400" />
              <span>Conversational Temporal Memory Retrieval</span>
            </h2>
            <p className="text-xs text-slate-400">
              Interactive chat querying persisted active facts, superseded historical transitions, and conversation provenance.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-[11px] font-mono text-cyan-300">
            Bi-Temporal Grounded
          </span>
        </div>

        {/* Quick Sample Questions */}
        <div className="space-y-2">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
            Suggested Verification Questions:
          </span>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(item.text)}
                disabled={loading}
                className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-750 hover:border-cyan-500/40 text-xs text-slate-300 hover:text-cyan-300 transition flex items-center gap-1.5"
              >
                <span className="text-[10px] text-slate-500 uppercase font-mono font-bold">[{item.category}]</span>
                <span>{item.text}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Messages Stream */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 min-h-[420px] max-h-[580px] overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`max-w-2xl rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                msg.sender === "user"
                  ? "bg-gradient-to-r from-cyan-600 to-indigo-600 text-white rounded-br-none shadow-md shadow-cyan-600/10"
                  : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none space-y-3"
              }`}
            >
              <div className="whitespace-pre-line">{msg.text}</div>

              {/* Provenance and Evidence Metadata (Assistant Only) */}
              {msg.responseMeta && (
                <div className="pt-3 border-t border-slate-800/80 space-y-2.5 text-xs text-slate-400">
                  {/* Status Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        msg.responseMeta.grounded
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      }`}
                    >
                      {msg.responseMeta.grounded ? (
                        <>
                          <ShieldCheck className="w-3 h-3 text-emerald-400" />
                          <span>Grounded Evidence</span>
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="w-3 h-3 text-amber-400" />
                          <span>Ungrounded / No Records</span>
                        </>
                      )}
                    </span>

                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      Method: {msg.responseMeta.retrieval_method}
                    </span>

                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                      Confidence: {(msg.responseMeta.confidence * 100).toFixed(0)}%
                    </span>

                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                      {msg.responseMeta.latency_ms.toFixed(1)} ms
                    </span>
                  </div>

                  {/* Supporting Fact IDs & Source Episodes */}
                  {(msg.responseMeta.supporting_fact_ids.length > 0 || msg.responseMeta.source_episode_ids.length > 0) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                      {msg.responseMeta.supporting_fact_ids.length > 0 && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                          <span className="text-slate-500 block mb-0.5">Supporting Fact IDs:</span>
                          <span className="text-cyan-400 truncate block">
                            {msg.responseMeta.supporting_fact_ids.join(", ")}
                          </span>
                        </div>
                      )}

                      {msg.responseMeta.source_episode_ids.length > 0 && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                          <span className="text-slate-500 block mb-0.5">Source Episode IDs:</span>
                          <span className="text-indigo-400 truncate block">
                            {msg.responseMeta.source_episode_ids.join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Temporal Validity Details */}
                  {Object.keys(msg.responseMeta.temporal_validity).length > 0 && (
                    <div className="p-2 rounded bg-slate-950/80 border border-slate-850 text-[11px]">
                      <span className="text-slate-500 font-mono block mb-1">Temporal Validity Verification:</span>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-slate-300">
                        {msg.responseMeta.temporal_validity.valid_from && (
                          <span>Valid From: <strong className="text-emerald-400">{msg.responseMeta.temporal_validity.valid_from.slice(0, 10)}</strong></span>
                        )}
                        {msg.responseMeta.temporal_validity.valid_to ? (
                          <span>Valid To: <strong className="text-rose-400">{msg.responseMeta.temporal_validity.valid_to.slice(0, 10)}</strong></span>
                        ) : (
                          msg.responseMeta.temporal_validity.valid_from && <span>Valid To: <strong className="text-cyan-400">Present (Current)</strong></span>
                        )}
                        {msg.responseMeta.temporal_validity.as_of && (
                          <span>Evaluated As Of: <strong className="text-indigo-400">{msg.responseMeta.temporal_validity.as_of.slice(0, 10)}</strong></span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Reasoning Chain */}
                  {msg.responseMeta.reasoning_chain.length > 0 && (
                    <details className="text-[11px] text-slate-400 cursor-pointer">
                      <summary className="hover:text-slate-300 transition">View Temporal Reasoning Steps ({msg.responseMeta.reasoning_chain.length})</summary>
                      <ul className="mt-1.5 pl-3 space-y-1 list-disc list-inside text-slate-400 font-mono">
                        {msg.responseMeta.reasoning_chain.map((step, sIdx) => (
                          <li key={sIdx}>{step}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-500 mt-1 px-1">
              {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 p-3 text-xs text-cyan-400 animate-pulse font-mono">
            <Zap className="w-4 h-4 animate-spin text-cyan-400" />
            <span>Traversing temporal knowledge graph intervals and retrieving conversation episodes...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-3 glass-panel rounded-2xl p-2.5 border border-slate-800"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about current state, past history, or timeline (e.g. 'What framework do I use now?')..."
          className="flex-1 bg-transparent px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-indigo-400 hover:from-cyan-300 hover:to-indigo-300 transition shadow-lg shadow-cyan-500/10 disabled:opacity-50"
        >
          <Send className="w-4 h-4 fill-slate-950" />
          <span>Ask Memory</span>
        </button>
      </form>
    </div>
  );
};
