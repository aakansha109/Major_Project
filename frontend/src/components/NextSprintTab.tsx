"use client";

import React, { useState } from "react";
import { 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  GitBranch, 
  Layers, 
  Cpu, 
  Database, 
  Sparkles, 
  FileText, 
  Terminal, 
  CheckSquare, 
  Square, 
  Rocket, 
  Award,
  BookOpen
} from "lucide-react";

interface TaskItem {
  id: string;
  title: string;
  category: string;
  status: "completed" | "in_progress" | "planned";
  priority: "High" | "Medium" | "Crucial";
  description: string;
  deliverable: string;
}

const SPRINTS = [
  {
    id: "sprint-1",
    number: "Sprint 1",
    title: "Bi-Temporal Knowledge Graph & Invalidation Engine",
    status: "completed",
    completion: "100%",
    dates: "Sprint 1 (Milestone 1)",
    tasks: [
      {
        id: "s1-1",
        title: "Bi-temporal Fact Schema Design",
        category: "Storage",
        status: "completed" as const,
        priority: "Crucial" as const,
        description: "Implemented subject, predicate, object, valid_from, valid_to, is_current, confidence, and source episode provenance.",
        deliverable: "app/models/fact.py, Neo4j schema constraints"
      },
      {
        id: "s1-2",
        title: "Deterministic Invalidation & Contradiction Resolution",
        category: "Graph Engine",
        status: "completed" as const,
        priority: "Crucial" as const,
        description: "Closed historical validity intervals when conflicting active facts are ingested; prevents duplicate active facts.",
        deliverable: "app/db/sqlite_store.py, app/db/neo4j.py"
      },
      {
        id: "s1-3",
        title: "Resilient Dual-Engine Persistence",
        category: "Storage",
        status: "completed" as const,
        priority: "High" as const,
        description: "Integrated Neo4j with automated Docker Compose support, plus zero-dependency resilient SQLite mirroring.",
        deliverable: "UnifiedGraphStore with automatic failover"
      }
    ]
  },
  {
    id: "sprint-2",
    number: "Sprint 2",
    title: "Confidence-Gated Hybrid Fact Extraction",
    status: "completed",
    completion: "100%",
    dates: "Sprint 2 (Milestone 2)",
    tasks: [
      {
        id: "s2-1",
        title: "Deterministic Rule Extraction Tier (Tier 1)",
        category: "Extraction",
        status: "completed" as const,
        priority: "Crucial" as const,
        description: "Built regex and pattern extraction rules for career, relocation, hardware, and framework changes in <2ms with zero token cost.",
        deliverable: "app/services/extractor/rule_extractor.py"
      },
      {
        id: "s2-2",
        title: "Confidence Gate & Strict Schema LLM Fallback (Tier 2)",
        category: "Extraction",
        status: "completed" as const,
        priority: "High" as const,
        description: "Engineered OpenAI-compatible LLM fallback with strict Pydantic parsing and validation error guards.",
        deliverable: "app/services/extractor/llm_extractor.py"
      },
      {
        id: "s2-3",
        title: "Empirical Token & Monetary Cost Accounting",
        category: "Telemetry",
        status: "completed" as const,
        priority: "High" as const,
        description: "Accurately measured prompt/completion tokens with measured vs estimated flags and zero fabricated metrics.",
        deliverable: "ExtractionResult telemetry & cost tracker"
      }
    ]
  },
  {
    id: "sprint-3",
    number: "Sprint 3",
    title: "Conversational Retrieval & Temporal Reasoning",
    status: "completed",
    completion: "100%",
    dates: "Sprint 3 (Milestone 3)",
    tasks: [
      {
        id: "s3-1",
        title: "Temporal Reasoning Engine (Current vs Historical vs Evolution)",
        category: "Retrieval",
        status: "completed" as const,
        priority: "Crucial" as const,
        description: "Implemented intent detection ensuring historical queries never return latest facts, with full timeline reconstruction.",
        deliverable: "app/services/chat_service.py"
      },
      {
        id: "s3-2",
        title: "Multi-Strategy Endpoints & Graph Traversal",
        category: "API",
        status: "completed" as const,
        priority: "High" as const,
        description: "Added POST /api/chat, GET /api/memory/facts, GET /api/memory/history, and GET /api/episodes/{episode_id}.",
        deliverable: "FastAPI REST API routes with OpenAPI documentation"
      },
      {
        id: "s3-3",
        title: "Automated Pytest Research Benchmark",
        category: "Evaluation",
        status: "completed" as const,
        priority: "High" as const,
        description: "Engineered 34 unit & integration tests validating temporal consistency, strategy comparisons, and chat groundings.",
        deliverable: "tests/test_conversational_retrieval.py (100% pass)"
      }
    ]
  },
  {
    id: "sprint-4",
    number: "Sprint 4",
    title: "Full-Stack Research Lab & Graph Inspector (Current)",
    status: "completed",
    completion: "100%",
    dates: "Sprint 4 (Current Sprint)",
    tasks: [
      {
        id: "s4-1",
        title: "Real API-Backed Dashboard & Metrics Cards",
        category: "Frontend",
        status: "completed" as const,
        priority: "High" as const,
        description: "Connected real counts of entities, active facts, superseded facts, and extraction calls; removed all hardcoded mock metrics.",
        deliverable: "OverviewTab.tsx with live API telemetry"
      },
      {
        id: "s4-2",
        title: "Interactive Knowledge Graph with Active vs Superseded Differentiation",
        category: "Frontend",
        status: "completed" as const,
        priority: "Crucial" as const,
        description: "Rendered SVG graph differentiating active (emerald) vs superseded (amber dashed) edges, with edge inspector and status filters.",
        deliverable: "TemporalGraphTab.tsx with edge inspector"
      },
      {
        id: "s4-3",
        title: "Conversational QA & Provenance Audit Interface",
        category: "Frontend",
        status: "completed" as const,
        priority: "High" as const,
        description: "Enabled sending messages, viewing conversation history, querying temporal facts, and inspecting source episode evidence.",
        deliverable: "ConversationLabTab.tsx with grounding badges"
      }
    ]
  },
  {
    id: "sprint-5",
    number: "Sprint 5",
    title: "Next Sprint: Multi-Modal Memory & Production Hardening",
    status: "planned",
    completion: "0%",
    dates: "Upcoming Sprint",
    tasks: [
      {
        id: "s5-1",
        title: "Multi-Modal Episode Ingestion (Voice & Visual Context)",
        category: "Multimodal",
        status: "planned" as const,
        priority: "High" as const,
        description: "Extend episode ingestion to accept audio transcripts with speaker diarization and image scene descriptions.",
        deliverable: "Audio/Image ingestion adapter & vector embedding"
      },
      {
        id: "s5-2",
        title: "Cross-Session Coreference Resolution Engine",
        category: "NLP",
        status: "planned" as const,
        priority: "High" as const,
        description: "Resolve anaphoric pronouns ('it', 'that company', 'there') across multi-session dialogues before graph insertion.",
        deliverable: "Neural coreference pipeline in extractor tier"
      },
      {
        id: "s5-3",
        title: "Ebbinghaus Forgetting & Memory Consolidation",
        category: "Graph Engine",
        status: "planned" as const,
        priority: "Medium" as const,
        description: "Implement human-like memory consolidation algorithms that summarize obsolete low-importance facts into higher-level abstractions.",
        deliverable: "Background consolidation worker daemon"
      },
      {
        id: "s5-4",
        title: "Distributed Neo4j Enterprise Cluster Sharding",
        category: "Infrastructure",
        status: "planned" as const,
        priority: "Medium" as const,
        description: "Shard memory graphs across multiple Neo4j causal cluster nodes partitioned by user/agent organization ID.",
        deliverable: "Kubernetes Helm charts & sharding proxy"
      }
    ]
  }
];

export const NextSprintTab: React.FC = () => {
  const [selectedSprint, setSelectedSprint] = useState<string>("sprint-5");
  const currentSprintData = SPRINTS.find((s) => s.id === selectedSprint) || SPRINTS[4];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              Project Roadmap
            </span>
            <span className="text-xs text-slate-400 font-mono">
              B.Tech Major Project (AI & ML) Milestone Tracker
            </span>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Core Research Milestones 1–4 Completed</span>
          </span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Chronos Memory: Engineering Sprint Board
        </h2>
        <p className="text-xs text-slate-400 max-w-3xl">
          Comprehensive development trajectory tracking completed architectural milestones (bi-temporal graph, confidence-gated extraction, conversational retrieval, interactive UI) and planned sprint deliverables.
        </p>
      </div>

      {/* Sprints Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {SPRINTS.map((sprint) => {
          const isSelected = selectedSprint === sprint.id;
          const isCompleted = sprint.status === "completed";
          const isPlanned = sprint.status === "planned";

          return (
            <button
              key={sprint.id}
              onClick={() => setSelectedSprint(sprint.id)}
              className={`p-4 rounded-xl border text-left transition-all relative overflow-hidden ${
                isSelected
                  ? "bg-slate-900 border-cyan-500 shadow-md shadow-cyan-500/10 scale-[1.02]"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-bold uppercase text-slate-400">
                  {sprint.number}
                </span>
                {isCompleted ? (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-400">
                    DONE
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-indigo-500/20 text-indigo-300">
                    PLANNED
                  </span>
                )}
              </div>

              <h4 className="text-xs font-bold text-slate-200 line-clamp-2 h-8 leading-snug">
                {sprint.title}
              </h4>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Progress:</span>
                <span className={isCompleted ? "text-emerald-400 font-bold" : "text-cyan-400"}>
                  {sprint.completion}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Sprint Details Board */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase">
                {currentSprintData.number}
              </span>
              <span className="text-slate-600">&bull;</span>
              <span className="text-xs font-mono text-slate-400">
                {currentSprintData.dates}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">
              {currentSprintData.title}
            </h3>
          </div>

          <span className={`px-3 py-1 rounded-xl text-xs font-mono font-semibold self-start md:self-auto ${
            currentSprintData.status === "completed"
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
              : "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
          }`}>
            Status: {currentSprintData.status.toUpperCase()} ({currentSprintData.completion})
          </span>
        </div>

        {/* Tasks List for Selected Sprint */}
        <div className="space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-bold">
            Sprint Work Items & Deliverables ({currentSprintData.tasks.length}):
          </h4>

          <div className="space-y-2.5">
            {currentSprintData.tasks.map((task) => {
              const isTaskDone = task.status === "completed";

              return (
                <div
                  key={task.id}
                  className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      {isTaskDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <Clock className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      )}
                      <span className="text-sm font-semibold text-slate-100">
                        {task.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-800 text-slate-300">
                        {task.category}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        task.priority === "Crucial" 
                          ? "bg-rose-500/15 text-rose-300 border border-rose-500/30" 
                          : "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                      }`}>
                        {task.priority}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 pl-6 leading-relaxed">
                    {task.description}
                  </p>

                  <div className="pl-6 pt-1 text-[11px] font-mono text-cyan-400/90 flex items-center gap-1.5">
                    <span className="text-slate-500">Deliverable:</span>
                    <span>{task.deliverable}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Academic / Major Project Deliverables Card */}
        <div className="p-5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-white font-bold flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-cyan-400" />
            <span>Academic B.Tech Major Project Deliverables Checklist</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Full-Stack Research Platform (FastAPI + Next.js + Neo4j)</span>
            </div>
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Bi-temporal Graph Invalidation Engine with Provenance</span>
            </div>
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Confidence-Gated Hybrid Extractor with Token Measurement</span>
            </div>
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Empirical Benchmark comparing Strategy A vs B</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
