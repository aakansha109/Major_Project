import re
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable, Tuple
import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.models.fact import Fact
from app.services.extractors.base import (
    BaseExtractor,
    ExtractionResult,
    LLMExtractedTriplet
)

logger = logging.getLogger("chronos.extractors.llm")

SYSTEM_EXTRACTION_PROMPT = """You are Chronos Fact Extraction Engine.
Extract factual temporal relationship triplets from conversational text.
Follow these strict guidelines:
1. Extract ONLY concrete assertions (e.g., job changes, relocations, tech stack, tooling).
2. If the text is conversational filler, greeting, polite acknowledgment, or ambiguous, return an empty array [].
3. Never invent facts, entities, or dates that are not in the text.
4. Output MUST be a valid JSON array of objects with keys:
   - "subject": string (entity performing or having the attribute)
   - "predicate": string (snake_case relation, e.g. "backend_framework", "lives_in", "works_at", "database_used")
   - "object": string (value or target entity)
   - "valid_from": string (ISO timestamp or YYYY-MM-DD or null if relative to episode time)
   - "confidence": float between 0.0 and 1.0
Return ONLY the raw JSON array without markdown formatting or commentary.
"""

class LLMBasedExtractor(BaseExtractor):
    """
    OpenAI-compatible LLM fact extractor with strict Pydantic schema validation,
    retry limits, timeouts, error recovery, and exact token accounting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.api_base = (api_base if api_base is not None else settings.OPENAI_API_BASE).rstrip("/")
        self.model = model if model is not None else settings.OPENAI_MODEL
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        self._custom_client = http_client

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def _call_api_with_retries(self, payload: dict) -> Tuple[dict, Optional[str]]:
        """
        Executes HTTP call with timeout and exponential backoff retry.
        Returns (response_json, raw_content_text).
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return data, content
                finally:
                    if self._custom_client is None:
                        await client.aclose()
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as err:
                last_error = err
                logger.warning("LLM API attempt %d/%d failed: %s", attempt, self.max_retries + 1, err)
                if attempt <= self.max_retries:
                    # Exponential backoff
                    await asyncio.sleep(0.4 * (2 ** (attempt - 1)))

        raise last_error or RuntimeError("LLM API call failed after retries")

    async def extract(
        self,
        text: str,
        episode_time: datetime,
        default_speaker: str = "User"
    ) -> ExtractionResult:
        start_t = time.perf_counter()

        if not self.is_configured():
            latency_ms = (time.perf_counter() - start_t) * 1000
            return ExtractionResult(
                facts=[],
                confidence=0.0,
                extraction_method="llm",
                latency_ms=round(latency_ms, 3),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tokens_is_measured=False,
                estimated_cost_usd=0.0,
                decision_reason="LLM provider API key not configured; safely skipped without writing guessed facts",
                fallback_triggered=True
            )

        user_content = (
            f"Reference episode time: {episode_time.isoformat()}\n"
            f"Default speaker identity: {default_speaker}\n"
            f"Input conversation text:\n{text}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_EXTRACTION_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": settings.LLM_TEMPERATURE
        }

        try:
            api_data, raw_content = await self._call_api_with_retries(payload)
        except Exception as e:
            latency_ms = (time.perf_counter() - start_t) * 1000
            logger.error("LLM Extraction failed after %d retries: %s", self.max_retries, e)
            return ExtractionResult(
                facts=[],
                confidence=0.0,
                extraction_method="llm",
                latency_ms=round(latency_ms, 3),
                input_tokens=None,
                output_tokens=None,
                total_tokens=0,
                tokens_is_measured=False,
                estimated_cost_usd=0.0,
                decision_reason=f"LLM API failure after {self.max_retries} retries: {str(e)}",
                fallback_triggered=True,
                validation_errors=[str(e)]
            )

        latency_ms = (time.perf_counter() - start_t) * 1000

        # Exact token accounting
        usage = api_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        tokens_measured = prompt_tokens is not None and completion_tokens is not None

        in_tok = prompt_tokens if tokens_measured else len(text.split()) * 4 # conservative fallback
        out_tok = completion_tokens if tokens_measured else 0
        tot_tok = in_tok + out_tok

        # Monetary cost computation based on standard GPT-4o-mini rates
        cost_usd = (in_tok * settings.COST_PROMPT_PER_1M / 1_000_000) + (out_tok * settings.COST_COMPLETION_PER_1M / 1_000_000)

        # Parse & Validate Output strictly against Pydantic schema
        clean_text = raw_content.strip() if raw_content else ""
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text)
        clean_text = clean_text.strip()

        # Strict JSON parse
        validation_errors = []
        try:
            raw_parsed = json.loads(clean_text)
            if not isinstance(raw_parsed, list):
                raise ValueError("Expected JSON array of triplets")
        except Exception as err:
            logger.warning("LLM returned non-JSON format: %s. Raw: %s", err, clean_text[:100])
            return ExtractionResult(
                facts=[],
                confidence=0.0,
                extraction_method="llm",
                latency_ms=round(latency_ms, 3),
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=tot_tok,
                tokens_is_measured=tokens_measured,
                estimated_cost_usd=round(cost_usd, 7),
                cost_pricing_basis=settings.COST_PRICING_BASIS_DESC,
                decision_reason=f"LLM output rejected: malformed JSON ({str(err)})",
                fallback_triggered=True,
                raw_llm_response=clean_text,
                validation_errors=[f"Malformed JSON: {str(err)}"]
            )

        # Strict Pydantic validation on each triplet
        validated_triplets: List[LLMExtractedTriplet] = []
        for idx, item in enumerate(raw_parsed):
            try:
                triplet = LLMExtractedTriplet.model_validate(item)
                valid, reason = triplet.is_valid_triplet()
                if not valid:
                    validation_errors.append(f"Item #{idx}: {reason}")
                    continue

                # Confidence check: reject low confidence
                if triplet.confidence < settings.EXTRACTION_CONFIDENCE_THRESHOLD:
                    validation_errors.append(
                        f"Item #{idx}: Confidence {triplet.confidence:.2f} below threshold {settings.EXTRACTION_CONFIDENCE_THRESHOLD:.2f}"
                    )
                    continue

                validated_triplets.append(triplet)
            except ValidationError as val_err:
                validation_errors.append(f"Item #{idx} schema error: {str(val_err)}")

        # Convert validated triplets to Fact models
        facts = []
        for triplet in validated_triplets:
            v_from = episode_time
            if triplet.valid_from:
                try:
                    v_from = datetime.fromisoformat(triplet.valid_from.replace("Z", "+00:00"))
                except Exception:
                    v_from = episode_time

            fact = Fact(
                subject=triplet.subject,
                predicate=triplet.predicate,
                object=triplet.object,
                valid_from=v_from,
                status="active",
                is_current=True,
                confidence=triplet.confidence,
                extraction_method="llm",
                source="llm",
                tokens_used=tot_tok // max(1, len(validated_triplets)),
                input_tokens=in_tok // max(1, len(validated_triplets)),
                output_tokens=out_tok // max(1, len(validated_triplets)),
                tokens_is_measured=tokens_measured,
                estimated_cost_usd=round(cost_usd / max(1, len(validated_triplets)), 7),
                cost_pricing_basis=settings.COST_PRICING_BASIS_DESC,
                decision_reason=f"Extracted by LLM ({self.model}) with verified schema and confidence {triplet.confidence:.2f}",
                raw_text=text
            )
            facts.append(fact)

        mean_confidence = sum(f.confidence for f in facts) / len(facts) if facts else 0.0

        if facts:
            decision = f"LLM ({self.model}) extracted {len(facts)} validated facts (measured tokens: {tot_tok}, mean confidence: {mean_confidence:.2f})"
        elif validation_errors:
            decision = f"LLM output rejected by schema validation ({len(validation_errors)} error(s))"
        else:
            decision = f"LLM returned empty facts (input determined to be non-factual/conversational)"

        return ExtractionResult(
            facts=facts,
            confidence=round(mean_confidence, 2),
            extraction_method="llm",
            latency_ms=round(latency_ms, 3),
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=tot_tok,
            tokens_is_measured=tokens_measured,
            estimated_cost_usd=round(cost_usd, 7),
            cost_pricing_basis=settings.COST_PRICING_BASIS_DESC,
            decision_reason=decision,
            fallback_triggered=True,
            raw_llm_response=clean_text,
            validation_errors=validation_errors
        )

llm_extractor = LLMBasedExtractor()
