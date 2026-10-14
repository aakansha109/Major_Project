import logging
from typing import List, Tuple, Optional, Any
from datetime import datetime
from app.models.fact import Fact
from app.db.graph_store import graph_store

logger = logging.getLogger("chronos.services.contradiction")

# Functional predicates that permit at most ONE active value per subject at any single point in time
FUNCTIONAL_PREDICATES = {
    "backend_framework",
    "frontend_framework",
    "database_used",
    "uses_database",
    "database",
    "cloud_provider",
    "primary_language",
    "office_location",
    "status",
    "lives_in",
    "resides_in",
    "location",
    "works_at",
    "employed_by",
    "holds_role",
    "role_title",
    "marital_status",
    "married_to",
    "current_device",
    "primary_os",
    "leads_project",
    "graduated_from"
}

# Multi-valued predicates that allow multiple co-existing active facts
MULTI_VALUED_PREDICATES = {
    "likes",
    "prefers",
    "interested_in",
    "skills",
    "knows",
    "speaks_language",
    "uses_language",
    "uses_hardware",
    "uses_tool",
    "maintains_repo",
    "parent_of",
    "hobby",
    "visited",
    "contributes_to"
}

class ContradictionService:
    """
    Detects and resolves temporal contradictions when incoming facts conflict
    with existing active facts in memory.
    """

    def resolve_contradictions(
        self,
        new_fact: Fact,
        conn: Optional[Any] = None
    ) -> Tuple[Fact, List[Fact], bool]:
        """
        Evaluates new_fact against active facts for the subject and predicate.
        Returns:
            (processed_fact, list_of_invalidated_facts, is_duplicate)
        """
        predicate_norm = new_fact.predicate.lower().strip()
        is_functional = predicate_norm in FUNCTIONAL_PREDICATES

        # Handle explicit negation (e.g. "I do not use Flask anymore")
        if new_fact.extraction_method == "negation":
            existing_active = graph_store.get_active_facts_for_predicate(
                new_fact.subject,
                new_fact.predicate,
                conn=conn
            )
            invalidated = []
            for old_fact in existing_active:
                if old_fact.object.lower().strip() == new_fact.object.lower().strip():
                    graph_store.invalidate_fact(
                        fact_id=old_fact.id,
                        valid_to=new_fact.valid_from,
                        superseded_by_id=new_fact.id,
                        conn=conn
                    )
                    old_fact.valid_to = new_fact.valid_from
                    old_fact.status = "superseded"
                    old_fact.is_current = False
                    invalidated.append(old_fact)
            # The negation fact itself is an invalidation marker
            new_fact.status = "superseded"
            new_fact.is_current = False
            new_fact.valid_to = new_fact.valid_from
            return new_fact, invalidated, False

        # Check for exact duplicate active fact (Idempotency)
        existing_dup = graph_store.find_duplicate_active_fact(
            subject=new_fact.subject,
            predicate=new_fact.predicate,
            object_=new_fact.object,
            conn=conn
        )
        if existing_dup:
            logger.info("Duplicate active fact detected for (%s, %s, %s); skipping duplicate creation.",
                        new_fact.subject, new_fact.predicate, new_fact.object)
            return existing_dup, [], True

        # Non-functional / multi-valued predicates (e.g. 'skills', 'likes') do NOT conflict
        if not is_functional:
            return new_fact, [], False

        # Functional predicate update check
        existing_active = graph_store.get_active_facts_for_predicate(
            new_fact.subject,
            new_fact.predicate,
            conn=conn
        )
        invalidated: List[Fact] = []

        for old_fact in existing_active:
            if old_fact.id == new_fact.id:
                continue

            # If the object is different
            if old_fact.object.lower().strip() != new_fact.object.lower().strip():
                # Temporal Ordering Check:
                # Case A: New fact is chronologically newer or simultaneous -> Supersedes old fact
                if new_fact.valid_from >= old_fact.valid_from:
                    logger.info(
                        "Temporal contradiction resolved: (%s %s %s) supersedes (%s %s %s)",
                        new_fact.subject, new_fact.predicate, new_fact.object,
                        old_fact.subject, old_fact.predicate, old_fact.object
                    )
                    graph_store.invalidate_fact(
                        fact_id=old_fact.id,
                        valid_to=new_fact.valid_from,
                        superseded_by_id=new_fact.id,
                        conn=conn
                    )
                    old_fact.valid_to = new_fact.valid_from
                    old_fact.status = "superseded"
                    old_fact.is_current = False
                    old_fact.superseded_by = new_fact.id
                    invalidated.append(old_fact)

                    new_fact.supersedes_fact_id = old_fact.id
                else:
                    # Case B: New fact is a historical backfill (older than current active fact)
                    # Do NOT invalidate the newer active fact! Bound the historical fact's validity interval.
                    logger.info(
                        "Historical backfill detected: (%s %s %s) valid until newer fact (%s) at %s",
                        new_fact.subject, new_fact.predicate, new_fact.object,
                        old_fact.object, old_fact.valid_from
                    )
                    new_fact.valid_to = old_fact.valid_from
                    new_fact.status = "superseded"
                    new_fact.is_current = False
                    new_fact.superseded_by = old_fact.id

        return new_fact, invalidated, False

contradiction_service = ContradictionService()
