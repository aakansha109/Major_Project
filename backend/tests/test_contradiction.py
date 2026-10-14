import pytest
from datetime import datetime, timezone
from app.models.fact import Fact
from app.services.contradiction_service import contradiction_service
from app.db.graph_store import graph_store

def test_contradiction_supersession():
    graph_store.reset_database()

    # Fact 1: Alice lived in Seattle in 2020
    fact1 = Fact(
        subject="Alice",
        predicate="lives_in",
        object="Seattle",
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        is_current=True
    )
    graph_store.store_fact(fact1)

    # Verify fact1 is active
    active = graph_store.get_active_facts_for_predicate("Alice", "lives_in")
    assert len(active) == 1
    assert active[0].object == "Seattle"

    # Fact 2: Alice moved to London in 2023
    fact2 = Fact(
        subject="Alice",
        predicate="lives_in",
        object="London",
        valid_from=datetime(2023, 1, 1, tzinfo=timezone.utc),
        is_current=True
    )

    resolved_fact2, invalidated, _ = contradiction_service.resolve_contradictions(fact2)
    graph_store.store_fact(resolved_fact2)

    # Verify fact1 was invalidated
    assert len(invalidated) == 1
    assert invalidated[0].id == fact1.id
    assert resolved_fact2.supersedes_fact_id == fact1.id

    # Verify currently active facts
    current_active = graph_store.get_active_facts_for_predicate("Alice", "lives_in")
    assert len(current_active) == 1
    assert current_active[0].object == "London"

    # Point-in-time check: In 2021, Alice lived in Seattle!
    facts_2021 = graph_store.get_facts(
        as_of=datetime(2021, 6, 1, tzinfo=timezone.utc),
        subject="Alice",
        predicate="lives_in"
    )
    assert len(facts_2021) == 1
    assert facts_2021[0].object == "Seattle"

    # Point-in-time check: In 2024, Alice lived in London!
    facts_2024 = graph_store.get_facts(
        as_of=datetime(2024, 6, 1, tzinfo=timezone.utc),
        subject="Alice",
        predicate="lives_in"
    )
    assert len(facts_2024) == 1
    assert facts_2024[0].object == "London"
