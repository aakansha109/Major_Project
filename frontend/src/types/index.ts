export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  uptime_seconds: number;
  environment: string;
  llm_fallback_enabled: boolean;
  llm_api_configured: boolean;
  llm_model: string;
  storage: {
    graph_backend: string;
    neo4j_connected: boolean;
    neo4j_uri: string;
    metrics: {
      episode_count: number;
      fact_count: number;
      active_facts_count?: number;
      superseded_facts_count?: number;
      extraction_calls_count?: number;
      entity_count: number;
      rule_extractions_count?: number;
      llm_extractions_count?: number;
      total_tokens_used: number;
      total_cost_usd: number;
    };
  };
}

export interface Fact {
  id: string;
  subject: string;
  predicate: string;
  object: string;
  valid_from: string;
  valid_to: string | null;
  tx_time: string;
  is_current: boolean;
  confidence: number;
  source: string;
  rule_name?: string | null;
  tokens_used: number;
  estimated_cost_usd: number;
  episode_id?: string | null;
  raw_text?: string | null;
  superseded_by?: string | null;
  supersedes_fact_id?: string | null;
}

export interface Episode {
  id: string;
  session_id: string;
  speaker: string;
  text: string;
  timestamp: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface IngestResponse {
  episode: Episode;
  extracted_facts: Fact[];
  invalidated_facts: Fact[];
  telemetry: {
    strategy: string;
    fact_count: number;
    tier1_latency_ms: number;
    tier2_latency_ms: number;
    total_latency_ms: number;
    tokens_consumed: number;
    cost_usd: number;
    contradictions_resolved: number;
    facts_stored: number;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  label: string;
  valid_from?: string | null;
  valid_to?: string | null;
  is_current: boolean;
  status?: string;
  confidence: number;
  source_type: string;
  source_episode_id?: string | null;
  fact_id?: string | null;
}

export interface Subgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RetrievalResult {
  query: string;
  as_of?: string | null;
  matched_facts: Fact[];
  matched_episodes: Episode[];
  subgraph: Subgraph;
  latency_ms: number;
  retrieval_strategy: string;
  stats: Record<string, any>;
}

export interface InferenceResponse {
  query: string;
  as_of: string;
  answer: string;
  reasoning_chain: string[];
  supporting_facts: Fact[];
  superseded_facts: Fact[];
  temporal_span_analyzed: Record<string, any>;
  confidence: number;
  latency_ms: number;
}

export interface ChatResponse {
  query: string;
  answer: string;
  grounded: boolean;
  evidence_status: string;
  supporting_fact_ids: string[];
  source_episode_ids: string[];
  temporal_validity: Record<string, any>;
  retrieval_method: string;
  confidence: number;
  supporting_facts: Fact[];
  supporting_episodes: Episode[];
  reasoning_chain: string[];
  latency_ms: number;
}

export interface MemoryHistoryItem {
  fact_id: string;
  subject: string;
  predicate: string;
  object: string;
  valid_from: string;
  valid_to: string | null;
  status: string;
  is_current: boolean;
  source_episode_id?: string | null;
  superseded_by?: string | null;
  confidence: number;
  created_at: string;
  extraction_method: string;
}

export interface MemoryHistoryResponse {
  subject: string | null;
  predicate: string | null;
  total_events: number;
  transitions_count: number;
  timeline: MemoryHistoryItem[];
}

export interface MetricSummary {
  total_test_cases: number;
  passed_cases: number;
  accuracy_score: number;
  precision: number;
  recall: number;
  f1_score: number;
}

export interface CostComparison {
  chronos_tokens_total: number;
  chronos_cost_usd: number;
  pure_llm_tokens_total: number;
  pure_llm_cost_usd: number;
  token_savings_percent: number;
  cost_reduction_percent: number;
  rule_extraction_ratio: number;
  llm_fallback_ratio: number;
}

export interface LatencyBreakdown {
  mean_rule_extraction_ms: number;
  mean_llm_extraction_ms: number;
  mean_graph_write_ms: number;
  mean_retrieval_ms: number;
  mean_inference_ms: number;
}

export interface EvaluationResult {
  run_id: string;
  timestamp: string;
  sample_size: number;
  extraction_metrics: MetricSummary;
  contradiction_metrics: MetricSummary;
  retrieval_metrics: MetricSummary;
  cost_comparison: CostComparison;
  latency_breakdown: LatencyBreakdown;
  detailed_results: Array<{
    case_id: string;
    input: string;
    matched: boolean;
    strategy: string;
    latency_ms: number;
    tokens: number;
    cost_usd: number;
    invalidated_count: number;
  }>;
}

export interface StrategyMetrics {
  strategy_name: string;
  sample_size: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  tokens_are_measured: boolean;
  mean_latency_ms: number;
  total_latency_ms: number;
  total_cost_usd: number;
  cost_pricing_basis: string;
  fallback_call_rate: number;
  rule_extraction_rate: number;
  decision_counts: Record<string, number>;
}

export interface StrategyComparisonResult {
  dataset_size: number;
  strategy_a: StrategyMetrics;
  strategy_b: StrategyMetrics;
  token_reduction_percent: number;
  cost_reduction_percent: number;
  latency_speedup_factor: number;
  hypothesis_tested: string;
  hypothesis_supported: boolean;
  hypothesis_summary: string;
  limitations: string[];
  detailed_episodes: Array<{
    case_id: string;
    input_text: string;
    expected: any;
    strategy_a: {
      matched: boolean;
      extracted_count: number;
      confidence: number;
      latency_ms: number;
      tokens: number;
      cost_usd: number;
      decision_reason: string;
    };
    strategy_b: {
      matched: boolean;
      extracted_count: number;
      confidence: number;
      latency_ms: number;
      tokens: number;
      cost_usd: number;
      method: string;
      fallback_triggered: boolean;
      decision_reason: string;
    };
  }>;
}
