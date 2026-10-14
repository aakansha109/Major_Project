"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Subgraph, GraphNode, GraphEdge, Episode, Fact } from "@/types";
import { api } from "@/lib/api";
import { 
  Network, 
  Calendar, 
  Clock, 
  Filter, 
  RefreshCw, 
  Info, 
  Layers, 
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  Eye,
  X,
  FileText,
  CheckCircle2,
  GitBranch,
  Search
} from "lucide-react";

interface TemporalGraphTabProps {
  onFetchGraph: (asOf?: string) => Promise<Subgraph>;
}

const TIMELINE_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

export const TemporalGraphTab: React.FC<TemporalGraphTabProps> = ({ onFetchGraph }) => {
  const [selectedYearIndex, setSelectedYearIndex] = useState(TIMELINE_YEARS.length - 1);
  const [isLiveTime, setIsLiveTime] = useState(true);
  const [graphData, setGraphData] = useState<Subgraph>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selection states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "superseded">("all");
  const [predicateFilter, setPredicateFilter] = useState<string>("all");

  // Provenance Episode Inspection
  const [inspectedEpisode, setInspectedEpisode] = useState<{ episode: Episode; facts: Fact[] } | null>(null);
  const [loadingEpisode, setLoadingEpisode] = useState(false);

  const selectedYear = TIMELINE_YEARS[selectedYearIndex];

  const loadGraph = async (year?: number) => {
    setLoading(true);
    setError(null);
    try {
      const asOfStr = year && !isLiveTime ? `${year}-06-01T00:00:00Z` : undefined;
      const data = await onFetchGraph(asOfStr);
      setGraphData(data);
    } catch (err: any) {
      console.error("Failed to load graph:", err);
      setError(err.message || "Failed to query graph database");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLiveTime) {
      loadGraph(undefined);
    } else {
      loadGraph(selectedYear);
    }
  }, [selectedYearIndex, isLiveTime]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value);
    setSelectedYearIndex(idx);
    setIsLiveTime(false);
  };

  // Distinct predicates for dropdown filter
  const distinctPredicates = useMemo(() => {
    const set = new Set<string>();
    graphData.edges.forEach((e) => set.add(e.label));
    return Array.from(set).sort();
  }, [graphData.edges]);

  // Filtered edges
  const filteredEdges = useMemo(() => {
    return graphData.edges.filter((e) => {
      // Status filter
      if (statusFilter === "active" && !e.is_current) return false;
      if (statusFilter === "superseded" && e.is_current) return false;
      // Predicate filter
      if (predicateFilter !== "all" && e.label !== predicateFilter) return false;
      return true;
    });
  }, [graphData.edges, statusFilter, predicateFilter]);

  // Distinct nodes that are referenced by filtered edges (or all if no filter)
  const activeNodeIds = useMemo(() => {
    const set = new Set<string>();
    filteredEdges.forEach((e) => {
      set.add(e.source);
      set.add(e.target);
    });
    return set;
  }, [filteredEdges]);

  const displayNodes = useMemo(() => {
    if (filteredEdges.length === 0 && graphData.edges.length > 0) {
      return [];
    }
    return graphData.nodes.filter((n) => activeNodeIds.has(n.id) || graphData.edges.length === 0);
  }, [graphData.nodes, activeNodeIds, filteredEdges.length, graphData.edges.length]);

  // Layout node positions in an aesthetic circular arrangement
  const width = 760;
  const height = 480;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.36;

  const nodePositions = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    const n = displayNodes.length;
    displayNodes.forEach((node, i) => {
      const angle = (i / Math.max(1, n)) * 2 * Math.PI - Math.PI / 2;
      pos[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
    return pos;
  }, [displayNodes, centerX, centerY, radius]);

  // Inspect source episode
  const handleInspectEpisode = async (episodeId?: string | null) => {
    if (!episodeId) return;
    setLoadingEpisode(true);
    try {
      const res = await api.getEpisodeById(episodeId);
      setInspectedEpisode(res);
    } catch (err: any) {
      console.error("Failed to load episode details:", err);
    } finally {
      setLoadingEpisode(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Controls: Time Scrubber & Filtering Bar */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Network className="w-5 h-5 text-cyan-400" />
              <span>Bi-Temporal Knowledge Graph Navigator</span>
            </h2>
            <p className="text-xs text-slate-400">
              Interactive visualization with active and superseded relationship differentiation, status filtering, and provenance audit.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => {
                setIsLiveTime(true);
                setSelectedYearIndex(TIMELINE_YEARS.length - 1);
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                isLiveTime 
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/10" 
                  : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              Current State (Live)
            </button>
            <button
              onClick={() => loadGraph(isLiveTime ? undefined : selectedYear)}
              disabled={loading}
              className="p-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-300 transition"
              title="Refresh graph"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Time Slider */}
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Point-in-Time Scrubbing:</span>
            </span>
            <span className="font-mono text-cyan-300 font-bold">
              {isLiveTime ? "Present (Open Validity)" : `Historical Snapshot (${selectedYear})`}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={TIMELINE_YEARS.length - 1}
            value={selectedYearIndex}
            onChange={handleSliderChange}
            className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
          <div className="flex justify-between text-[11px] font-mono text-slate-500 px-1">
            {TIMELINE_YEARS.map((y, idx) => (
              <span
                key={y}
                className={`cursor-pointer transition ${idx === selectedYearIndex && !isLiveTime ? "text-cyan-400 font-bold" : "hover:text-slate-300"}`}
                onClick={() => {
                  setSelectedYearIndex(idx);
                  setIsLiveTime(false);
                }}
              >
                {y}
              </span>
            ))}
          </div>
        </div>

        {/* Graph Filters Bar */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>Filter Status:</span>
            </span>
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setStatusFilter("all")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                  statusFilter === "all"
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All ({graphData.edges.length})
              </button>
              <button
                onClick={() => setStatusFilter("active")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                  statusFilter === "active"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    : "text-slate-400 hover:text-emerald-300"
                }`}
              >
                Active Only ({graphData.edges.filter(e => e.is_current).length})
              </button>
              <button
                onClick={() => setStatusFilter("superseded")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                  statusFilter === "superseded"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    : "text-slate-400 hover:text-amber-300"
                }`}
              >
                Superseded Only ({graphData.edges.filter(e => !e.is_current).length})
              </button>
            </div>
          </div>

          {/* Relationship Type / Predicate Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Relationship:</span>
            <select
              value={predicateFilter}
              onChange={(e) => setPredicateFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-500/50 focus:outline-none"
            >
              <option value="all">All Predicates ({distinctPredicates.length})</option>
              {distinctPredicates.map((pred) => (
                <option key={pred} value={pred}>
                  {pred}
                </option>
              ))}
            </select>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-400 inline-block shadow-sm shadow-emerald-400/50" />
              <span className="text-emerald-400 font-semibold">Active Valid Fact</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-b border-dashed border-amber-400 inline-block" />
              <span className="text-amber-400 font-semibold">Superseded / Closed</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Graph Viewport & Inspector Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SVG Canvas Area (8 cols) */}
        <div className="lg:col-span-8 p-4 rounded-2xl bg-slate-900/60 border border-slate-800 relative min-h-[500px] flex items-center justify-center overflow-hidden">
          {loading && (
            <div className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm z-20 flex items-center justify-center">
              <div className="flex items-center gap-2 text-sm text-cyan-400 font-mono">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Computing temporal subgraph...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute top-4 left-4 right-4 p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-xs text-rose-300 z-10 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {displayNodes.length === 0 ? (
            <div className="text-center py-16 space-y-3">
              <Network className="w-12 h-12 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-300 font-medium">No knowledge graph elements match current filter.</p>
              <p className="text-xs text-slate-500">
                Adjust the status/predicate filters, or seed benchmark scenarios in Overview.
              </p>
            </div>
          ) : (
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full h-full max-h-[540px] select-none"
            >
              <defs>
                {/* Emerald Active Arrow Marker */}
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="24"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
                </marker>
                {/* Amber Superseded Arrow Marker */}
                <marker
                  id="arrow-superseded"
                  viewBox="0 0 10 10"
                  refX="24"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>

              {/* Graph Edges */}
              {filteredEdges.map((edge, i) => {
                const sPos = nodePositions[edge.source];
                const tPos = nodePositions[edge.target];
                if (!sPos || !tPos) return null;

                const midX = (sPos.x + tPos.x) / 2;
                const midY = (sPos.y + tPos.y) / 2;
                const isSelected = selectedEdge && selectedEdge.source === edge.source && selectedEdge.target === edge.target && selectedEdge.label === edge.label;
                const isCurrent = edge.is_current;

                return (
                  <g 
                    key={`edge-${i}`} 
                    className="cursor-pointer group"
                    onClick={() => {
                      setSelectedEdge(edge);
                      setSelectedNode(null);
                    }}
                  >
                    {/* Edge Line */}
                    <line
                      x1={sPos.x}
                      y1={sPos.y}
                      x2={tPos.x}
                      y2={tPos.y}
                      stroke={
                        isSelected 
                          ? "#38bdf8" 
                          : isCurrent 
                            ? "#10b981" 
                            : "#f59e0b"
                      }
                      strokeWidth={isSelected ? 3.5 : isCurrent ? 2.2 : 1.6}
                      strokeDasharray={isCurrent ? "none" : "6 4"}
                      opacity={isSelected ? 1 : isCurrent ? 0.9 : 0.65}
                      markerEnd={isCurrent ? "url(#arrow-active)" : "url(#arrow-superseded)"}
                      className="transition-all duration-200"
                    />

                    {/* Edge Clickable Predicate Badge */}
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x="-40"
                        y="-11"
                        width="80"
                        height="22"
                        rx="5"
                        fill="#020617"
                        stroke={
                          isSelected 
                            ? "#38bdf8" 
                            : isCurrent 
                              ? "#10b981" 
                              : "#f59e0b"
                        }
                        strokeWidth={isSelected ? 2 : 1}
                        opacity="0.95"
                        className="transition-all group-hover:scale-105"
                      />
                      <text
                        x="0"
                        y="3"
                        textAnchor="middle"
                        fill={isCurrent ? "#6ee7b7" : "#fcd34d"}
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="600"
                      >
                        {edge.label}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Graph Nodes */}
              {displayNodes.map((node) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;

                const isSelected = selectedNode?.id === node.id;
                const isEdgeConnected = selectedEdge && (selectedEdge.source === node.id || selectedEdge.target === node.id);

                return (
                  <g
                    key={`node-${node.id}`}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    className="cursor-pointer group"
                    onClick={() => {
                      setSelectedNode(node);
                      setSelectedEdge(null);
                    }}
                  >
                    <circle
                      r={isSelected ? 24 : isEdgeConnected ? 21 : 18}
                      fill="#0f172a"
                      stroke={isSelected ? "#38bdf8" : isEdgeConnected ? "#06b6d4" : "#475569"}
                      strokeWidth={isSelected || isEdgeConnected ? 3 : 1.8}
                      className="transition-all duration-200 group-hover:stroke-cyan-400 group-hover:r-[22px]"
                    />
                    <text
                      y="4"
                      textAnchor="middle"
                      fill="#f8fafc"
                      fontSize="10"
                      fontWeight="bold"
                      className="select-none pointer-events-none"
                    >
                      {node.label.length > 8 ? `${node.label.substring(0, 7)}…` : node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          <div className="absolute bottom-3 left-4 text-[10px] font-mono text-slate-500">
            Click any edge or node to view validity intervals, provenance, and episode evidence.
          </div>
        </div>

        {/* Detail Inspector Panel (4 cols) */}
        <div className="lg:col-span-4 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>Inspector Panel</span>
            </h3>
            {(selectedEdge || selectedNode) && (
              <button
                onClick={() => {
                  setSelectedEdge(null);
                  setSelectedNode(null);
                }}
                className="text-xs text-slate-400 hover:text-slate-200 p-1"
                title="Clear selection"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* INSPECTOR STATE 1: EDGE SELECTED */}
          {selectedEdge ? (
            <div className="space-y-4 text-xs">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
                    Selected Relationship
                  </span>
                  {selectedEdge.is_current ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      ACTIVE FACT
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                      SUPERSEDED
                    </span>
                  )}
                </div>
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-sm text-cyan-300">
                  <span className="text-white font-bold">{selectedEdge.source}</span>
                  <span className="text-slate-400 mx-2">&mdash;[{selectedEdge.label}]&rarr;</span>
                  <span className="text-white font-bold">{selectedEdge.target}</span>
                </div>
              </div>

              {/* Temporal Validity Details */}
              <div className="space-y-2 p-3 rounded-xl bg-slate-950/50 border border-slate-800">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block">
                  Temporal Validity Interval:
                </span>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Valid From:</span>
                  <span className="font-mono text-slate-200">
                    {selectedEdge.valid_from ? selectedEdge.valid_from.split("T")[0] : "Recorded inception"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Valid To:</span>
                  <span className="font-mono">
                    {selectedEdge.valid_to ? (
                      <span className="text-amber-400 font-semibold">{selectedEdge.valid_to.split("T")[0]}</span>
                    ) : (
                      <span className="text-emerald-400 font-semibold">Open-ended (Current)</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Extractor Method:</span>
                  <span className="font-mono text-indigo-300 uppercase">
                    {selectedEdge.source_type || "rule"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Confidence:</span>
                  <span className="font-mono text-slate-200">
                    {(selectedEdge.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Provenance: Source Episode Link */}
              <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block">
                  Provenance Source Episode:
                </span>
                <div className="font-mono text-[11px] text-slate-300 break-all">
                  {selectedEdge.source_episode_id || selectedEdge.fact_id || "Direct ingestion episode"}
                </div>
                {selectedEdge.source_episode_id && (
                  <button
                    onClick={() => handleInspectEpisode(selectedEdge.source_episode_id)}
                    disabled={loadingEpisode}
                    className="w-full mt-2 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800/60 text-xs font-semibold text-cyan-300 transition flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{loadingEpisode ? "Loading Turn..." : "Inspect Source Episode"}</span>
                  </button>
                )}
              </div>
            </div>
          ) : selectedNode ? (
            /* INSPECTOR STATE 2: NODE SELECTED */
            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block mb-1">
                  Selected Entity Node
                </span>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-sm font-bold text-white font-mono">
                  {selectedNode.label}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block">
                  Connected Temporal Edges:
                </span>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {graphData.edges
                    .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                    .map((edge, i) => (
                      <div
                        key={i}
                        onClick={() => setSelectedEdge(edge)}
                        className="p-2.5 rounded-xl bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800/80 cursor-pointer transition space-y-1"
                      >
                        <div className="flex items-center justify-between font-mono text-[11px]">
                          <span className="text-slate-200">
                            {edge.source === selectedNode.id ? `&rarr; ${edge.target}` : `&larr; ${edge.source}`}
                          </span>
                          <span className={edge.is_current ? "text-emerald-400 text-[10px] font-bold" : "text-amber-400 text-[10px] font-bold"}>
                            {edge.is_current ? "ACTIVE" : "SUPERSEDED"}
                          </span>
                        </div>
                        <div className="text-[10px] text-cyan-400 font-mono">
                          [{edge.label}] &bull; {edge.valid_from?.split("T")[0]} &rarr; {edge.valid_to ? edge.valid_to.split("T")[0] : "Now"}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            /* INSPECTOR STATE 3: NOTHING SELECTED */
            <div className="py-12 text-center space-y-2 text-slate-400">
              <Info className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs">Select any edge or entity node in the graph viewport.</p>
              <p className="text-[11px] text-slate-500">
                View temporal validity intervals, closed dates, and conversation provenance.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Episode Provenance Modal */}
      {inspectedEpisode && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-xl w-full p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Source Episode Provenance</h3>
              </div>
              <button
                onClick={() => setInspectedEpisode(null)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                  <span>Speaker: <strong className="text-slate-200">{inspectedEpisode.episode.speaker}</strong></span>
                  <span>Session: <strong className="text-slate-200">{inspectedEpisode.episode.session_id}</strong></span>
                </div>
                <div className="text-sm text-slate-100 font-sans mt-1">
                  "{inspectedEpisode.episode.text}"
                </div>
                <div className="text-[10px] font-mono text-slate-500">
                  Recorded: {new Date(inspectedEpisode.episode.timestamp).toLocaleString()}
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold block mb-1">
                  Facts Extracted From This Turn ({inspectedEpisode.facts.length}):
                </span>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {inspectedEpisode.facts.map((f) => (
                    <div key={f.id} className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 font-mono text-[11px] flex items-center justify-between">
                      <span className="text-slate-200">({f.subject}) -[{f.predicate}]-&gt; ({f.object})</span>
                      <span className={f.is_current ? "text-emerald-400 text-[10px]" : "text-amber-400 text-[10px]"}>
                        {f.is_current ? "ACTIVE" : "SUPERSEDED"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={() => setInspectedEpisode(null)}
              className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition"
            >
              Close Provenance Audit
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
