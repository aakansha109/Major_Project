import time
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from app.models.fact import Fact
from app.models.episode import Episode
from app.services.extractors import (
    rule_extractor,
    llm_extractor,
    hybrid_extractor,
    ExtractionResult
)

logger = logging.getLogger("chronos.services.extraction")

class ExtractionService:
    """
    High-level facade over the Confidence-Gated Hybrid Extractor architecture.
    Provides backward compatibility while delegating to modular extractors.
    """

    def __init__(self):
        self.rule_extractor = rule_extractor
        self.llm_extractor = llm_extractor
        self.hybrid_extractor = hybrid_extractor

    def extract_deterministic(
        self,
        text: str,
        episode_time: datetime,
        default_speaker: str = "User"
    ) -> List[Fact]:
        """Synchronous wrapper for deterministic rule extraction"""
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = pool.submit(
                    asyncio.run,
                    self.rule_extractor.extract(text, episode_time, default_speaker)
                ).result()
        else:
            res = asyncio.run(self.rule_extractor.extract(text, episode_time, default_speaker))
        return res.facts

    async def extract_llm_fallback(self, text: str, episode_time: datetime) -> List[Fact]:
        """Direct call to LLM extractor"""
        res = await self.llm_extractor.extract(text, episode_time)
        return res.facts

    async def extract_facts(self, episode: Episode) -> Tuple[List[Fact], Dict[str, Any]]:
        """
        Primary extraction pipeline:
        Executes Confidence-Gated Hybrid extraction.
        Returns extracted facts and comprehensive telemetry.
        """
        speaker = "User" if episode.speaker.lower() in ["user", "human"] else episode.speaker
        result: ExtractionResult = await self.hybrid_extractor.extract(
            text=episode.text,
            episode_time=episode.timestamp,
            default_speaker=speaker
        )

        for f in result.facts:
            f.source_episode_id = episode.id
            f.episode_id = episode.id

        telemetry = {
            "strategy": "rule_only" if result.extraction_method in ["rule", "hybrid_rule"] else result.extraction_method,
            "extraction_method": result.extraction_method,
            "fact_count": len(result.facts),
            "confidence": result.confidence,
            "total_latency_ms": result.latency_ms,
            "tokens_consumed": result.total_tokens,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "tokens_is_measured": result.tokens_is_measured,
            "cost_usd": result.estimated_cost_usd,
            "cost_pricing_basis": result.cost_pricing_basis,
            "decision_reason": result.decision_reason,
            "fallback_triggered": result.fallback_triggered,
            "validation_errors": result.validation_errors
        }

        return result.facts, telemetry

extraction_service = ExtractionService()
