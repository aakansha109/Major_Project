import pytest
from datetime import datetime, timezone
from app.services.extraction_service import extraction_service
from app.models.episode import Episode

@pytest.mark.asyncio
async def test_deterministic_rule_extraction():
    ep_time = datetime(2023, 5, 1, 10, 0, tzinfo=timezone.utc)
    episode = Episode(
        session_id="test_sess",
        speaker="user",
        text="Alice moved to London in 2023. She joined DeepMind in 2023.",
        timestamp=ep_time
    )

    facts, telemetry = await extraction_service.extract_facts(episode)

    assert len(facts) >= 2
    assert telemetry["strategy"] == "rule_only"
    assert telemetry["tokens_consumed"] == 0
    assert telemetry["cost_usd"] == 0.0

    preds = {f.predicate: f for f in facts}
    assert "lives_in" in preds
    assert preds["lives_in"].subject == "Alice"
    assert "London" in preds["lives_in"].object
    assert preds["lives_in"].valid_from.year == 2023

    assert "works_at" in preds
    assert preds["works_at"].subject == "Alice"
    assert "DeepMind" in preds["works_at"].object

@pytest.mark.asyncio
async def test_role_and_hardware_extraction():
    ep_time = datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
    ep1 = Episode(
        session_id="test_sess_2",
        speaker="user",
        text="Charlie became a Principal Engineer in 2022.",
        timestamp=ep_time
    )
    facts, _ = await extraction_service.extract_facts(ep1)
    assert len(facts) == 1
    assert facts[0].predicate == "role_title"
    assert "Principal Engineer" in facts[0].object
    assert facts[0].valid_from.year == 2022

    ep2 = Episode(
        session_id="test_sess_3",
        speaker="user",
        text="Diana upgraded to a MacBook Pro M3.",
        timestamp=ep_time
    )
    facts2, _ = await extraction_service.extract_facts(ep2)
    assert len(facts2) == 1
    assert facts2[0].predicate == "uses_hardware"
    assert "MacBook Pro M3" in facts2[0].object
