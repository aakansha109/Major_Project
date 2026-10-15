from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.fact import Fact
from app.models.episode import Episode

class RetrievalQuery(BaseModel):
    query: str = Field(..., description="Natural language search or temporal question")
    as_of: Optional[datetime] = Field(default=None, description="Point-in-time snapshot timestamp (None = current now)")
    session_id: Optional[str] = Field(default=None, description="Optional session filter")
    top_k: int = Field(default=5, ge=1, le=50)
    include_neighborhood: bool = Field(default=True, description="Expand 1-hop graph neighborhood")
    include_episodes: bool = Field(default=True, description="Include source conversation episodes")

class GraphNode(BaseModel):
    id: str
    label: str
    type: str # 'entity' | 'episode'
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    label: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    is_current: bool = True
    status: str = "active"
    confidence: float = 1.0
    source_type: str = "rule"
    source_episode_id: Optional[str] = None
    fact_id: Optional[str] = None

class Subgraph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

class RetrievalResult(BaseModel):
    query: str
    as_of: Optional[datetime] = None
    matched_facts: List[Fact]
    matched_episodes: List[Episode]
    subgraph: Subgraph
    latency_ms: float
    retrieval_strategy: str # "temporal_vector_hybrid"
    stats: Dict[str, Any] = Field(default_factory=dict)
