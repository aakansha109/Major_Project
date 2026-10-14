import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from benchmarks.baselines.base import BaseMemoryStrategy
from app.db.graph_store import graph_store
from app.services.episode_service import episode_service
from app.services.chat_service import chat_service
from app.services.extractors.llm_extractor import llm_extractor
from app.services.extractors.base import BaseExtractor
from app.models.episode import EpisodeCreate
from app.core.config import settings

logger = logging.getLogger("chronos.benchmarks.chronos_hybrid")

class ChronosHybridStrategy(BaseMemoryStrategy):
    """
    Chronos Strategy: Confidence-gated hybrid fact extraction (rules first, LLM fallback when confidence < tau)
    with bi-temporal graph contradiction resolution and conversational retrieval.
    """
    def __init__(
        self,
        fallback_extractor: Optional[BaseExtractor] = None,
        name: str = "chronos_hybrid",
        confidence_threshold: Optional[float] = None
    ):
        super().__init__(name=name, is_live=llm_extractor.is_configured())
        self.fallback_extractor = fallback_extractor
        self.confidence_threshold = confidence_threshold

    def is_available(self) -> Tuple[bool, str]:
        return True, "Chronos Hybrid Engine operational."

    async def setup(self) -> None:
        # Reset memory graph before each scenario
        graph_store.reset_database()
        
        # When offline, ensure the hybrid extractor has an active simulated LLM fallback engine
        from app.services.evaluation_service import BenchmarkSimulatedLLMExtractor
        from app.services.extractors.hybrid_extractor import ConfidenceGatedHybridExtractor
        from app.services.extractors.rule_extractor import rule_extractor
        from app.services.extraction_service import extraction_service
        
        active_llm = self.fallback_extractor
        if active_llm is None:
            active_llm = llm_extractor if llm_extractor.is_configured() else BenchmarkSimulatedLLMExtractor()
            
        thresh = self.confidence_threshold if self.confidence_threshold is not None else settings.EXTRACTION_CONFIDENCE_THRESHOLD
        extraction_service.hybrid_extractor = ConfidenceGatedHybridExtractor(
            rule_engine=rule_extractor,
            llm_engine=active_llm,
            confidence_threshold=thresh
        )

    async def ingest_episode(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        ep_create = EpisodeCreate(
            session_id=session_id,
            speaker=speaker,
            text=text,
            timestamp=timestamp
        )
        
        episode, confirmed_facts, invalidated_facts, telemetry = await episode_service.ingest_episode(ep_create)
        
        return {
            "latency_ms": telemetry.get("total_latency_ms", 0.0),
            "input_tokens": telemetry.get("input_tokens", 0),
            "output_tokens": telemetry.get("output_tokens", 0),
            "total_tokens": telemetry.get("tokens_consumed", 0),
            "tokens_is_measured": telemetry.get("tokens_is_measured", True),
            "cost_usd": telemetry.get("cost_usd", 0.0),
            "method": telemetry.get("strategy", "hybrid"),
            "extracted_count": len(confirmed_facts),
            "invalidated_count": len(invalidated_facts),
            "fallback_triggered": bool(telemetry.get("fallback_triggered", False) or telemetry.get("tier2_latency_ms", 0.0) > 0)
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
