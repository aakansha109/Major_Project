import pytest
import json
import httpx
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.config import settings
from app.models.fact import Fact
from app.services.extractors.base import BaseExtractor, ExtractionResult, LLMExtractedTriplet
from app.services.extractors.rule_extractor import RuleBasedExtractor
from app.services.extractors.llm_extractor import LLMBasedExtractor
from app.services.extractors.hybrid_extractor import ConfidenceGatedHybridExtractor
from app.services.evaluation_service import evaluation_service

@pytest.mark.asyncio
async def test_rule_based_extraction_telemetry():
    """Rule-based extractor must report 0 tokens, $0.00 cost, and tokens_is_measured=True."""
    extractor = RuleBasedExtractor()
    t = datetime(2023, 6, 1, 12, 0, tzinfo=timezone.utc)
    res = await extractor.extract("Alice moved to Seattle in 2020.", t)

    assert len(res.facts) == 1
    assert res.facts[0].subject == "Alice"
    assert res.facts[0].predicate == "lives_in"
    assert "Seattle" in res.facts[0].object
    assert res.input_tokens == 0
    assert res.output_tokens == 0
    assert res.total_tokens == 0
    assert res.tokens_is_measured is True
    assert res.estimated_cost_usd == 0.0
    assert res.confidence >= 0.90
    assert "deterministic" in res.decision_reason.lower()
    assert res.fallback_triggered is False

@pytest.mark.asyncio
async def test_hybrid_bypasses_llm_on_high_confidence_rule():
    """When a rule matches with confidence >= threshold, the LLM must NEVER be called."""
    mock_llm = MagicMock(spec=LLMBasedExtractor)
    mock_llm.extract = AsyncMock()

    hybrid = ConfidenceGatedHybridExtractor(
        rule_engine=RuleBasedExtractor(),
        llm_engine=mock_llm,
        confidence_threshold=0.80
    )

    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    res = await hybrid.extract("Bob joined OpenAI in 2024.", t)

    assert len(res.facts) == 1
    assert res.facts[0].subject == "Bob"
    assert res.facts[0].predicate == "works_at"
    assert "OpenAI" in res.facts[0].object
    assert res.extraction_method == "hybrid_rule"
    assert res.fallback_triggered is False
    assert res.total_tokens == 0
    assert res.estimated_cost_usd == 0.0
    assert "accepted deterministic extraction" in res.decision_reason

    # Verify LLM was never called
    mock_llm.extract.assert_not_called()

@pytest.mark.asyncio
async def test_hybrid_fallback_invoked_on_unrecognized_text():
    """When rules cannot interpret a message, hybrid extractor calls LLM fallback."""
    mock_llm = MagicMock(spec=LLMBasedExtractor)
    mock_llm.model = "gpt-4o-mini-mock"
    mock_llm.is_configured.return_value = True

    t = datetime(2024, 7, 1, 12, 0, tzinfo=timezone.utc)
    fallback_fact = Fact(
        subject="John Smith",
        predicate="role_title",
        object="Head of AI Research",
        valid_from=t,
        status="active",
        is_current=True,
        confidence=0.92,
        extraction_method="llm",
        tokens_used=420,
        input_tokens=380,
        output_tokens=40,
        tokens_is_measured=True,
        estimated_cost_usd=0.000081,
        decision_reason="Mock LLM extraction"
    )

    mock_llm.extract = AsyncMock(return_value=ExtractionResult(
        facts=[fallback_fact],
        confidence=0.92,
        extraction_method="llm",
        latency_ms=120.0,
        input_tokens=380,
        output_tokens=40,
        total_tokens=420,
        tokens_is_measured=True,
        estimated_cost_usd=0.000081,
        cost_pricing_basis=settings.COST_PRICING_BASIS_DESC,
        decision_reason="Extracted by mock LLM",
        fallback_triggered=True
    ))

    hybrid = ConfidenceGatedHybridExtractor(
        rule_engine=RuleBasedExtractor(),
        llm_engine=mock_llm,
        confidence_threshold=0.80
    )

    text = "Due to recent restructuring, Dr. John Smith was appointed Head of AI Research."
    res = await hybrid.extract(text, t)

    assert len(res.facts) == 1
    assert res.facts[0].subject == "John Smith"
    assert res.extraction_method == "hybrid_llm_fallback"
    assert res.fallback_triggered is True
    assert res.total_tokens == 420
    assert res.input_tokens == 380
    assert res.output_tokens == 40
    assert res.tokens_is_measured is True
    assert "fallback called gpt-4o-mini-mock" in res.decision_reason

    mock_llm.extract.assert_called_once()

@pytest.mark.asyncio
async def test_llm_schema_validation_and_rejections():
    """Pydantic schema must reject malformed, circular, or invalid triplets."""
    # Test 1: Valid triplet
    valid = LLMExtractedTriplet(
        subject="Alice",
        predicate="works_at",
        object="DeepMind",
        confidence=0.95
    )
    is_ok, reason = valid.is_valid_triplet()
    assert is_ok is True
    assert reason is None

    # Test 2: Circular fact rejection
    circular = LLMExtractedTriplet(
        subject="Python",
        predicate="is",
        object="python",
        confidence=0.90
    )
    is_ok, reason = circular.is_valid_triplet()
    assert is_ok is False
    assert "Circular fact rejected" in reason

    # Test 3: Short gibberish
    too_short = LLMExtractedTriplet(
        subject="A",
        predicate="is",
        object="B",
        confidence=0.90
    )
    is_ok, reason = too_short.is_valid_triplet()
    assert is_ok is False
    assert "too short" in reason

@pytest.mark.asyncio
async def test_llm_malformed_json_handling():
    """LLMBasedExtractor must reject unparseable output rather than inserting blind facts."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "This is definitely not JSON and has no brackets"}}],
        "usage": {"prompt_tokens": 350, "completion_tokens": 15}
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response

    llm = LLMBasedExtractor(api_key="test-key", http_client=mock_client)
    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    res = await llm.extract("Random conversational chatter", t)

    assert len(res.facts) == 0
    assert "rejected: malformed JSON" in res.decision_reason
    assert len(res.validation_errors) > 0
    assert res.total_tokens == 365
    assert res.tokens_is_measured is True

@pytest.mark.asyncio
async def test_llm_retry_and_timeout_resilience():
    """LLMBasedExtractor must retry up to max_retries on network timeout and handle failure gracefully."""
    mock_client = AsyncMock()
    # Always raise TimeoutException
    mock_client.post.side_effect = httpx.TimeoutException("Read timeout on provider socket")

    llm = LLMBasedExtractor(
        api_key="test-key",
        timeout_seconds=0.1,
        max_retries=2,
        http_client=mock_client
    )

    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    res = await llm.extract("Sarah relocated to Zurich.", t)

    # 1 initial try + 2 retries = 3 calls
    assert mock_client.post.call_count == 3
    assert len(res.facts) == 0
    assert "failure after 2 retries" in res.decision_reason.lower()
    assert res.fallback_triggered is True

@pytest.mark.asyncio
async def test_no_api_key_rule_safety():
    """Without an API key, rule-based extraction works perfectly and LLM degrades gracefully."""
    rule_ext = RuleBasedExtractor()
    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    res_rule = await rule_ext.extract("Diana upgraded to a MacBook Pro M3.", t)
    assert len(res_rule.facts) == 1

    # Unconfigured LLM extractor
    unconfigured_llm = LLMBasedExtractor(api_key="")
    assert unconfigured_llm.is_configured() is False
    res_llm = await unconfigured_llm.extract("Ambiguous sentence without rule match", t)
    assert len(res_llm.facts) == 0
    assert "safely skipped without writing guessed facts" in res_llm.decision_reason

@pytest.mark.asyncio
async def test_strategy_comparison_benchmark():
    """
    Evaluates Strategy A (100% LLM) vs Strategy B (Confidence-Gated Hybrid) on the same dataset.
    Verifies that token reduction, precision, recall, F1, latency, and hypothesis test are computed.
    """
    comp_result = await evaluation_service.compare_strategies()

    assert comp_result.dataset_size >= 10
    assert comp_result.strategy_a.total_tokens > comp_result.strategy_b.total_tokens
    assert comp_result.token_reduction_percent > 0.0
    assert comp_result.latency_speedup_factor >= 1.0

    # Ensure Strategy B achieves high F1 and uses fewer tokens
    assert comp_result.strategy_b.f1_score >= 0.80
    assert comp_result.strategy_b.fallback_call_rate < 1.0
    assert comp_result.strategy_b.rule_extraction_rate > 0.0

    # Verify hypothesis metadata is documented
    assert "Rules-first" in comp_result.hypothesis_tested
    assert isinstance(comp_result.hypothesis_supported, bool)
    assert len(comp_result.limitations) >= 3

@pytest.mark.skipif(
    not settings.LIVE_LLM_TESTS_ENABLED or not settings.OPENAI_API_KEY,
    reason="Live LLM tests require explicit LIVE_LLM_TESTS_ENABLED=True and valid OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_live_openai_compatible_integration():
    """Optional live integration test against a configured OpenAI-compatible provider."""
    live_extractor = LLMBasedExtractor()
    t = datetime.now(timezone.utc)
    res = await live_extractor.extract("Alice is currently the Chief Scientist at Anthropic.", t)

    assert res.total_tokens > 0
    assert res.tokens_is_measured is True
    assert len(res.facts) >= 1
    assert "Anthropic" in res.facts[0].object

@pytest.mark.asyncio
async def test_threshold_boundary_routing_decisions():
    """
    Research Validity Audit (Priority 1):
    Proves that the configured confidence threshold tau strictly governs routing decisions.
    Examples near threshold boundaries route to deterministic rules or LLM fallback
    depending on whether rule confidence >= tau.
    """
    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    fallback_fact = Fact(
        subject="User", predicate="test", object="test", valid_from=t,
        status="active", is_current=True, confidence=0.90, extraction_method="llm"
    )

    # Helper to build mock LLM
    def create_mock_llm():
        mock = MagicMock(spec=LLMBasedExtractor)
        mock.model = "gpt-4o-mini-mock"
        mock.is_configured.return_value = True
        mock.extract = AsyncMock(return_value=ExtractionResult(
            facts=[fallback_fact], confidence=0.90, extraction_method="llm",
            latency_ms=100.0, input_tokens=300, output_tokens=30, total_tokens=330,
            tokens_is_measured=True, estimated_cost_usd=0.000063, decision_reason="Mock LLM",
            fallback_triggered=True
        ))
        return mock

    rule_eng = RuleBasedExtractor()

    # Case 1: backend_informal has confidence = 0.75
    # Text: "I think we use FastAPI for now"
    text_075 = "I think we use FastAPI for now"
    rule_res_075 = await rule_eng.extract(text_075, t)
    assert len(rule_res_075.facts) == 1
    assert rule_res_075.confidence == 0.75

    # At tau = 0.70: 0.75 >= 0.70 -> Bypasses LLM (routes to Rule)
    mock_llm_70 = create_mock_llm()
    hybrid_70 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_70, confidence_threshold=0.70)
    res_70 = await hybrid_70.extract(text_075, t)
    assert res_70.extraction_method == "hybrid_rule"
    assert res_70.fallback_triggered is False
    assert res_70.total_tokens == 0
    mock_llm_70.extract.assert_not_called()

    # At tau = 0.80: 0.75 < 0.80 -> Gating fails -> Routes to LLM Fallback
    mock_llm_80 = create_mock_llm()
    hybrid_80 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_80, confidence_threshold=0.80)
    res_80 = await hybrid_80.extract(text_075, t)
    assert res_80.extraction_method == "hybrid_llm_fallback"
    assert res_80.fallback_triggered is True
    assert res_80.total_tokens == 330
    mock_llm_80.extract.assert_called_once()

    # Case 2: job_contracting has confidence = 0.85
    # Text: "I am contracting for Google"
    text_085 = "I am contracting for Google"
    rule_res_085 = await rule_eng.extract(text_085, t)
    assert len(rule_res_085.facts) == 1
    assert rule_res_085.confidence == 0.85

    # At tau = 0.80: 0.85 >= 0.80 -> Bypasses LLM
    mock_llm_b80 = create_mock_llm()
    hybrid_b80 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_b80, confidence_threshold=0.80)
    res_b80 = await hybrid_b80.extract(text_085, t)
    assert res_b80.extraction_method == "hybrid_rule"
    assert res_b80.fallback_triggered is False
    mock_llm_b80.extract.assert_not_called()

    # At tau = 0.90: 0.85 < 0.90 -> Routes to LLM Fallback
    mock_llm_b90 = create_mock_llm()
    hybrid_b90 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_b90, confidence_threshold=0.90)
    res_b90 = await hybrid_b90.extract(text_085, t)
    assert res_b90.extraction_method == "hybrid_llm_fallback"
    assert res_b90.fallback_triggered is True
    mock_llm_b90.extract.assert_called_once()

    # Case 3: relocation_visiting has confidence = 0.65
    # Text: "I am visiting in Boston"
    text_065 = "I am visiting in Boston"
    rule_res_065 = await rule_eng.extract(text_065, t)
    assert len(rule_res_065.facts) == 1
    assert rule_res_065.confidence == 0.65

    # At tau = 0.60: 0.65 >= 0.60 -> Bypasses LLM
    mock_llm_c60 = create_mock_llm()
    hybrid_c60 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_c60, confidence_threshold=0.60)
    res_c60 = await hybrid_c60.extract(text_065, t)
    assert res_c60.extraction_method == "hybrid_rule"
    assert res_c60.fallback_triggered is False
    mock_llm_c60.extract.assert_not_called()

    # At tau = 0.70: 0.65 < 0.70 -> Routes to LLM Fallback
    mock_llm_c70 = create_mock_llm()
    hybrid_c70 = ConfidenceGatedHybridExtractor(rule_engine=rule_eng, llm_engine=mock_llm_c70, confidence_threshold=0.70)
    res_c70 = await hybrid_c70.extract(text_065, t)
    assert res_c70.extraction_method == "hybrid_llm_fallback"
    assert res_c70.fallback_triggered is True
    mock_llm_c70.extract.assert_called_once()
