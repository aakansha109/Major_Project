import pytest
from datetime import datetime, timezone, timedelta
from app.models.episode import EpisodeCreate
from app.models.chat import ChatRequest
from app.services.episode_service import episode_service
from app.services.chat_service import chat_service
from app.db.graph_store import graph_store

@pytest.fixture(autouse=True)
def clean_database():
    graph_store.reset_database()
    yield
    graph_store.reset_database()

@pytest.mark.asyncio
async def test_multiple_sequential_fact_changes():
    """
    Test 1: Multiple fact changes (A -> B -> C -> D)
    Verifies that a series of transitions closes each previous interval cleanly
    and leaves exactly one active fact with all previous states preserved.
    """
    t1 = datetime(2020, 1, 15, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2021, 6, 1, 10, 0, tzinfo=timezone.utc)
    t3 = datetime(2023, 3, 10, 10, 0, tzinfo=timezone.utc)
    t4 = datetime(2024, 8, 20, 10, 0, tzinfo=timezone.utc)

    # Ingest 4 transitions
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="multi_seq", speaker="user", text="My backend framework is Flask.", timestamp=t1
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="multi_seq", speaker="user", text="I switched my backend to Django.", timestamp=t2
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="multi_seq", speaker="user", text="I switched my backend to FastAPI.", timestamp=t3
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="multi_seq", speaker="user", text="I switched my backend to Go.", timestamp=t4
    ))

    # Verify only Go is active
    active = graph_store.get_facts(subject="User", predicate="backend_framework", only_current=True)
    assert len(active) == 1
    assert active[0].object == "Go"
    assert active[0].status == "active"
    assert active[0].valid_to is None
    assert active[0].valid_from == t4

    # Verify all 4 historical facts exist in chronological order
    history = graph_store.get_fact_history(subject="User", predicate="backend_framework")
    assert len(history) == 4
    objects = [f.object for f in history]
    assert objects == ["Flask", "Django", "FastAPI", "Go"]

    # Verify exact validity interval chaining
    f_flask, f_django, f_fastapi, f_go = history
    assert f_flask.valid_from == t1 and f_flask.valid_to == t2 and f_flask.status == "superseded"
    assert f_django.valid_from == t2 and f_django.valid_to == t3 and f_django.status == "superseded"
    assert f_fastapi.valid_from == t3 and f_fastapi.valid_to == t4 and f_fastapi.status == "superseded"
    assert f_go.valid_from == t4 and f_go.valid_to is None and f_go.status == "active"

    # Point-in-time evaluations
    assert graph_store.get_facts(as_of=datetime(2020, 8, 1, tzinfo=timezone.utc), predicate="backend_framework")[0].object == "Flask"
    assert graph_store.get_facts(as_of=datetime(2022, 1, 1, tzinfo=timezone.utc), predicate="backend_framework")[0].object == "Django"
    assert graph_store.get_facts(as_of=datetime(2023, 8, 1, tzinfo=timezone.utc), predicate="backend_framework")[0].object == "FastAPI"
    assert graph_store.get_facts(as_of=datetime(2025, 1, 1, tzinfo=timezone.utc), predicate="backend_framework")[0].object == "Go"

@pytest.mark.asyncio
async def test_same_day_fact_changes():
    """
    Test 2: Same-day changes with sub-day precision.
    Verifies that two updates on the same calendar day transition correctly.
    """
    morning = datetime(2024, 5, 10, 9, 30, 0, tzinfo=timezone.utc)
    evening = datetime(2024, 5, 10, 17, 45, 0, tzinfo=timezone.utc)

    await episode_service.ingest_episode(EpisodeCreate(
        session_id="same_day", speaker="user", text="My backend framework is Flask.", timestamp=morning
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="same_day", speaker="user", text="I switched my backend to FastAPI.", timestamp=evening
    ))

    # Active fact must be FastAPI
    active = graph_store.get_facts(subject="User", predicate="backend_framework", only_current=True)
    assert len(active) == 1
    assert active[0].object == "FastAPI"
    assert active[0].valid_from == evening

    # Flask must be superseded with valid_to = evening
    superseded = [f for f in graph_store.get_facts(predicate="backend_framework") if not f.is_current]
    assert len(superseded) == 1
    assert superseded[0].object == "Flask"
    assert superseded[0].valid_from == morning
    assert superseded[0].valid_to == evening

    # Midday query (12:00) should return Flask
    midday = datetime(2024, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    res_midday = graph_store.get_facts(as_of=midday, predicate="backend_framework")
    assert len(res_midday) == 1
    assert res_midday[0].object == "Flask"

    # Post-evening query (20:00) should return FastAPI
    post = datetime(2024, 5, 10, 20, 0, 0, tzinfo=timezone.utc)
    res_post = graph_store.get_facts(as_of=post, predicate="backend_framework")
    assert len(res_post) == 1
    assert res_post[0].object == "FastAPI"

@pytest.mark.asyncio
async def test_exact_validity_boundaries():
    """
    Test 3: Exact validity boundaries [t_start, t_end).
    Validates boundary conditions:
    - At t exactly equal to t_start of Fact 1 -> Fact 1 is returned
    - At t exactly equal to t_start of Fact 2 (which is t_end of Fact 1) -> Fact 2 is returned
    """
    t_start_1 = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_boundary = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    await episode_service.ingest_episode(EpisodeCreate(
        session_id="boundary_test", speaker="user", text="My backend framework is Flask.", timestamp=t_start_1
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="boundary_test", speaker="user", text="I switched my backend to FastAPI.", timestamp=t_boundary
    ))

    # Exactly at t_start_1: Flask
    f_at_start = graph_store.get_facts(as_of=t_start_1, predicate="backend_framework")
    assert len(f_at_start) == 1
    assert f_at_start[0].object == "Flask"

    # 1 second before boundary: Flask
    f_before_bound = graph_store.get_facts(as_of=t_boundary - timedelta(seconds=1), predicate="backend_framework")
    assert len(f_before_bound) == 1
    assert f_before_bound[0].object == "Flask"

    # Exactly at boundary: FastAPI (Flask valid_to is t_boundary, so valid_to > t_boundary is False)
    f_at_bound = graph_store.get_facts(as_of=t_boundary, predicate="backend_framework")
    assert len(f_at_bound) == 1
    assert f_at_bound[0].object == "FastAPI"

@pytest.mark.asyncio
async def test_out_of_order_episodes_historical_backfill():
    """
    Test 4: Out-of-order episode ingestion (historical backfill).
    Ingests a newer fact first (2024), followed by an older historical fact (2020).
    The system must NOT overwrite the newer active state with the older backfilled fact.
    """
    t_2024 = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
    t_2020 = datetime(2020, 6, 1, 10, 0, tzinfo=timezone.utc)

    # 1. Ingest newer fact first
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="backfill_test", speaker="user", text="I moved to Denver.", timestamp=t_2024
    ))

    # 2. Ingest older backfill fact later
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="backfill_test", speaker="user", text="Alice moved to Seattle in 2020.", timestamp=t_2020
    ))

    # Denver must remain current for User
    user_active = graph_store.get_active_facts_for_predicate("User", "lives_in")
    assert len(user_active) == 1
    assert user_active[0].object == "Denver"
    assert user_active[0].is_current is True

    # Alice lives_in Seattle is recorded with valid_from=2020
    alice_facts = graph_store.get_facts(subject="Alice", predicate="lives_in")
    assert len(alice_facts) == 1
    assert alice_facts[0].object == "Seattle"
    assert alice_facts[0].valid_from.year == 2020

@pytest.mark.asyncio
async def test_historical_conversational_queries_with_evidence():
    """
    Test 5: Conversational QA over temporal facts.
    Verifies that /api/chat answers current vs historical queries accurately with strict evidence grounding.
    """
    t_2020 = datetime(2020, 1, 10, 10, 0, tzinfo=timezone.utc)
    t_2023 = datetime(2023, 5, 1, 10, 0, tzinfo=timezone.utc)

    await episode_service.ingest_episode(EpisodeCreate(
        session_id="chat_temporal", speaker="user", text="Alice moved to Seattle in 2020.", timestamp=t_2020
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="chat_temporal", speaker="user", text="Alice moved to London in 2023.", timestamp=t_2023
    ))

    # Current query
    resp_curr = await chat_service.process_chat(ChatRequest(message="Where does Alice live now?"))
    assert "London" in resp_curr.answer
    assert resp_curr.grounded is True
    assert resp_curr.evidence_status == "verified_active"

    # Historical query (previous)
    resp_prev = await chat_service.process_chat(ChatRequest(message="Where did Alice live previously?"))
    assert "Seattle" in resp_prev.answer
    assert resp_prev.grounded is True
    assert resp_prev.evidence_status == "verified_historical"

    # Point-in-time query ("in 2021")
    resp_pit = await chat_service.process_chat(ChatRequest(message="Where did Alice live in 2021?"))
    assert "Seattle" in resp_pit.answer
    assert resp_pit.grounded is True
    assert resp_pit.evidence_status == "verified_point_in_time"

@pytest.mark.asyncio
async def test_data_integrity_provenance_and_ambiguous_rejection():
    """
    Test 6: Provenance linking and ambiguous input rejection.
    Verifies that:
    1. Every extracted fact has an exact source_episode_id pointing to the originating episode.
    2. Ambiguous non-factual inputs extract zero facts and create zero records.
    """
    ep1 = EpisodeCreate(
        session_id="prov_test", speaker="user", text="My backend framework is FastAPI.",
        timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    )
    episode, confirmed, _, _ = await episode_service.ingest_episode(ep1)

    assert len(confirmed) == 1
    fact = confirmed[0]
    assert fact.source_episode_id == episode.id

    # Verify retrieval from graph store by episode ID
    facts_for_ep = graph_store.get_facts_by_episode_id(episode.id)
    assert len(facts_for_ep) == 1
    assert facts_for_ep[0].id == fact.id
    assert facts_for_ep[0].source_episode_id == episode.id

    # Ingest ambiguous / chit-chat filler
    ep_ambiguous = EpisodeCreate(
        session_id="prov_test", speaker="user", text="Sounds good! Thanks for the meeting, talk tomorrow.",
        timestamp=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed_amb, _, tel_amb = await episode_service.ingest_episode(ep_ambiguous)
    assert len(confirmed_amb) == 0
    assert tel_amb.get("fact_count", 0) == 0

    # Ensure total facts in DB is strictly still 1
    all_facts = graph_store.get_facts()
    assert len(all_facts) == 1

@pytest.mark.asyncio
async def test_intra_utterance_retraction_and_self_correction():
    """
    Test 7 (Priority 1): Intra-utterance self-corrections and retractions.
    Verifies:
    1. 'I work at Meta, wait actually I left Meta.' -> No retracted fact remains active.
    2. 'My framework is Flask—actually, I switched to FastAPI.' -> FastAPI active, Flask superseded.
    3. 'I live in Delhi, but I moved to Bangalore.' -> Bangalore active, Delhi superseded.
    4. Normal sentence containing two unrelated valid facts -> both remain active.
    5. Ambiguous correction ('I live in Delhi, wait actually maybe not.') -> rejects guessed update.
    """
    # Case 1: Pure retraction / negation within single utterance
    ep1 = EpisodeCreate(
        session_id="retract_test", speaker="user",
        text="I work at Meta, wait actually I left Meta.",
        timestamp=datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed1, _, _ = await episode_service.ingest_episode(ep1)
    active_meta = graph_store.get_facts(subject="User", predicate="works_at", only_current=True)
    assert len(active_meta) == 0, f"Retracted fact must not be active! Found: {active_meta}"

    # Case 2: Intra-utterance transition with em-dash / actually
    ep2 = EpisodeCreate(
        session_id="retract_test", speaker="user",
        text="My framework is Flask—actually, I switched to FastAPI.",
        timestamp=datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed2, _, _ = await episode_service.ingest_episode(ep2)
    active_framework = graph_store.get_facts(subject="User", predicate="backend_framework", only_current=True)
    assert len(active_framework) == 1
    assert active_framework[0].object == "FastAPI"
    assert active_framework[0].status == "active"

    history_framework = graph_store.get_fact_history(subject="User", predicate="backend_framework")
    assert len(history_framework) == 2
    assert history_framework[0].object == "Flask"
    assert history_framework[0].status == "superseded"
    assert history_framework[1].object == "FastAPI"
    assert history_framework[1].status == "active"

    resp_fw_now = await chat_service.process_chat(ChatRequest(message="What framework do I use now?"))
    assert "FastAPI" in resp_fw_now.answer
    resp_fw_prev = await chat_service.process_chat(ChatRequest(message="What framework did I use before?"))
    assert "Flask" in resp_fw_prev.answer

    # Case 3: Relocation correction with 'but I moved to'
    ep3 = EpisodeCreate(
        session_id="retract_test", speaker="user",
        text="I live in Delhi, but I moved to Bangalore.",
        timestamp=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed3, _, _ = await episode_service.ingest_episode(ep3)
    active_city = graph_store.get_facts(subject="User", predicate="lives_in", only_current=True)
    assert len(active_city) == 1
    assert active_city[0].object == "Bangalore"
    assert active_city[0].status == "active"

    history_city = graph_store.get_fact_history(subject="User", predicate="lives_in")
    assert len(history_city) == 2
    assert history_city[0].object == "Delhi"
    assert history_city[0].status == "superseded"
    assert history_city[1].object == "Bangalore"
    assert history_city[1].status == "active"

    resp_city_now = await chat_service.process_chat(ChatRequest(message="Where do I live now?"))
    assert "Bangalore" in resp_city_now.answer
    resp_city_prev = await chat_service.process_chat(ChatRequest(message="Where did I live previously?"))
    assert "Delhi" in resp_city_prev.answer

    # Case 4: Normal sentence containing two unrelated valid facts
    ep4 = EpisodeCreate(
        session_id="multi_fact_test", speaker="user",
        text="I work at Google and I live in Seattle.",
        timestamp=datetime(2024, 4, 1, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed4, _, _ = await episode_service.ingest_episode(ep4)
    active_works = graph_store.get_facts(subject="User", predicate="works_at", only_current=True)
    active_lives = graph_store.get_facts(subject="User", predicate="lives_in", only_current=True)
    assert any(f.object == "Google" and f.status == "active" for f in active_works)
    assert any(f.object == "Seattle" and f.status == "active" for f in active_lives)

    # Case 5: Ambiguous correction that must not trigger a guessed update
    ep5 = EpisodeCreate(
        session_id="ambig_test", speaker="user",
        text="I live in Pune, wait actually maybe not.",
        timestamp=datetime(2024, 5, 1, 10, 0, tzinfo=timezone.utc)
    )
    _, confirmed5, _, _ = await episode_service.ingest_episode(ep5)
    # Must NOT have inserted Pune as an active fact
    pune_facts = [f for f in graph_store.get_facts(subject="User", predicate="lives_in") if f.object == "Pune"]
    assert len(pune_facts) == 0, f"Ambiguous retraction must not insert guessed fact! Found: {pune_facts}"
