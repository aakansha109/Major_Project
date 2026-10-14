import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.models.fact import Fact
from app.services.extractors.base import BaseExtractor, ExtractionResult
from app.services.extractors.rule_extractor import RuleBasedExtractor, rule_extractor
from app.services.extractors.llm_extractor import LLMBasedExtractor, llm_extractor

logger = logging.getLogger("chronos.extractors.hybrid")

class ConfidenceGatedHybridExtractor(BaseExtractor):
    """
    Research Core: Confidence-Gated Hybrid Fact Extractor.
    Executes fast deterministic rules first ($0.00, 0 tokens).
    Only routes to OpenAI-compatible LLM if rule confidence is below threshold τ.
    Tracks exact decision provenance, measured tokens, and empirical fallbacks.
    """

    def __init__(
        self,
        rule_engine: Optional[RuleBasedExtractor] = None,
        llm_engine: Optional[LLMBasedExtractor] = None,
        confidence_threshold: Optional[float] = None
    ):
        self.rule_engine = rule_engine or rule_extractor
        self.llm_engine = llm_engine or llm_extractor
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.EXTRACTION_CONFIDENCE_THRESHOLD
        )

    async def extract(
        self,
        text: str,
        episode_time: datetime,
        default_speaker: str = "User"
    ) -> ExtractionResult:
        start_t = time.perf_counter()

        # Step 1: Run Tier 1 Deterministic Rules
        rule_res = await self.rule_engine.extract(
            text=text,
            episode_time=episode_time,
            default_speaker=default_speaker
        )

        # Gate Check: If rule matched with high confidence (>= threshold)
        if len(rule_res.facts) > 0 and rule_res.confidence >= self.confidence_threshold:
            total_latency = (time.perf_counter() - start_t) * 1000
            decision = (
                f"Rule confidence ({rule_res.confidence:.2f}) >= threshold ({self.confidence_threshold:.2f}); "
                f"accepted deterministic extraction without LLM invocation (Saved {len(text.split()) * 4} estimated tokens, $0.00 cost)"
            )
            # Annotate facts
            for f in rule_res.facts:
                f.extraction_method = "rule"
                f.source = "rule"
                f.decision_reason = decision

            return ExtractionResult(
                facts=rule_res.facts,
                confidence=rule_res.confidence,
                extraction_method="hybrid_rule",
                latency_ms=round(total_latency, 3),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tokens_is_measured=True,
                estimated_cost_usd=0.0,
                cost_pricing_basis="Deterministic rule match (Zero LLM tokens used)",
                decision_reason=decision,
                fallback_triggered=False
            )

        # Step 2: Gating Failed -> Route to LLM Fallback
        logger.info(
            "Rule confidence %.2f < threshold %.2f (or 0 facts matched); gating triggered LLM fallback.",
            rule_res.confidence, self.confidence_threshold
        )

        # If LLM fallback is disabled or unconfigured
        if not settings.ENABLE_LLM_FALLBACK or not self.llm_engine.is_configured():
            total_latency = (time.perf_counter() - start_t) * 1000
            decision = (
                f"Rule confidence ({rule_res.confidence:.2f}) < threshold ({self.confidence_threshold:.2f}); "
                f"LLM fallback unconfigured or disabled. Guarded against guessing: 0 facts inserted."
            )
            return ExtractionResult(
                facts=[],
                confidence=0.0,
                extraction_method="rejected",
                latency_ms=round(total_latency, 3),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tokens_is_measured=False,
                estimated_cost_usd=0.0,
                decision_reason=decision,
                fallback_triggered=False
            )

        # Call LLM Fallback
        llm_res = await self.llm_engine.extract(
            text=text,
            episode_time=episode_time,
            default_speaker=default_speaker
        )

        total_latency = (time.perf_counter() - start_t) * 1000

        decision = (
            f"Rule confidence ({rule_res.confidence:.2f}) < threshold ({self.confidence_threshold:.2f}); "
            f"fallback called {self.llm_engine.model}. Outcome: {llm_res.decision_reason}"
        )

        for f in llm_res.facts:
            f.extraction_method = "hybrid_llm_fallback"
            f.source = "hybrid_llm_fallback"
            f.decision_reason = decision

        return ExtractionResult(
            facts=llm_res.facts,
            confidence=llm_res.confidence,
            extraction_method="hybrid_llm_fallback" if llm_res.facts else "rejected",
            latency_ms=round(total_latency, 3),
            input_tokens=llm_res.input_tokens,
            output_tokens=llm_res.output_tokens,
            total_tokens=llm_res.total_tokens,
            tokens_is_measured=llm_res.tokens_is_measured,
            estimated_cost_usd=llm_res.estimated_cost_usd,
            cost_pricing_basis=llm_res.cost_pricing_basis,
            decision_reason=decision,
            fallback_triggered=True,
            raw_llm_response=llm_res.raw_llm_response,
            validation_errors=llm_res.validation_errors
        )

hybrid_extractor = ConfidenceGatedHybridExtractor()
