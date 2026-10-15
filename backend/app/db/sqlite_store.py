import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger("chronos.db.sqlite")

class SQLiteStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path(settings.LOCAL_DATA_DIR)
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "chronos.db")
        else:
            self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def transaction(self):
        """Transactional context manager guaranteeing ACID consistency and rollback on failure"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE TRANSACTION;")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Transaction failed and was rolled back: %s", e)
            raise
        finally:
            conn.close()

    def _init_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Episodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_time ON episodes(timestamp);")

            # Facts table with explicit status and provenance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    is_current INTEGER NOT NULL DEFAULT 1,
                    source_episode_id TEXT,
                    created_at TEXT NOT NULL,
                    extraction_method TEXT NOT NULL DEFAULT 'rule',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    rule_name TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    estimated_cost_usd REAL DEFAULT 0.0,
                    raw_text TEXT,
                    superseded_by TEXT,
                    supersedes_fact_id TEXT
                );
            """)

            # Auto-migrate existing tables if missing newly added columns
            cursor.execute("PRAGMA table_info(facts);")
            cols = {row[1] for row in cursor.fetchall()}
            if "status" not in cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN status TEXT NOT NULL DEFAULT 'active';")
            if "source_episode_id" not in cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN source_episode_id TEXT;")
            if "extraction_method" not in cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'rule';")
            if "created_at" not in cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN created_at TEXT NOT NULL DEFAULT '';")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_sub_pred ON facts(subject, predicate);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_temporal ON facts(valid_from, valid_to);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_current ON facts(is_current);")
            
            # Entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    name TEXT PRIMARY KEY,
                    type TEXT DEFAULT 'entity',
                    first_seen TEXT,
                    last_seen TEXT
                );
            """)
            conn.commit()

    def insert_episode(self, ep_dict: Dict[str, Any], conn: Optional[sqlite3.Connection] = None):
        own_conn = False
        if conn is None:
            conn = self._get_connection()
            own_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO episodes (id, session_id, speaker, text, timestamp, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ep_dict["id"],
                ep_dict["session_id"],
                ep_dict["speaker"],
                ep_dict["text"],
                ep_dict["timestamp"],
                json.dumps(ep_dict.get("metadata", {})),
                ep_dict.get("created_at", datetime.now(timezone.utc).isoformat())
            ))
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_episodes(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    "SELECT * FROM episodes WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (session_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM episodes ORDER BY timestamp ASC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
                results.append(item)
            return results

    def get_episode_by_id(self, episode_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
            return item

    def get_facts_by_episode_id(self, episode_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM facts WHERE source_episode_id = ? OR episode_id = ? ORDER BY created_at ASC",
                (episode_id, episode_id)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_fact_history(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM facts WHERE 1=1"
            params = []
            if subject:
                query += " AND LOWER(subject) = LOWER(?)"
                params.append(subject)
            if predicate:
                query += " AND LOWER(predicate) = LOWER(?)"
                params.append(predicate)
            query += " ORDER BY valid_from ASC, created_at ASC LIMIT ?"
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def find_duplicate_active_fact(
        self,
        subject: str,
        predicate: str,
        object_: str,
        conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Dict[str, Any]]:
        """Checks if an identical active fact already exists to prevent duplicate insertion"""
        own_conn = False
        if conn is None:
            conn = self._get_connection()
            own_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM facts
                WHERE LOWER(subject) = LOWER(?)
                  AND LOWER(predicate) = LOWER(?)
                  AND LOWER(object) = LOWER(?)
                  AND status = 'active'
                  AND is_current = 1
                LIMIT 1
            """, (subject, predicate, object_))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            if own_conn:
                conn.close()

    def insert_fact(self, fact_dict: Dict[str, Any], conn: Optional[sqlite3.Connection] = None):
        own_conn = False
        if conn is None:
            conn = self._get_connection()
            own_conn = True
        try:
            cursor = conn.cursor()
            status = fact_dict.get("status", "active")
            is_current = 1 if (status == "active" and not fact_dict.get("valid_to")) else 0
            ep_id = fact_dict.get("source_episode_id") or fact_dict.get("episode_id")
            time_val = fact_dict.get("created_at") or fact_dict.get("tx_time") or datetime.now(timezone.utc).isoformat()
            source_val = fact_dict.get("extraction_method") or fact_dict.get("source", "rule")
            
            cursor.execute("""
                INSERT OR REPLACE INTO facts (
                    id, subject, predicate, object, valid_from, valid_to, status,
                    is_current, source_episode_id, episode_id, created_at, tx_time,
                    extraction_method, source, confidence, rule_name, tokens_used,
                    estimated_cost_usd, raw_text, superseded_by, supersedes_fact_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact_dict["id"],
                fact_dict["subject"],
                fact_dict["predicate"],
                fact_dict["object"],
                fact_dict["valid_from"],
                fact_dict.get("valid_to"),
                status,
                is_current,
                ep_id,
                ep_id,
                time_val,
                time_val,
                source_val,
                source_val,
                fact_dict.get("confidence", 1.0),
                fact_dict.get("rule_name"),
                fact_dict.get("tokens_used", 0),
                fact_dict.get("estimated_cost_usd", 0.0),
                fact_dict.get("raw_text"),
                fact_dict.get("superseded_by"),
                fact_dict.get("supersedes_fact_id")
            ))
            # Track entities
            for ent in [fact_dict["subject"], fact_dict["object"]]:
                cursor.execute("""
                    INSERT OR REPLACE INTO entities (name, type, first_seen, last_seen)
                    VALUES (?, 'entity', COALESCE((SELECT first_seen FROM entities WHERE name = ?), ?), ?)
                """, (ent, ent, fact_dict["valid_from"], fact_dict["valid_from"]))
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def update_fact_invalidation(
        self,
        fact_id: str,
        valid_to: str,
        superseded_by: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None
    ):
        own_conn = False
        if conn is None:
            conn = self._get_connection()
            own_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE facts
                SET valid_to = ?, status = 'superseded', is_current = 0, superseded_by = ?
                WHERE id = ?
            """, (valid_to, superseded_by, fact_id))
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_facts(
        self,
        as_of: Optional[str] = None,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_: Optional[str] = None,
        only_current: bool = False,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []

            if subject:
                conditions.append("LOWER(subject) = LOWER(?)")
                params.append(subject)
            if predicate:
                conditions.append("LOWER(predicate) = LOWER(?)")
                params.append(predicate)
            if object_:
                conditions.append("LOWER(object) = LOWER(?)")
                params.append(object_)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if only_current:
                conditions.append("status = 'active' AND is_current = 1")
            if as_of:
                # Point-in-time logic: valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)
                conditions.append("valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)")
                params.extend([as_of, as_of])

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM facts{where_clause} ORDER BY valid_from DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_active_facts_for_subject_predicate(
        self,
        subject: str,
        predicate: str,
        conn: Optional[sqlite3.Connection] = None
    ) -> List[Dict[str, Any]]:
        own_conn = False
        if conn is None:
            conn = self._get_connection()
            own_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM facts
                WHERE LOWER(subject) = LOWER(?)
                  AND LOWER(predicate) = LOWER(?)
                  AND status = 'active'
                  AND is_current = 1
                ORDER BY valid_from DESC
            """, (subject, predicate))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            if own_conn:
                conn.close()

    def count_metrics(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM episodes")
            ep_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM facts")
            fact_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM facts WHERE status = 'active' AND is_current = 1")
            active_facts_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM facts WHERE status = 'superseded' OR is_current = 0 OR valid_to IS NOT NULL")
            superseded_facts_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT entity) FROM (
                    SELECT subject AS entity FROM facts
                    UNION
                    SELECT object AS entity FROM facts
                )
            """)
            ent_count = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM facts WHERE extraction_method IN ('rule', 'hybrid_rule')")
            rule_ext_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM facts WHERE extraction_method IN ('llm', 'hybrid_llm_fallback')")
            llm_ext_count = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(tokens_used), SUM(estimated_cost_usd) FROM facts")
            tok_row = cursor.fetchone()
            total_tokens = tok_row[0] or 0
            total_cost = tok_row[1] or 0.0

            return {
                "episode_count": ep_count,
                "fact_count": fact_count,
                "active_facts_count": active_facts_count,
                "superseded_facts_count": superseded_facts_count,
                "extraction_calls_count": ep_count,
                "entity_count": ent_count,
                "rule_extractions_count": rule_ext_count,
                "llm_extractions_count": llm_ext_count,
                "total_tokens_used": total_tokens,
                "total_cost_usd": round(total_cost, 6)
            }

    def clear(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM episodes;")
            cursor.execute("DELETE FROM facts;")
            cursor.execute("DELETE FROM entities;")
            conn.commit()

sqlite_store = SQLiteStore()
