# Chronos Memory: Cost-Efficient Temporal Knowledge Graph Memory for Conversational AI Agents

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![Neo4j](https://img.shields.io/badge/Database-Neo4j%205-008CC1?style=flat-square&logo=neo4j)](https://neo4j.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Styling-TailwindCSS%203-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com)

**B.Tech CSE (AI & ML) Major Project**  
*A Research-Grade, Bi-temporal Knowledge Graph Memory Engine for Conversational AI Agents featuring Cost-Efficient Deterministic Extraction, Anaphora Resolution, Temporal Contradiction Resolution, Point-in-Time Retrieval, and Empirical Benchmarking.*

---

## 1. Problem Statement & Motivation

Existing conversational AI agents suffer from critical architectural deficiencies:
1. **Temporal Incoherence in Flat Contexts / RAG**: Naive vector RAG retrieves text chunks without temporal reasoning (e.g., retrieving both *"Alice lived in Seattle in 2020"* and *"Alice moved to London in 2023"* simultaneously, causing conversational hallucination when asked *"Where does Alice live now?"*).
2. **Prohibitive Token Costs of Naive LLM Extraction**: Extracting memory facts using an LLM on every conversation turn costs approximately **$0.02 – $0.15 per turn** in prompt and completion tokens, creating severe economic bottlenecks for real-time continuous deployment.
3. **Absence of Provenance & Bi-temporal Auditability**: Inability to time-travel (evaluating the memory state at any specific historical timestamp $t_s$) or audit when a fact was asserted vs. when it was effectively valid.

---

## 2. Chronos Memory Architecture

Chronos Memory introduces a multi-tiered, cost-efficient temporal graph architecture:

```
[ Conversation Episode Ingestion (User / Assistant) ]
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: Deterministic Rule Engine + Pronoun Coreference     │  ──► 0 Tokens ($0.00), <2ms Latency
│ (Regex, Lexical Anchors, Relative Time Parsing)             │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Triggered if confidence < threshold τ)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 2: Real OpenAI-Compatible LLM Fallback (GPT-4o-mini)   │  ──► Exact Token Accounting ($ / 1M tok)
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Temporal Contradiction Resolution Engine                   │
│ - Detects single-valued functional predicate conflicts       │
│ - Updates validity: valid_to = new_valid_from, is_current=0 │
│ - Establishes [SUPERSEDES] relation & audit provenance       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Unified Temporal Knowledge Graph Store                      │
│ - Primary: Neo4j Cypher Graph Engine (Dockerized)           │
│ - Secondary: Persistent SQLite Resilient Local Mirror        │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        ▼                                             ▼
┌──────────────────────────────┐        ┌─────────────────────────────┐
│ Point-in-Time Semantic       │        │ Temporal Task Inference     │
│ Vector & Subgraph Retrieval  │        │ Engine (Reasoning Chains)   │
└──────────────────────────────┘        └─────────────────────────────┘
```

### Key Capabilities
- **Two-Tier Cost-Efficient Extraction**: Handles ~75–85% of everyday conversational declarations at **zero token cost** ($0.00), dropping to OpenAI-compatible LLM extraction only on complex syntax.
- **Bi-Temporal Model**: Every relation edge stores:
  - `valid_from`: Effective real-world start timestamp
  - `valid_to`: Effective real-world invalidation timestamp (or `None` if ongoing)
  - `tx_time`: Transaction time when the agent learned the fact
  - `is_current`: Boolean flag for active state
- **Automated Contradiction Resolution**: When an entity's functional state changes (e.g. relocation, career move), older facts are automatically marked expired and superseded.
- **Point-in-Time Time Travel**: Query memory as of any arbitrary timestamp $T$ using strict temporal predicates (`valid_from <= T AND (valid_to IS NULL OR valid_to > T)`).
- **Interactive Visual Scrubber**: Interactive visual graph with dynamic time slider from 2019 to Present.
- **Empirical Evaluation Suite**: Real live benchmark runner computing Precision, Recall, F1, Contradiction Resolution Accuracy, and Dollar/Token savings.

---

## 3. Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI endpoints (health, episodes, facts, graph, retrieval, inference, evaluation, seed)
│   │   ├── core/           # Configuration & environment settings
│   │   ├── db/             # Neo4j client, SQLite persistent mirror, and UnifiedGraphStore
│   │   ├── models/         # Pydantic schemas (Episode, Fact, Retrieval, Inference, Evaluation)
│   │   ├── services/       # Extraction, Contradiction, Retrieval, Inference, Evaluation services
│   │   └── main.py         # FastAPI application entrypoint & lifespan
│   ├── tests/              # Pytest test suite (unit & integration tests)
│   ├── Dockerfile          # Backend container specification
│   ├── requirements.txt    # Python dependencies
│   └── pytest.ini          # Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router (layout, page, styles)
│   │   ├── components/     # UI components (Header, Ingestion, Graph, Retrieval, Inference, Evaluation, Audit)
│   │   ├── lib/            # Typed API client
│   │   └── types/          # TypeScript interface definitions
│   ├── Dockerfile          # Frontend container specification
│   ├── package.json        # Node.js dependencies
│   ├── tailwind.config.ts  # Tailwind CSS styling configuration
│   └── tsconfig.json       # TypeScript compiler settings
├── docker-compose.yml      # Single-command orchestration (Neo4j, Backend, Frontend)
├── .env.example            # Environment template
└── README.md               # Documentation

```

All 7 test suites pass (45 passed, 1 skipped due to live provider requirement):
1. `tests/test_extraction.py`: Validates deterministic rules, coreference resolution, and $0.00 token accounting.
2. `tests/test_contradiction.py`: Validates supersession and bi-temporal intervals.
3. `tests/test_retrieval_and_inference.py`: Validates time-travel queries ("Where did Alice live in 2021?" vs "Where does Alice live now?").
4. `tests/test_temporal_research_validity.py`: Validates the 7 core research validity properties:
   - Multiple sequential transitions (A -> B -> C -> D)
   - Same-day fact changes with sub-second precision
   - Exact temporal validity boundary queries
   - Out-of-order episode ingestion (historical backfill)
   - Evidence-grounded conversational QA
   - Provenance linking and ambiguous input rejection
   - **Intra-utterance self-corrections & retractions (Priority 1 bug fix)**
5. `tests/test_hybrid_extraction.py`: Validates confidence gating, schema enforcement, and retry resilience.
6. `tests/test_reproducible_benchmark.py`: Validates dataset schema, metric formulas, and stale fact error detection.
7. `tests/test_temporal_engine.py`: Validates transactional atomicity, idempotency, and rollback.

To run the end-to-end 5-point verification script:
```bash
python scripts/e2e_user_verification.py
```

---

## 4. Reproducible Benchmark Pipeline & Empirical Evaluation

Chronos Memory includes a reproducible research evaluation pipeline designed to evaluate conversational memory systems across multi-turn scenarios under identical conditions.

### Labelled Dataset Specification (`benchmarks/dataset/scenarios.json`)
The dataset includes **35 labelled scenarios** (with a schema structured to expand toward **150 scenarios**), spanning 8 diverse categories:
1. **Software Stacks** (5 scenarios): Backend frameworks (Flask $\to$ FastAPI), database migrations (PostgreSQL $\to$ DynamoDB), frontend transitions (Vue.js $\to$ Next.js), cloud migrations (AWS $\to$ GCP), and language modernization (Java $\to$ Kotlin).
2. **Location Changes** (5 scenarios): Domestic, multi-hop (NYC $\to$ Berlin $\to$ Tokyo), and remote relocations.
3. **Employment & Roles** (5 scenarios): Company transitions (Google $\to$ OpenAI), promotions (Senior Eng $\to$ Eng Manager), resignations, and startup foundings.
4. **Projects** (4 scenarios): Project leadership, ownership handoffs, and deprecations.
5. **Non-Conflicting Additions** (5 scenarios): Concurrent skills (Python + Rust), multiple hardware devices, and concurrent repository maintainership.
6. **Repeated Facts / Idempotency** (3 scenarios): Confirming existing facts without creating duplicate active edges or closing validity intervals.
7. **Ambiguous Inputs** (4 scenarios): Hypothetical future intentions, chit-chat filler, and conditional statements that must not overwrite current active state.
8. **Adversarial Scenarios** (4 scenarios): Intra-utterance self-corrections (*"I work at Meta, wait actually I left Meta..."*), temporal out-of-order backfills, and multi-entity distractors.

Each scenario explicitly defines:
- `episode_sequence`: Chronological turns with session ID, speaker, text, and timestamp.
- `expected_active_facts`: Ground-truth triplets $(s, p, o)$ that must be active at the end.
- `expected_historical_facts`: Ground-truth triplets $(s, p, o)$ that must be closed and superseded.
- `expected_contradictions`: Expected number of closed temporal invalidations.
- `expected_test_queries`: Target queries with `expected_keywords` and `forbidden_keywords` to detect **Stale-Fact Errors**.

---


### Baseline Handling Policy
- **Chronos Hybrid**: Always operational. Uses deterministic rules first and confidence-gated LLM fallback when confidence $< \tau$ ($0.80$).
- **Always-LLM**: Routes 100% of turns to LLM extraction. Uses live OpenAI model when `OPENAI_API_KEY` is provided; uses the standardized simulated offline LLM baseline when offline (clearly labeled with `tokens_is_measured = False`).
- **Mem0 & Graphiti**: Evaluated only when their packages and live API credentials are configured in the environment. If dependencies or API keys are missing, the runner truthfully reports their status as **`not_run`** with the exact missing requirement instead of fabricating numbers.

---

### Preliminary Results vs. Iteration 2 Results

The table below contrasts the preliminary baseline results with the post-audit **Iteration 2** results across the 35 labelled benchmark scenarios:

| Metric | Preliminary (Chronos Hybrid) | **Iteration 2 (Chronos Hybrid)** | Always-LLM Baseline |
| :--- | :---: | :---: | :---: |
| **Overall F1 Score** | 72.6% | **87.0%** (+14.4%) | 93.8% |
| **Active Facts F1** | 76.5% | **91.1%** (+14.6%) | 94.7% |
| **Historical Facts F1** | 66.7% | **77.8%** (+11.1%) | 91.7% |
| **Query Accuracy** | 65.1% | **90.7%** (+25.6%) | 93.0% |
| **Stale-Fact Errors** | 1 | **0** (Zero stale facts) | 0 |
| **Total Tokens Consumed** | 9,815 | **7,647** | 27,062 |
| **Token Reduction vs LLM** | 63.7% | **71.7%** | Baseline |
| **Estimated Cost (USD)** | $0.00186 | **$0.00144** | $0.00525 |
| **Mean Ingest Latency** | 7.9 ms | **7.2 ms** (3.6x speedup) | 26.4 ms |
| **Rule Bypass Rate** | 71.4% | **71.4%** (28.6% fallback) | 0.0% |

---

### Cost-versus-Quality Threshold Sweep Experiment (`benchmarks/experiments/threshold_sweep.py`)

To evaluate the trade-off between rule confidence gating and extraction quality, we evaluated rule-confidence thresholds $\tau \in [0.60, 0.70, 0.80, 0.90, 0.99]$ across the identical 35 scenarios:

| Gating Threshold ($\\tau$) | Overall F1 | Query Accuracy | Stale Errors | Fallback Rate | Total Tokens | Estimated Cost | Mean Latency |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $\\tau = 0.60$ | 87.0% | 90.7% | 0 | 28.6% | 7,647 | $0.00144 | 7.2 ms |
| $\\tau = 0.70$ | 87.0% | 90.7% | 0 | 28.6% | 7,647 | $0.00144 | 7.0 ms |
| $\\tau = 0.80$ **(Recommended)** | **87.0%** | **90.7%** | **0** | **28.6%** | **7,647** | **$0.00144** | **7.3 ms** |
| $\\tau = 0.90$ | 87.0% | 90.7% | 0 | 28.6% | 7,647 | $0.00144 | 6.9 ms |
| $\\tau = 0.99$ *(Forced LLM)* | 93.8% | 93.0% | 0 | 100.0% | 27,062 | $0.00525 | 26.1 ms |

#### Recommended Operating Point: $\\tau = 0.80$
- **Rationale**: Setting $\\tau = 0.80$ achieves **87.0% F1** and **90.7% Query Accuracy** with **0 stale-fact errors**, while consuming **71.7% fewer tokens** and running **3.6x faster** than the pure LLM strategy. Pushing to $\\tau = 0.99$ incurs a 253% token increase (+19,415 tokens) and 3.7x latency penalty for only a marginal 2.3% gain in query accuracy.

---


### Limitations & Scope
1. **Third-Party Baseline Dependencies**: Mem0 (`mem0ai`) and Graphiti (`graphiti-core`) require external Python packages and live API keys; when uninstalled or unconfigured, the benchmark runner truthfully reports their status as `not_run` rather than fabricating simulated baseline metrics.
2. **Deterministic Coverage**: Deterministic regex extraction covers structured conversational transitions (locations, software stacks, employment, titles, hardware, tools, repositories, and relationships). Highly idiomatic or ambiguous phrasing outside these patterns routes to the LLM fallback.

---

### API Endpoint Integration

The benchmark can also be triggered and inspected programmatically:

- `POST /api/evaluation/benchmark?limit=35&strategies=all`: Triggers the reproducible benchmark and returns JSON results.
- `GET /api/evaluation/benchmark/latest`: Returns the canonical results.
- `GET /api/evaluation/benchmark/scenarios`: Returns the full labelled dataset schema and scenarios.

---

## 5. License

MIT License. Designed and developed as a B.Tech CSE (AI & ML) Major Project.

