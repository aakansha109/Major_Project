import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from benchmarks.baselines.base import BaseMemoryStrategy

logger = logging.getLogger("chronos.benchmarks.mem0")

class Mem0BaselineStrategy(BaseMemoryStrategy):
    """
    Adapter for Mem0 (https://github.com/mem0ai/mem0).
    Runs only if mem0 package is installed and an API key is available.
    Otherwise reports unavailable without fabricating results.
    """
    def __init__(self, name: str = "mem0"):
        super().__init__(name=name, is_live=True)
        self.mem0_client = None
        self._check_installed()

    def _check_installed(self) -> None:
        try:
            import mem0  # type: ignore
            self._installed = True
        except ImportError:
            self._installed = False

    def is_available(self) -> Tuple[bool, str]:
        if not self._installed:
            return False, "Dependency 'mem0ai' is not installed in the python environment."
        
        has_key = bool(os.environ.get("MEM0_API_KEY") or os.environ.get("OPENAI_API_KEY"))
        if not has_key:
            return False, "MEM0_API_KEY or OPENAI_API_KEY environment variable is not configured."
            
        return True, "Mem0 client library and provider credentials verified."

    async def setup(self) -> None:
        avail, reason = self.is_available()
        if not avail:
            raise RuntimeError(f"Cannot setup Mem0 baseline: {reason}")
        
        from mem0 import Memory  # type: ignore
        self.mem0_client = Memory()

    async def ingest_episode(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        if not self.mem0_client:
            raise RuntimeError("Mem0 is not initialized.")
        
        # Real mem0 ingestion
        import time
        start_t = time.perf_counter()
        res = self.mem0_client.add(
            messages=[{"role": speaker.lower(), "content": text}],
            user_id=session_id
        )
        latency = (time.perf_counter() - start_t) * 1000
        
        return {
            "latency_ms": round(latency, 3),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "tokens_is_measured": False,
            "cost_usd": 0.0,
            "method": "mem0_hybrid",
            "extracted_count": len(res) if isinstance(res, list) else 1,
            "invalidated_count": 0
        }

    async def answer_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.mem0_client:
            raise RuntimeError("Mem0 is not initialized.")
            
        import time
        start_t = time.perf_counter()
        memories = self.mem0_client.search(query=query, user_id=session_id)
        latency = (time.perf_counter() - start_t) * 1000
        
        answer = " ".join([m.get("memory", "") for m in memories]) if memories else "No relevant memories found."
        return {
            "answer": answer,
            "latency_ms": round(latency, 3),
            "confidence": 0.8 if memories else 0.2,
            "grounded": bool(memories)
        }

    async def get_active_facts(self) -> List[Dict[str, str]]:
        return []

    async def get_historical_facts(self) -> List[Dict[str, str]]:
        return []

    async def teardown(self) -> None:
        self.mem0_client = None
