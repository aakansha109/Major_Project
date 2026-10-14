from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.fact import Fact
from app.models.episode import Episode

class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or conversational message")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    as_of: Optional[datetime] = Field(default=None, description="Optional point-in-time timestamp for historical QA")

class ChatResponse(BaseModel):
    query: str
    answer: str
    grounded: bool = Field(..., description="True if answer is directly grounded in retrieved temporal records")
    evidence_status: str = Field(..., description="'verified_active', 'verified_historical', 'verified_point_in_time', 'semantic_episode', 'ungrounded'")
    supporting_fact_ids: List[str] = Field(default_factory=list, description="IDs of facts supporting the answer")
    source_episode_ids: List[str] = Field(default_factory=list, description="IDs of source conversation episodes")
    temporal_validity: Dict[str, Any] = Field(default_factory=dict, description="Validity bounds: valid_from, valid_to, is_current, as_of")
    retrieval_method: str = Field(..., description="'temporal_graph_active', 'temporal_graph_historical', 'temporal_graph_point_in_time', 'temporal_timeline', 'semantic_episode_retrieval', 'unmatched'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_facts: List[Fact] = Field(default_factory=list)
    supporting_episodes: List[Episode] = Field(default_factory=list)
    reasoning_chain: List[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0)

class MemoryHistoryItem(BaseModel):
    fact_id: str
    subject: str
    predicate: str
    object: str
    valid_from: datetime
    valid_to: Optional[datetime] = None
    status: str
    is_current: bool
    source_episode_id: Optional[str] = None
    superseded_by: Optional[str] = None
    confidence: float
    created_at: datetime
    extraction_method: str

class MemoryHistoryResponse(BaseModel):
    subject: Optional[str]
    predicate: Optional[str]
    total_events: int
    transitions_count: int
    timeline: List[MemoryHistoryItem]
