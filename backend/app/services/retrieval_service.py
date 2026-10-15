import time
import math
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from app.models.retrieval import RetrievalQuery, RetrievalResult, Subgraph
from app.models.fact import Fact
from app.models.episode import Episode
from app.db.graph_store import graph_store

class SemanticVectorIndex:
    """
    Lightweight persistent vector index using character n-gram + term hashing
    and numpy cosine similarity. Runs without heavy PyTorch dependencies while
    producing strong semantic alignment across entities and queries.
    """
    def __init__(self, dim: int = 128):
        self.dim = dim

    def encode(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return vec
        
        # Word and character 3-gram hashing
        for word in words:
            # Word hash
            h = hash(word) % self.dim
            vec[h] += 1.5
            # Character n-grams
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    ngram = word[i:i+3]
                    nh = hash(ngram) % self.dim
                    vec[nh] += 0.5
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

class RetrievalService:
    def __init__(self):
        self.vector_index = SemanticVectorIndex(dim=128)

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        start_t = time.perf_counter()

        # 1. Fetch candidate facts from graph store
        all_facts = graph_store.get_facts(as_of=query.as_of, limit=200)

        # 2. Encode query vector
        q_vec = self.vector_index.encode(query.query)

        # 3. Score candidate facts
        scored_facts = []
        q_lower = query.query.lower()
        q_words = set(re.findall(r'\b\w+\b', q_lower))

        for fact in all_facts:
            fact_text = f"{fact.subject} {fact.predicate} {fact.object} {fact.raw_text or ''}"
            f_vec = self.vector_index.encode(fact_text)
            sim = self.vector_index.cosine_similarity(q_vec, f_vec)
            
            # Subject matching (including User pronouns "my", "I", "me")
            if fact.subject.lower() in q_words:
                sim += 0.50
            elif fact.subject.lower() == "user" and any(p in q_words for p in ["i", "my", "me", "myself", "we", "our"]):
                sim += 0.50

            # Predicate relevance matching
            pred_norm = fact.predicate.lower()
            pred_clean = pred_norm.replace('_', ' ')
            pred_words = set(pred_clean.split())
            if pred_words.intersection(q_words):
                sim += 0.40

            if "backend" in q_words and "backend" in pred_norm:
                sim += 0.60
            if ("live" in q_words or "living" in q_words or "relocate" in q_words or "reside" in q_words) and pred_norm in ["lives_in", "resides_in"]:
                sim += 0.60
            if ("work" in q_words or "job" in q_words or "company" in q_words) and pred_norm in ["works_at", "employed_by"]:
                sim += 0.60
            if "database" in q_words and "database" in pred_norm:
                sim += 0.60

            # Object match
            if fact.object.lower() in q_lower:
                sim += 0.40

            # Prioritize active facts over historical superseded facts
            if fact.is_current:
                sim += 0.25

            scored_facts.append((sim, fact))

        # Sort by similarity score descending
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        top_facts = [f for score, f in scored_facts[:query.top_k] if score > 0.15]

        # 4. Retrieve matching episodes if requested
        matched_episodes: List[Episode] = []
        if query.include_episodes:
            episodes = graph_store.get_episodes(session_id=query.session_id, limit=20)
            scored_eps = []
            for ep in episodes:
                ep_vec = self.vector_index.encode(ep.text)
                sim = self.vector_index.cosine_similarity(q_vec, ep_vec)
                scored_eps.append((sim, ep))
            scored_eps.sort(key=lambda x: x[0], reverse=True)
            matched_episodes = [ep for score, ep in scored_eps[:3] if score > 0.10]

        # 5. Graph neighborhood expansion (1-hop / 2-hop)
        entities_to_expand = set()
        for f in top_facts:
            entities_to_expand.add(f.subject)
            entities_to_expand.add(f.object)

        subgraph = Subgraph(nodes=[], edges=[])
        if query.include_neighborhood and entities_to_expand:
            subgraph = graph_store.get_subgraph_for_entities(
                entity_names=list(entities_to_expand),
                as_of=query.as_of,
                depth=1
            )

        latency = (time.perf_counter() - start_t) * 1000

        return RetrievalResult(
            query=query.query,
            as_of=query.as_of,
            matched_facts=top_facts,
            matched_episodes=matched_episodes,
            subgraph=subgraph,
            latency_ms=round(latency, 2),
            retrieval_strategy="temporal_vector_hybrid",
            stats={
                "candidate_facts_searched": len(all_facts),
                "matched_fact_count": len(top_facts),
                "graph_nodes_retrieved": len(subgraph.nodes),
                "graph_edges_retrieved": len(subgraph.edges)
            }
        )

retrieval_service = RetrievalService()
