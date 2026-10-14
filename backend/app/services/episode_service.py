import logging
from typing import Dict, Any, List, Tuple, Optional
from app.models.episode import Episode, EpisodeCreate
from app.models.fact import Fact
from app.db.graph_store import graph_store
from app.services.extraction_service import extraction_service
from app.services.contradiction_service import contradiction_service

logger = logging.getLogger("chronos.services.episode")

class EpisodeService:
    async def ingest_episode(self, ep_create: EpisodeCreate) -> Tuple[Episode, List[Fact], List[Fact], Dict[str, Any]]:
        """
        Full atomic ingestion pipeline:
        1. Parse & validate episode
        2. Extract facts via deterministic rules first (or LLM fallback)
        3. Transactionally:
           a. Persist episode node with provenance
           b. Evaluate contradiction / supersession / duplicates against active facts
           c. Invalidate conflicting historical facts
           d. Store new facts with bi-temporal validity bounds
        4. Return episode, confirmed facts, invalidated facts, and telemetry
        """
        episode = Episode(
            session_id=ep_create.session_id,
            speaker=ep_create.speaker,
            text=ep_create.text,
            timestamp=ep_create.timestamp,
            metadata=ep_create.metadata
        )

        # 1. Extract facts outside transaction (computation & parsing)
        extracted_facts, telemetry = await extraction_service.extract_facts(episode)

        confirmed_facts: List[Fact] = []
        all_invalidated: List[Fact] = []
        duplicates_count = 0

        # 2. Execute persistence and contradiction resolution inside atomic transaction
        with graph_store.transaction() as tx:
            # a. Store episode node
            graph_store.store_episode(episode, conn=tx)

            # b. Process each fact
            for fact in extracted_facts:
                fact.source_episode_id = episode.id
                fact.episode_id = episode.id

                # Resolve contradiction / check idempotency
                resolved_fact, invalidated, is_duplicate = contradiction_service.resolve_contradictions(
                    fact,
                    conn=tx
                )
                all_invalidated.extend(invalidated)

                if is_duplicate:
                    duplicates_count += 1
                    confirmed_facts.append(resolved_fact)
                    continue

                # Store newly resolved fact
                graph_store.store_fact(resolved_fact, conn=tx)
                confirmed_facts.append(resolved_fact)

        telemetry["contradictions_resolved"] = len(all_invalidated)
        telemetry["facts_stored"] = len(confirmed_facts) - duplicates_count
        telemetry["duplicates_skipped"] = duplicates_count

        return episode, confirmed_facts, all_invalidated, telemetry

    def get_session_episodes(self, session_id: str, limit: int = 50) -> List[Episode]:
        return graph_store.get_episodes(session_id=session_id, limit=limit)

    def get_all_episodes(self, limit: int = 100) -> List[Episode]:
        return graph_store.get_episodes(session_id=None, limit=limit)

    def get_episode_by_id(self, episode_id: str) -> Optional[Episode]:
        return graph_store.get_episode_by_id(episode_id)

    def get_episode_with_facts(self, episode_id: str) -> Optional[Dict[str, Any]]:
        ep = graph_store.get_episode_by_id(episode_id)
        if not ep:
            return None
        facts = graph_store.get_facts_by_episode_id(episode_id)
        return {
            "episode": ep,
            "facts": facts,
            "fact_count": len(facts)
        }

episode_service = EpisodeService()

