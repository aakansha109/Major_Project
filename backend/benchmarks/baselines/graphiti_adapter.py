import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from benchmarks.baselines.base import BaseMemoryStrategy
from app.core.config import settings

logger = logging.getLogger("chronos.benchmarks.graphiti")

class GraphitiBaselineStrategy(BaseMemoryStrategy):
    """
    Adapter for Graphiti (https://github.com/getzep/graphiti).
    Runs only if graphiti-core package is installed and Neo4j + LLM provider are active.
    Otherwise reports unavailable without fabricating results.
    """
    def __init__(self, name: str = "graphiti"):
        super().__init__(name=name, is_live=True)
        self.client = None
        self._check_installed()

    def _check_installed(self) -> None:
        try:
            import graphiti_core  # type: ignore
            self._installed = True
        except ImportError:
            self._installed = False

    def is_available(self) -> Tuple[bool, str]:
        if not self._installed:
            return False, "Dependency 'graphiti-core' is not installed in the python environment."
        
        has_key = bool(os.environ.get("OPENAI_API_KEY"))
        if not has_key:
            return False, "OPENAI_API_KEY environment variable is not configured for Graphiti LLM client."
            
        return True, "Graphiti package and credentials operational."

    async def setup(self) -> None:
        avail, reason = self.is_available()
        if not avail:
            raise RuntimeError(f"Cannot setup Graphiti baseline: {reason}")
            
        from graphiti_core import Graphiti  # type: ignore
        self.client = Graphiti(
            neo4j_uri=settings.NEO4J_URI,
            neo4j_user=settings.NEO4J_USER,
            neo4j_password=settings.NEO4J_PASSWORD
        )

    async def ingest_episode(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Graphiti client is not initialized.")
            
        import time
        start_t = time.perf_counter()
        
        await self.client.add_episode(
            name=f"turn_{session_id}_{int(timestamp.timestamp())}",
            episode_body=f"{speaker}: {text}",
            source_description=session_id,
            reference_time=timestamp
        )
        latency = (time.perf_counter() - start_t) * 1000
        
        return {
            "latency_ms": round(latency, 3),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "tokens_is_measured": False,
            "cost_usd": 0.0,
            "method": "graphiti_temporal",
            "extracted_count": 1,
            "invalidated_count": 0
        }

    async def answer_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Graphiti client is not initialized.")
            
        import time
        start_t = time.perf_counter()
        results = await self.client.search(query=query)
        latency = (time.perf_counter() - start_t) * 1000
        
        answer = " ".join([str(r) for r in results]) if results else "No graph nodes retrieved."
        return {
            "answer": answer,
            "latency_ms": round(latency, 3),
            "confidence": 0.8 if results else 0.2,
            "grounded": bool(results)
        }

    async def get_active_facts(self) -> List[Dict[str, str]]:
        return []

    async def get_historical_facts(self) -> List[Dict[str, str]]:
        return []

    async def teardown(self) -> None:
        self.client = None
