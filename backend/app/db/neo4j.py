import logging
from typing import Optional, Dict, Any
from neo4j import GraphDatabase, Driver
from app.core.config import settings

logger = logging.getLogger("chronos.db.neo4j")

class Neo4jClient:
    def __init__(self):
        self.driver: Optional[Driver] = None
        self._is_connected = False

    def connect(self) -> bool:
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            self._is_connected = True
            logger.info("Successfully connected to Neo4j at %s", settings.NEO4J_URI)
            self.init_schema()
            return True
        except Exception as e:
            logger.warning("Could not connect to Neo4j (%s): %s. Operating in local resilient mode.", settings.NEO4J_URI, e)
            self._is_connected = False
            self.driver = None
            return False

    def is_connected(self) -> bool:
        if not self.driver:
            return False
        try:
            self.driver.verify_connectivity()
            self._is_connected = True
            return True
        except Exception:
            self._is_connected = False
            return False

    def init_schema(self):
        """Create constraints and indexes for high-performance temporal querying"""
        if not self.driver:
            return
        queries = [
            "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;",
            "CREATE CONSTRAINT episode_id_unique IF NOT EXISTS FOR (ep:Episode) REQUIRE ep.id IS UNIQUE;",
            "CREATE CONSTRAINT fact_id_unique IF NOT EXISTS FOR ()-[r:RELATION]-() REQUIRE r.id IS UNIQUE;"
        ]
        try:
            with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                for q in queries:
                    try:
                        session.run(q)
                    except Exception as err:
                        logger.debug("Constraint creation notice: %s", err)
        except Exception as e:
            logger.warning("Failed to initialize Neo4j constraints: %s", e)

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass
            self.driver = None
            self._is_connected = False

neo4j_client = Neo4jClient()
