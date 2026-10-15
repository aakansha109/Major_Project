from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.fact import Fact

class InferenceRequest(BaseModel):
    query: str = Field(..., description="Query requiring temporal reasoning (e.g. 'Where does Alice work now?')")
    as_of: Optional[datetime] = Field(default=None, description="Time anchor for evaluation (defaults to now)")
    session_id: Optional[str] = Field(default=None)

class InferenceResponse(BaseModel):
    query: str
    as_of: str
    answer: str
    reasoning_chain: List[str]
    supporting_facts: List[Fact]
    superseded_facts: List[Fact]
    temporal_span_analyzed: Dict[str, Optional[str]]
    confidence: float
    latency_ms: float
