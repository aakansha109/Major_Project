"use client";

import React, { useState, useEffect } from "react";
import { Episode, Fact, ChatResponse, IngestResponse } from "@/types";
import { api } from "@/lib/api";
import { 
  MessageSquare, 
  Send, 
  Sparkles, 
  Clock, 
  History, 
  Database, 
  Cpu, 
  Zap, 
  Layers, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Bot,
  User,
  RefreshCw,
  Search
} from "lucide-react";

interface ConversationLabTabProps {
  episodes: Episode[];
  onMemoryChange: () => Promise<void>;
}

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  responseMeta?: ChatResponse;
  timestamp: Date;
}

const SAMPLE_EPISODES = [
  { text: "My backend framework is Flask.", session: "dev-session-1" },
  { text: "I switched my backend framework to FastAPI.", session: "dev-session-1" },
  { text: "I currently live in Seattle.", session: "profile-1" },
  { text: "I moved from Seattle to San Francisco last month.", session: "profile-1" },
  { text: "Alice joined Google in 2021 as a Staff Engineer.", session: "team-1" },
  { text: "Alice left Google and moved to DeepMind in 2023.", session: "team-1" }
];

const SAMPLE_QUESTIONS = [
  { text: "What framework do I use now?", category: "Current State" },
  { text: "What framework did I use before?", category: "Previous State" },
  { text: "Where do I live now?", category: "Current State" },
  { text: "Where did I live previously?", category: "Previous State" },
  { text: "Where did Alice work in 2021?", category: "Point-in-Time" },
  { text: "Show the history of my backend framework.", category: "Timeline / Evolution" },
  { text: "What is my favorite ice cream flavor?", category: "Ungrounded Guard" }
];

export const ConversationLabTab: React.FC<ConversationLabTabProps> = ({
  episodes,
  onMemoryChange
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"chat_qa" | "ingest_stream">("chat_qa");
  
  // Chat QA state
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hello! I am your Chronos Temporal Memory Assistant. Ask me about your current state, past historical states, point-in-time facts, or request an evolution timeline.",
      timestamp: new Date()
    }
  ]);

  // Episode Ingestion state
  const [ingestText, setIngestText] = useState("");
  const [sessionId, setSessionId] = useState("session-lab-1");
  const [speaker, setSpeaker] = useState("User");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  const handleSendChat = async (messageText?: string) => {
    const textToSend = messageText || chatInput;
    if (!textToSend.trim() || chatLoading) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: textToSend.trim(),
      timestamp: new Date()
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const resp = await api.chat({ message: textToSend.trim() });
      const assistantMsg: ChatMessage = {
        id: `assistant_${Date.now()}`,
        sender: "assistant",
        text: resp.answer,
        responseMeta: resp,
        timestamp: new Date()
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "assistant",
        text: `Error retrieving memory: ${err.message}`,
        timestamp: new Date()
      };
      setChatMessages((prev) => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleIngest = async (e?: React.FormEvent, customText?: string, customSession?: string) => {
    if (e) e.preventDefault();
    const textToIngest = customText || ingestText;
    const sessionToUse = customSession || sessionId;
    if (!textToIngest.trim() || ingestLoading) return;

    setIngestLoading(true);
    setIngestError(null);
    setIngestResult(null);

    try {
      const res = await api.ingestEpisode({
        session_id: sessionToUse,
        speaker: speaker || "User",
        text: textToIngest.trim(),
        timestamp: new Date().toISOString()
      });
      setIngestResult(res);
      setIngestText("");
      await onMemoryChange();
    } catch (err: any) {
      setIngestError(err.message || "Failed to ingest conversation episode");
    } finally {
      setIngestLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub-tab selection bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab("chat_qa")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeSubTab === "chat_qa"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Bot className="w-4 h-4 text-cyan-400" />
            <span>Temporal Memory Chat & QA</span>
          </button>

          <button
            onClick={() => setActiveSubTab("ingest_stream")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeSubTab === "ingest_stream"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <MessageSquare className="w-4 h-4 text-indigo-400" />
            <span>Episode Ingestion & Stream</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">
              {episodes.length}
            </span>
          </button>
        </div>

        <span className="text-xs text-slate-400 font-mono hidden sm:inline">
          POST /api/chat &bull; POST /api/episodes
        </span>
      </div>

      {/* VIEW 1: TEMPORAL MEMORY CHAT & QA */}
      {activeSubTab === "chat_qa" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chat Stream (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Sample Question Chips */}
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>Verification Queries (Current vs Historical vs Evolution):</span>
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SAMPLE_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendChat(q.text)}
                    disabled={chatLoading}
                    className="px-2.5 py-1 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/40 text-xs text-slate-300 hover:text-cyan-300 transition flex items-center gap-1.5"
                  >
                    <span className="text-[9px] text-slate-500 uppercase font-mono font-bold">[{q.category}]</span>
                    <span>{q.text}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Messages Container */}
            <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 min-h-[440px] max-h-[560px] overflow-y-auto space-y-4">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-2xl rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-cyan-600/20 text-cyan-100 border border-cyan-500/30 rounded-tr-none"
                        : "bg-slate-950/80 text-slate-200 border border-slate-800 rounded-tl-none shadow-md"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1.5 text-[11px] font-mono text-slate-400">
                      {msg.sender === "user" ? (
                        <div className="flex items-center gap-1 text-cyan-400">
                          <User className="w-3.5 h-3.5" />
                          <span>You</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-indigo-400">
                          <Bot className="w-3.5 h-3.5" />
                          <span>Chronos Memory</span>
                        </div>
                      )}
                      <span>&bull;</span>
                      <span>{msg.timestamp.toLocaleTimeString()}</span>
                    </div>

                    <div className="text-slate-100">{msg.text}</div>

                    {/* Metadata & Grounding Inspection Panel */}
                    {msg.responseMeta && (
                      <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2.5 text-xs">
                        <div className="flex flex-wrap items-center gap-2">
                          {msg.responseMeta.grounded ? (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              <ShieldCheck className="w-3 h-3" />
                              VERIFIED GROUNDED
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                              <ShieldAlert className="w-3 h-3" />
                              UNGROUNDED / NO EVIDENCE
                            </span>
                          )}

                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-300 border border-slate-800">
                            Strategy: {msg.responseMeta.retrieval_method}
                          </span>

                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-300 border border-slate-800">
                            Confidence: {(msg.responseMeta.confidence * 100).toFixed(0)}%
                          </span>

                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
                            Latency: {msg.responseMeta.latency_ms.toFixed(1)}ms
                          </span>
                        </div>

                        {/* Supporting Facts Pill List */}
                        {msg.responseMeta.supporting_facts && msg.responseMeta.supporting_facts.length > 0 && (
                          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1">
                            <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold block">
                              Supporting Knowledge Graph Facts:
                            </span>
                            {msg.responseMeta.supporting_facts.map((f, i) => (
                              <div key={i} className="flex items-center justify-between text-[11px] font-mono">
                                <span className="text-slate-200">
                                  ({f.subject}) -[{f.predicate}]-&gt; ({f.object})
                                </span>
                                <span className={f.is_current ? "text-emerald-400 text-[10px]" : "text-amber-400 text-[10px]"}>
                                  {f.is_current ? "ACTIVE" : "SUPERSEDED"}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 p-3 rounded-xl bg-slate-950/60 border border-cyan-500/20 max-w-xs animate-pulse">
                  <Bot className="w-4 h-4 animate-spin" />
                  <span>Traversing temporal knowledge graph...</span>
                </div>
              )}
            </div>

            {/* Input Bar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                placeholder="Ask about current state, previous historical state, or timeline..."
                disabled={chatLoading}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition"
              />
              <button
                onClick={() => handleSendChat()}
                disabled={chatLoading || !chatInput.trim()}
                className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition flex items-center gap-1.5 shadow-md shadow-cyan-600/20 disabled:opacity-50"
              >
                <span>Ask</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Memory Ingestion Sidebar (1 col) */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span>Quick Ingest New Fact</span>
              </h3>
              <p className="text-xs text-slate-400">
                Teach the agent new facts or state updates.
              </p>
            </div>

            <form onSubmit={handleIngest} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Session ID</label>
                <input
                  type="text"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-500/50 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Message Text</label>
                <textarea
                  rows={3}
                  value={ingestText}
                  onChange={(e) => setIngestText(e.target.value)}
                  placeholder="e.g. My backend framework is FastAPI."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={ingestLoading || !ingestText.trim()}
                className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {ingestLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Extracting Facts...</span>
                  </>
                ) : (
                  <>
                    <Database className="w-3.5 h-3.5" />
                    <span>Ingest Episode</span>
                  </>
                )}
              </button>
            </form>

            {/* Quick Test Ingestion Scenarios */}
            <div className="pt-3 border-t border-slate-800/80 space-y-2">
              <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold block">
                Quick Mutation Scenarios:
              </span>
              <div className="space-y-1.5">
                {SAMPLE_EPISODES.map((ep, i) => (
                  <button
                    key={i}
                    onClick={() => handleIngest(undefined, ep.text, ep.session)}
                    disabled={ingestLoading}
                    className="w-full text-left p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/60 text-xs text-slate-300 hover:text-cyan-300 transition flex items-center justify-between group"
                  >
                    <span className="truncate pr-2">{ep.text}</span>
                    <ArrowRight className="w-3 h-3 text-slate-500 group-hover:text-cyan-400 flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: EPISODE STREAM & HISTORY */}
      {activeSubTab === "ingest_stream" && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Conversation Episodes Stream</h3>
              <p className="text-xs text-slate-400">
                Immutable conversational turns stored with timestamp, session ID, and provenance.
              </p>
            </div>
            <span className="text-xs font-mono text-cyan-400">
              {episodes.length} Episodes Persisted
            </span>
          </div>

          {episodes.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800">
              <MessageSquare className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No episodes stored yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Ingest a message or click "Seed Benchmark Scenarios" in Overview.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {episodes.map((ep) => (
                <div
                  key={ep.id}
                  className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                        {ep.speaker || "User"}
                      </span>
                      <span className="font-mono text-slate-400 text-[11px]">
                        Session: {ep.session_id}
                      </span>
                    </div>
                    <span className="font-mono text-slate-500 text-[11px]">
                      {ep.timestamp ? new Date(ep.timestamp).toLocaleString() : ep.created_at}
                    </span>
                  </div>
                  <p className="text-sm text-slate-100 font-sans">{ep.text}</p>
                  <div className="text-[10px] font-mono text-slate-500">
                    Episode ID: {ep.id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
