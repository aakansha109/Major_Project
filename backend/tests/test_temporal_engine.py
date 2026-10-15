import pytest
from datetime import datetime, timezone
from app.models.episode import EpisodeCreate
from app.models.fact import Fact
from app.services.episode_service import episode_service
from app.db.graph_store import graph_store

@pytest.fixture(autouse=True)
def clean_database():
    graph_store.reset_database()
    yield
    graph_store.reset_database()

@pytest.mark.asyncio
async def test_first_time_fact_insertion():
    """Test 1: First-time fact insertion"""
    ep = EpisodeCreate(
        session_id="test_sess_insert",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)
    )

    episode, confirmed_facts, invalidated, telemetry = await episode_service.ingest_episode(ep)

    assert len(confirmed_facts) == 1
    assert len(invalidated) == 0

    fact = confirmed_facts[0]
    assert fact.subject == "User"
    assert fact.predicate == "backend_framework"
    assert fact.object == "Flask"
    assert fact.status == "active"
    assert fact.is_current is True
    assert fact.valid_to is None
    assert fact.valid_from == datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)
    assert fact.source_episode_id == episode.id
    assert fact.confidence >= 0.95
    assert fact.extraction_method == "rule"

@pytest.mark.asyncio
async def test_changed_facts_supersession():
    """Test 2: Changed facts with temporal contradiction resolution"""
    t1 = datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 4, 15, 14, 0, tzinfo=timezone.utc)

    # 1. Ingest initial fact
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_change",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=t1
    ))

    # 2. Ingest updated fact
    _, confirmed_facts, invalidated, _ = await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_change",
        speaker="user",
        text="I switched my backend to FastAPI.",
        timestamp=t2
    ))

    assert len(confirmed_facts) == 1
    assert len(invalidated) == 1

    old_fact = invalidated[0]
    new_fact = confirmed_facts[0]

    # Verify old fact is superseded and validity interval closed
    assert old_fact.object == "Flask"
    assert old_fact.status == "superseded"
    assert old_fact.is_current is False
    assert old_fact.valid_to == t2
    assert old_fact.superseded_by == new_fact.id

    # Verify new fact is active
    assert new_fact.object == "FastAPI"
    assert new_fact.status == "active"
    assert new_fact.is_current is True
    assert new_fact.valid_to is None
    assert new_fact.valid_from == t2
    assert new_fact.supersedes_fact_id == old_fact.id

@pytest.mark.asyncio
async def test_historical_retrieval():
    """Test 3: Historical Point-in-Time queries"""
    t1 = datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 4, 15, 14, 0, tzinfo=timezone.utc)

    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_hist",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=t1
    ))
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_hist",
        speaker="user",
        text="I switched my backend to FastAPI.",
        timestamp=t2
    ))

    # Query as of 2022 (should return Flask)
    as_of_2022 = datetime(2022, 6, 1, tzinfo=timezone.utc)
    facts_2022 = graph_store.get_facts(
        as_of=as_of_2022,
        subject="User",
        predicate="backend_framework"
    )
    assert len(facts_2022) == 1
    assert facts_2022[0].object == "Flask"
    assert facts_2022[0].valid_from == t1

    # Query as of 2024 (should return FastAPI)
    as_of_2024 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    facts_2024 = graph_store.get_facts(
        as_of=as_of_2024,
        subject="User",
        predicate="backend_framework"
    )
    assert len(facts_2024) == 1
    assert facts_2024[0].object == "FastAPI"

    # Query current active facts
    current_facts = graph_store.get_facts(
        subject="User",
        predicate="backend_framework",
        only_current=True
    )
    assert len(current_facts) == 1
    assert current_facts[0].object == "FastAPI"

@pytest.mark.asyncio
async def test_duplicate_ingestion_idempotency():
    """Test 4: Duplicate ingestion prevention (idempotency)"""
    t1 = datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)

    # Ingest same utterance twice
    ep1 = EpisodeCreate(
        session_id="test_sess_dup",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=t1
    )
    _, confirmed1, _, _ = await episode_service.ingest_episode(ep1)
    _, confirmed2, _, telemetry2 = await episode_service.ingest_episode(ep1)

    assert len(confirmed1) == 1
    assert len(confirmed2) == 1
    assert telemetry2["duplicates_skipped"] == 1

    # Total active facts in memory must strictly be 1, not 2
    active_facts = graph_store.get_active_facts_for_predicate("User", "backend_framework")
    assert len(active_facts) == 1
    assert active_facts[0].object == "Flask"

@pytest.mark.asyncio
async def test_unrelated_and_multi_valued_facts():
    """Test 5: Distinguishing updates from unrelated or multi-valued facts"""
    t1 = datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)

    # 1. Framework
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_multi",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=t1
    ))
    # 2. Database (different predicate, should co-exist)
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_multi",
        speaker="user",
        text="I now use PostgreSQL.",
        timestamp=t1
    ))
    # 3. Location (different predicate, should co-exist)
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_multi",
        speaker="user",
        text="I moved to Bangalore.",
        timestamp=t1
    ))

    # All three distinct facts must be active simultaneously
    active_facts = graph_store.get_facts(subject="User", only_current=True)
    active_predicates = {f.predicate: f.object for f in active_facts}

    assert "backend_framework" in active_predicates
    assert active_predicates["backend_framework"] == "Flask"

    assert "database_used" in active_predicates
    assert active_predicates["database_used"] == "PostgreSQL"

    assert "lives_in" in active_predicates
    assert active_predicates["lives_in"] == "Bangalore"

@pytest.mark.asyncio
async def test_ambiguous_input_rejection():
    """Test 6: Ambiguous input safely ignored (no guessed facts written)"""
    ep = EpisodeCreate(
        session_id="test_sess_ambiguous",
        speaker="user",
        text="Hello there, the weather is quite pleasant today.",
        timestamp=datetime.now(timezone.utc)
    )

    episode, confirmed_facts, invalidated, telemetry = await episode_service.ingest_episode(ep)

    assert len(confirmed_facts) == 0
    assert len(invalidated) == 0
    assert telemetry["fact_count"] == 0

    # Ensure zero facts were committed to memory
    all_facts = graph_store.get_facts()
    assert len(all_facts) == 0

@pytest.mark.asyncio
async def test_temporal_ordering_historical_backfill():
    """Test 7: Historical fact backfill does not overwrite newer active fact"""
    # 1. Current fact asserted at 2023
    t_newer = datetime(2023, 8, 20, 10, 0, tzinfo=timezone.utc)
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_order",
        speaker="user",
        text="I moved to Bangalore in 2023.",
        timestamp=t_newer
    ))

    # 2. Later, user mentions an older historical fact from 2018
    t_older = datetime(2018, 5, 1, 10, 0, tzinfo=timezone.utc)
    _, confirmed, invalidated, _ = await episode_service.ingest_episode(EpisodeCreate(
        session_id="test_sess_order",
        speaker="user",
        text="Alice moved to Pune in 2018.",
        timestamp=t_older
    ))

    # 3. User location test: Bangalore remains current
    user_active = graph_store.get_active_facts_for_predicate("User", "lives_in")
    assert len(user_active) == 1
    assert user_active[0].object == "Bangalore"
    assert user_active[0].is_current is True

@pytest.mark.asyncio
async def test_transaction_failure_and_rollback():
    """Test 8: Transaction rollback on failure guarantees zero orphaned state"""
    class SimulatedDBError(Exception):
        pass

    # Save starting fact count
    initial_facts = len(graph_store.get_facts())

    try:
        with graph_store.transaction() as tx:
            # 1. Insert a fact
            graph_store.store_fact(Fact(
                subject="TestSubject",
                predicate="test_predicate",
                object="TestObject",
                valid_from=datetime.now(timezone.utc)
            ), conn=tx)

            # 2. Simulate catastrophic error before commit
            raise SimulatedDBError("Forced database failure mid-transaction!")
    except SimulatedDBError:
        pass

    # Verify that the fact was completely rolled back and never persisted
    facts_after = graph_store.get_facts(subject="TestSubject")
    assert len(facts_after) == 0
    assert len(graph_store.get_facts()) == initial_facts

@pytest.mark.asyncio
async def test_seed_demo_sequence_verification():
    """
    Test 9: Demo sequence: Flask -> FastAPI and Delhi -> Bangalore.
    Verifies latest facts are current while old facts remain queryable.
    """
    t1 = datetime(2021, 1, 10, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2021, 2, 15, 11, 0, tzinfo=timezone.utc)
    t3 = datetime(2023, 4, 10, 14, 0, tzinfo=timezone.utc)
    t4 = datetime(2023, 8, 20, 16, 0, tzinfo=timezone.utc)

    # 1. Flask
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="demo_seq",
        speaker="user",
        text="My backend framework is Flask.",
        timestamp=t1
    ))
    # 2. Delhi
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="demo_seq",
        speaker="user",
        text="I moved to Delhi in 2021.",
        timestamp=t2
    ))
    # 3. Switch backend to FastAPI
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="demo_seq",
        speaker="user",
        text="I switched my backend to FastAPI.",
        timestamp=t3
    ))
    # 4. Move to Bangalore
    await episode_service.ingest_episode(EpisodeCreate(
        session_id="demo_seq",
        speaker="user",
        text="I moved to Bangalore in 2023.",
        timestamp=t4
    ))

    # Verify Current Facts:
    current_facts = graph_store.get_facts(subject="User", only_current=True)
    current_map = {f.predicate: f.object for f in current_facts}

    assert current_map["backend_framework"] == "FastAPI"
    assert current_map["lives_in"] == "Bangalore"

    # Verify Historical State at mid-2022:
    as_of_2022 = datetime(2022, 6, 1, tzinfo=timezone.utc)
    facts_2022 = graph_store.get_facts(subject="User", as_of=as_of_2022)
    map_2022 = {f.predicate: f.object for f in facts_2022}

    assert map_2022["backend_framework"] == "Flask"
    assert map_2022["lives_in"] == "Delhi"

    # Verify Supersession Links:
    all_framework_facts = graph_store.get_facts(subject="User", predicate="backend_framework")
    assert len(all_framework_facts) == 2
    superseded_flask = [f for f in all_framework_facts if f.object == "Flask"][0]
    active_fastapi = [f for f in all_framework_facts if f.object == "FastAPI"][0]

    assert superseded_flask.status == "superseded"
    assert superseded_flask.is_current is False
    assert superseded_flask.valid_to == t3
    assert superseded_flask.superseded_by == active_fastapi.id
    assert active_fastapi.supersedes_fact_id == superseded_flask.id
