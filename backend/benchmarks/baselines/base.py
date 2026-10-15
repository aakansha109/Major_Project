from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

class BaseMemoryStrategy(ABC):
    """
    Abstract interface for evaluating memory systems under identical scenario conditions.
    """
    def __init__(self, name: str, is_live: bool = False):
        self.name = name
        self.is_live = is_live

    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """
        Returns (True, "Ready") if available, or (False, "Reason for unavailability").
        Never invent results if a baseline is unavailable.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """Initialize clean state before each scenario run."""
        pass

    @abstractmethod
    async def ingest_episode(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Ingest an episode turn.
        Returns telemetry:
        {
          "latency_ms": float,
          "input_tokens": int,
          "output_tokens": int,
          "total_tokens": int,
          "tokens_is_measured": bool,
          "cost_usd": float,
          "method": str,
          "extracted_count": int,
          "invalidated_count": int
        }
        """
        pass

    @abstractmethod
    async def answer_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a verification question.
        Returns:
        {
          "answer": str,
          "latency_ms": float,
          "confidence": float,
          "grounded": bool
        }
        """
        pass

    @abstractmethod
    async def get_active_facts(self) -> List[Dict[str, str]]:
        """Return list of active triplet dicts: [{"subject": ..., "predicate": ..., "object": ...}]"""
        pass

    @abstractmethod
    async def get_historical_facts(self) -> List[Dict[str, str]]:
        """Return list of superseded historical triplet dicts"""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up scenario state."""
        pass
