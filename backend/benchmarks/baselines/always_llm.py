import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from benchmarks.baselines.base import BaseMemoryStrategy
from app.db.graph_store import graph_store
from app.services.contradiction_service import contradiction_service
from app.services.chat_service import chat_service
from app.services.extractors.llm_extractor import llm_extractor
from app.services.extractors.base import BaseExtractor
from app.services.evaluation_service import BenchmarkSimulatedLLMExtractor
from app.models.episode import Episode, EpisodeCreate
from app.models.fact import Fact
from app.core.config import settings

logger = logging.getLogger("chronos.benchmarks.always_llm")

class AlwaysLLMStrategy(BaseMemoryStrategy):
    """
    Baseline Strategy: Calls an LLM on 100% of episode turns without rule pre-filtering.
    Uses live OpenAI model if configured, or standardized simulated benchmark extractor offline.
    """
    def __init__(self, llm_engine_override: Optional[BaseExtractor] = None, name: str = "always_llm"):
        is_live = llm_extractor.is_configured() and llm_engine_override is None
        super().__init__(name=name, is_live=is_live)
        self.llm_engine_override = llm_engine_override
        self.active_llm: Optional[BaseExtractor] = None

    def is_available(self) -> Tuple[bool, str]:
        if self.is_live:
            return True, f"Live OpenAI-compatible LLM ({settings.LLM_MODEL})"
        return True, "Offline Benchmark Simulated LLM Baseline (deterministic offline fixture)"

    async def setup(self) -> None:
        graph_store.reset_database()
        if self.llm_engine_override:
            self.active_llm = self.llm_engine_override
        elif llm_extractor.is_configured():
            self.active_llm = llm_extractor
        else:
            self.active_llm = BenchmarkSimulatedLLMExtractor()

    async def ingest_episode(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        episode = Episode(
            session_id=session_id,
            speaker=speaker,
            text=text,
            timestamp=timestamp
        )
        
        # 1. 100% of turns invoke the LLM extractor
        ext_res = await self.active_llm.extract(
            text=text,
            episode_time=timestamp,
            default_speaker=speaker
        )
        
        confirmed_facts: List[Fact] = []
        all_invalidated: List[Fact] = []
        
        # 2. Persist in graph store
        with graph_store.transaction() as tx:
            graph_store.store_episode(episode, conn=tx)
            
            for fact in ext_res.facts:
                fact.source_episode_id = episode.id
                fact.episode_id = episode.id
                
                resolved_fact, invalidated, is_duplicate = contradiction_service.resolve_contradictions(
                    fact,
                    conn=tx
                )
                all_invalidated.extend(invalidated)
                if not is_duplicate:
                    graph_store.store_fact(resolved_fact, conn=tx)
                    confirmed_facts.append(resolved_fact)
                else:
                    confirmed_facts.append(resolved_fact)

        return {
            "latency_ms": ext_res.latency_ms,
            "input_tokens": ext_res.input_tokens,
            "output_tokens": ext_res.output_tokens,
            "total_tokens": ext_res.total_tokens,
            "tokens_is_measured": ext_res.tokens_is_measured,
            "cost_usd": ext_res.estimated_cost_usd,
            "method": "always_llm",
            "extracted_count": len(confirmed_facts),
            "invalidated_count": len(all_invalidated),
            "fallback_triggered": True
        }

    async def answer_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        from app.models.chat import ChatRequest
        chat_resp = await chat_service.process_chat(
            ChatRequest(message=query, session_id=session_id)
        )
        return {
            "answer": chat_resp.answer,
            "latency_ms": chat_resp.latency_ms,
            "confidence": chat_resp.confidence,
            "grounded": chat_resp.grounded
        }

    async def get_active_facts(self) -> List[Dict[str, str]]:
        facts = graph_store.get_facts(only_current=True, limit=500)
        return [{"subject": f.subject, "predicate": f.predicate, "object": f.object} for f in facts]

    async def get_historical_facts(self) -> List[Dict[str, str]]:
        all_facts = graph_store.get_facts(limit=500)
        superseded = [f for f in all_facts if not f.is_current]
        return [{"subject": f.subject, "predicate": f.predicate, "object": f.object} for f in superseded]

    async def teardown(self) -> None:
        graph_store.reset_database()
