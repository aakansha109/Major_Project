import {
  HealthResponse,
  IngestResponse,
  Fact,
  Episode,
  Subgraph,
  RetrievalResult,
  InferenceResponse,
  EvaluationResult,
  StrategyComparisonResult,
  ChatResponse,
  MemoryHistoryResponse
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}/api${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {})
      }
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`API Error [${res.status}]: ${errText || res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Request to ${url} failed:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),

  ingestEpisode: (payload: { session_id?: string; speaker?: string; text: string; timestamp?: string }) =>
    request<IngestResponse>("/episodes", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  getEpisodes: (sessionId?: string, limit = 50) =>
    request<Episode[]>(`/episodes?${sessionId ? `session_id=${sessionId}&` : ""}limit=${limit}`),

  getEpisodeById: (episodeId: string) =>
    request<{ episode: Episode; facts: Fact[]; fact_count: number }>(`/episodes/${episodeId}`),

  chat: (payload: { message: string; session_id?: string; as_of?: string }) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  getMemoryFacts: (params?: { as_of?: string; subject?: string; predicate?: string; only_current?: boolean; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.as_of) q.set("as_of", params.as_of);
    if (params?.subject) q.set("subject", params.subject);
    if (params?.predicate) q.set("predicate", params.predicate);
    if (params?.only_current !== undefined) q.set("only_current", params.only_current ? "true" : "false");
    if (params?.limit) q.set("limit", params.limit.toString());
    const queryStr = q.toString();
    return request<Fact[]>(`/memory/facts${queryStr ? `?${queryStr}` : ""}`);
  },

  getMemoryHistory: (params?: { subject?: string; predicate?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.subject) q.set("subject", params.subject);
    if (params?.predicate) q.set("predicate", params.predicate);
    if (params?.limit) q.set("limit", params.limit.toString());
    const queryStr = q.toString();
    return request<MemoryHistoryResponse>(`/memory/history${queryStr ? `?${queryStr}` : ""}`);
  },

  getFacts: (params?: { as_of?: string; subject?: string; predicate?: string; only_current?: boolean; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.as_of) q.set("as_of", params.as_of);
    if (params?.subject) q.set("subject", params.subject);
    if (params?.predicate) q.set("predicate", params.predicate);
    if (params?.only_current) q.set("only_current", "true");
    if (params?.limit) q.set("limit", params.limit.toString());
    const queryStr = q.toString();
    return request<Fact[]>(`/facts${queryStr ? `?${queryStr}` : ""}`);
  },

  getGraph: (asOf?: string, limit = 250) => {
    const q = new URLSearchParams();
    if (asOf) q.set("as_of", asOf);
    if (limit) q.set("limit", limit.toString());
    const queryStr = q.toString();
    return request<Subgraph>(`/graph${queryStr ? `?${queryStr}` : ""}`);
  },

  retrieve: (payload: { query: string; as_of?: string | null; session_id?: string; top_k?: number; include_neighborhood?: boolean }) =>
    request<RetrievalResult>("/retrieval", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  infer: (payload: { query: string; as_of?: string | null; session_id?: string }) =>
    request<InferenceResponse>("/inference", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  runEvaluation: () =>
    request<EvaluationResult>("/evaluation/run", {
      method: "POST"
    }),

  getLatestEvaluation: () =>
    request<EvaluationResult | { status: string; message: string }>("/evaluation/latest"),

  compareStrategies: () =>
    request<StrategyComparisonResult>("/evaluation/compare-strategies", {
      method: "POST"
    }),

  getLatestComparison: () =>
    request<StrategyComparisonResult | { status: string; message: string }>("/evaluation/comparison/latest"),

  seedSampleData: () =>
    request<{ status: string; message: string; episodes_seeded: number; database_metrics: any }>("/seed", {
      method: "POST"
    }),

  resetDatabase: () =>
    request<{ status: string; message: string }>("/reset", {
      method: "POST"
    })
};
