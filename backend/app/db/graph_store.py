import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from app.db.neo4j import neo4j_client
from app.db.sqlite_store import sqlite_store
from app.models.fact import Fact
from app.models.episode import Episode
from app.models.retrieval import Subgraph, GraphNode, GraphEdge
from app.core.config import settings

logger = logging.getLogger("chronos.db.graph_store")

class UnifiedGraphStore:
    """
    Unified Temporal Knowledge Graph Store.
    Executes on Neo4j when available; continuously syncs and mirrors in persistent SQLite
    with strict ACID transactional guarantees, rollback support, and idempotency.
    """

    def __init__(self):
        self.sqlite = sqlite_store

    def is_neo4j_active(self) -> bool:
        return neo4j_client.is_connected()

    @contextmanager
    def transaction(self):
        """Context manager providing an atomic database transaction"""
        with self.sqlite.transaction() as conn:
            yield conn

    def find_duplicate_active_fact(
        self,
        subject: str,
        predicate: str,
        object_: str,
        conn: Optional[Any] = None
    ) -> Optional[Fact]:
        row = self.sqlite.find_duplicate_active_fact(subject, predicate, object_, conn=conn)
        if not row:
            return None
        return self._row_to_fact(row)

    def store_episode(self, episode: Episode, conn: Optional[Any] = None):
        # 1. Persistent SQLite write
        ep_dict = {
            "id": episode.id,
            "session_id": episode.session_id,
            "speaker": episode.speaker,
            "text": episode.text,
            "timestamp": episode.timestamp.isoformat(),
            "metadata": episode.metadata,
            "created_at": episode.created_at.isoformat()
        }
        self.sqlite.insert_episode(ep_dict, conn=conn)

        # 2. Neo4j graph write if connected
        if self.is_neo4j_active() and neo4j_client.driver:
            try:
                with neo4j_client.driver.session(database=settings.NEO4J_DATABASE) as session:
                    cypher = """
                    MERGE (ep:Episode {id: $id})
                    SET ep.session_id = $session_id,
                        ep.speaker = $speaker,
                        ep.text = $text,
                        ep.timestamp = datetime($timestamp),
                        ep.created_at = datetime($created_at)
                    """
                    session.run(cypher, ep_dict)
            except Exception as e:
                logger.error("Error writing episode to Neo4j: %s", e)

    def store_fact(self, fact: Fact, conn: Optional[Any] = None):
        # 1. Persistent SQLite write
        fact_dict = fact.model_dump()
        fact_dict["valid_from"] = fact.valid_from.isoformat()
        fact_dict["valid_to"] = fact.valid_to.isoformat() if fact.valid_to else None
        fact_dict["created_at"] = fact.created_at.isoformat()
        fact_dict["tx_time"] = fact.tx_time.isoformat()
        self.sqlite.insert_fact(fact_dict, conn=conn)

        # 2. Neo4j graph write
        if self.is_neo4j_active() and neo4j_client.driver:
            try:
                with neo4j_client.driver.session(database=settings.NEO4J_DATABASE) as session:
                    cypher = """
                    MERGE (s:Entity {name: $subject})
                    MERGE (o:Entity {name: $object})
                    CREATE (s)-[r:RELATION {
                        id: $id,
                        predicate: $predicate,
                        valid_from: datetime($valid_from),
                        valid_to: CASE WHEN $valid_to IS NOT NULL THEN datetime($valid_to) ELSE null END,
                        status: $status,
                        is_current: $is_current,
                        source_episode_id: $source_episode_id,
                        created_at: datetime($created_at),
                        extraction_method: $extraction_method,
                        confidence: $confidence,
                        rule_name: $rule_name,
                        tokens_used: $tokens_used,
                        estimated_cost_usd: $estimated_cost_usd,
                        raw_text: $raw_text
                    }]->(o)
                    """
                    session.run(cypher, fact_dict)

                    ep_id = fact.source_episode_id or fact.episode_id
                    if ep_id:
                        link_cypher = """
                        MATCH (ep:Episode {id: $episode_id})
                        MATCH ()-[r:RELATION {id: $fact_id}]->()
                        MERGE (ep)-[:PRODUCES]->(r)
                        """
                        session.run(link_cypher, {"episode_id": ep_id, "fact_id": fact.id})
            except Exception as e:
                logger.error("Error writing fact to Neo4j: %s", e)

    def invalidate_fact(
        self,
        fact_id: str,
        valid_to: datetime,
        superseded_by_id: Optional[str] = None,
        conn: Optional[Any] = None
    ):
        valid_to_iso = valid_to.isoformat()
        # 1. Update SQLite
        self.sqlite.update_fact_invalidation(fact_id, valid_to_iso, superseded_by_id, conn=conn)

        # 2. Update Neo4j
        if self.is_neo4j_active() and neo4j_client.driver:
            try:
                with neo4j_client.driver.session(database=settings.NEO4J_DATABASE) as session:
                    cypher = """
                    MATCH ()-[r:RELATION {id: $fact_id}]->()
                    SET r.valid_to = datetime($valid_to),
                        r.status = 'superseded',
                        r.is_current = false,
                        r.superseded_by = $superseded_by
                    """
                    session.run(cypher, {
                        "fact_id": fact_id,
                        "valid_to": valid_to_iso,
                        "superseded_by": superseded_by_id
                    })
                    if superseded_by_id:
                        supersede_cypher = """
                        MATCH ()-[old_r:RELATION {id: $fact_id}]->()
                        MATCH ()-[new_r:RELATION {id: $superseded_by}]->()
                        CREATE (new_r)-[:SUPERSEDES]->(old_r)
                        """
                        session.run(supersede_cypher, {
                            "fact_id": fact_id,
                            "superseded_by": superseded_by_id
                        })
            except Exception as e:
                logger.error("Error updating fact invalidation in Neo4j: %s", e)

    def _row_to_fact(self, r: Dict[str, Any]) -> Fact:
        status_val = r.get("status") or ("active" if r.get("is_current") else "superseded")
        is_cur_val = bool(r.get("is_current", True)) and (status_val == "active")
        return Fact(
            id=r["id"],
            subject=r["subject"],
            predicate=r["predicate"],
            object=r["object"],
            valid_from=datetime.fromisoformat(r["valid_from"]),
            valid_to=datetime.fromisoformat(r["valid_to"]) if r.get("valid_to") else None,
            status=status_val,
            is_current=is_cur_val,
            source_episode_id=r.get("source_episode_id") or r.get("episode_id"),
            created_at=datetime.fromisoformat(r["created_at"]) if r.get("created_at") else datetime.now(timezone.utc),
            extraction_method=r.get("extraction_method") or r.get("source", "rule"),
            confidence=float(r.get("confidence", 1.0)),
            rule_name=r.get("rule_name"),
            tokens_used=int(r.get("tokens_used", 0)),
            estimated_cost_usd=float(r.get("estimated_cost_usd", 0.0)),
            raw_text=r.get("raw_text"),
            superseded_by=r.get("superseded_by"),
            supersedes_fact_id=r.get("supersedes_fact_id")
        )

    def get_facts(
        self,
        as_of: Optional[datetime] = None,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_: Optional[str] = None,
        only_current: bool = False,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Fact]:
        as_of_iso = as_of.isoformat() if as_of else None
        rows = self.sqlite.get_facts(
            as_of=as_of_iso,
            subject=subject,
            predicate=predicate,
            object_=object_,
            only_current=only_current,
            status=status,
            limit=limit
        )
        return [self._row_to_fact(r) for r in rows]

    def get_active_facts_for_predicate(
        self,
        subject: str,
        predicate: str,
        conn: Optional[Any] = None
    ) -> List[Fact]:
        rows = self.sqlite.get_active_facts_for_subject_predicate(subject, predicate, conn=conn)
        return [self._row_to_fact(r) for r in rows]

    def get_episodes(self, session_id: Optional[str] = None, limit: int = 50) -> List[Episode]:
        rows = self.sqlite.get_episodes(session_id=session_id, limit=limit)
        return [
            Episode(
                id=r["id"],
                session_id=r["session_id"],
                speaker=r["speaker"],
                text=r["text"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                metadata=r["metadata"],
                created_at=datetime.fromisoformat(r["created_at"])
            )
            for r in rows
        ]

    def get_episode_by_id(self, episode_id: str) -> Optional[Episode]:
        r = self.sqlite.get_episode_by_id(episode_id)
        if not r:
            return None
        return Episode(
            id=r["id"],
            session_id=r["session_id"],
            speaker=r["speaker"],
            text=r["text"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            metadata=r["metadata"],
            created_at=datetime.fromisoformat(r["created_at"])
        )

    def get_facts_by_episode_id(self, episode_id: str) -> List[Fact]:
        rows = self.sqlite.get_facts_by_episode_id(episode_id)
        return [self._row_to_fact(r) for r in rows]

    def get_fact_history(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        limit: int = 100
    ) -> List[Fact]:
        rows = self.sqlite.get_fact_history(subject=subject, predicate=predicate, limit=limit)
        return [self._row_to_fact(r) for r in rows]

    def get_subgraph_for_entities(
        self,
        entity_names: List[str],
        as_of: Optional[datetime] = None,
        depth: int = 1
    ) -> Subgraph:
        if not entity_names:
            return Subgraph(nodes=[], edges=[])

        relevant_facts: List[Fact] = []
        for ent in entity_names:
            facts_as_sub = self.get_facts(as_of=as_of, subject=ent, limit=50)
            relevant_facts.extend(facts_as_sub)

            with self.sqlite._get_connection() as conn:
                cursor = conn.cursor()
                if as_of:
                    cursor.execute("""
                        SELECT * FROM facts 
                        WHERE LOWER(object) = LOWER(?)
                        AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)
                        LIMIT 50
                    """, (ent, as_of.isoformat(), as_of.isoformat()))
                else:
                    cursor.execute("""
                        SELECT * FROM facts 
                        WHERE LOWER(object) = LOWER(?)
                        LIMIT 50
                    """, (ent,))
                for r in cursor.fetchall():
                    row_dict = dict(r)
                    if not any(f.id == row_dict["id"] for f in relevant_facts):
                        relevant_facts.append(self._row_to_fact(row_dict))

        node_dict = {}
        edge_list = []
        for f in relevant_facts:
            if f.subject not in node_dict:
                node_dict[f.subject] = GraphNode(id=f.subject, label=f.subject, type="entity")
            if f.object not in node_dict:
                node_dict[f.object] = GraphNode(id=f.object, label=f.object, type="entity")
            edge_list.append(GraphEdge(
                source=f.subject,
                target=f.object,
                label=f.predicate,
                valid_from=f.valid_from.isoformat(),
                valid_to=f.valid_to.isoformat() if f.valid_to else None,
                is_current=f.is_current,
                confidence=f.confidence,
                source_type=f.extraction_method
            ))

        return Subgraph(nodes=list(node_dict.values()), edges=edge_list)

    def get_full_graph(self, as_of: Optional[datetime] = None, limit: int = 250) -> Subgraph:
        facts = self.get_facts(as_of=as_of, limit=limit)
        node_dict = {}
        edges = []
        for f in facts:
            if f.subject not in node_dict:
                node_dict[f.subject] = GraphNode(id=f.subject, label=f.subject, type="entity")
            if f.object not in node_dict:
                node_dict[f.object] = GraphNode(id=f.object, label=f.object, type="entity")
            edges.append(GraphEdge(
                id=f.id,
                fact_id=f.id,
                source=f.subject,
                target=f.object,
                label=f.predicate,
                valid_from=f.valid_from.isoformat(),
                valid_to=f.valid_to.isoformat() if f.valid_to else None,
                is_current=f.is_current,
                status="active" if f.is_current else "superseded",
                confidence=f.confidence,
                source_type=f.extraction_method,
                source_episode_id=f.source_episode_id
            ))
        return Subgraph(nodes=list(node_dict.values()), edges=edges)

    def get_status(self) -> Dict[str, Any]:
        neo4j_ok = self.is_neo4j_active()
        stats = self.sqlite.count_metrics()
        return {
            "graph_backend": "neo4j" if neo4j_ok else "sqlite_resilient",
            "neo4j_connected": neo4j_ok,
            "neo4j_uri": settings.NEO4J_URI,
            "metrics": stats
        }

    def reset_database(self):
        self.sqlite.clear()
        if self.is_neo4j_active() and neo4j_client.driver:
            try:
                with neo4j_client.driver.session(database=settings.NEO4J_DATABASE) as session:
                    session.run("MATCH (n) DETACH DELETE n")
            except Exception as e:
                logger.error("Error clearing Neo4j database: %s", e)

graph_store = UnifiedGraphStore()
