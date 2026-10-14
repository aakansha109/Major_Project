from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
import uuid

class Fact(BaseModel):
    id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:12]}")
    subject: str = Field(..., description="Subject entity (e.g. 'User', 'Alice')")
    predicate: str = Field(..., description="Temporal relation (e.g. 'backend_framework', 'lives_in')")
    object: str = Field(..., description="Object entity or value (e.g. 'FastAPI', 'Bangalore')")
    
    # Bi-temporal interval properties
    valid_from: datetime = Field(..., description="Effective start timestamp of this fact in the real world")
    valid_to: Optional[datetime] = Field(default=None, description="Effective expiration timestamp. None while currently active")
    
    # Status: 'active' or 'superseded'
    status: str = Field(default="active", description="'active' or 'superseded'")
    is_current: bool = Field(default=True, description="True if status is active and valid_to is None or in future")
    
    # Provenance
    source_episode_id: Optional[str] = Field(default=None, description="Originating conversation episode ID")
    episode_id: Optional[str] = Field(default=None, description="Alias for source_episode_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Transaction time when fact was recorded")
    tx_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Alias for created_at")
    
    # Extraction telemetry & Research auditability
    extraction_method: str = Field(default="rule", description="Extraction method: 'rule', 'llm', 'hybrid_rule', 'hybrid_llm_fallback'")
    source: str = Field(default="rule", description="Alias for extraction_method")
    rule_name: Optional[str] = Field(default=None, description="Identifier of the rule pattern if rule-extracted")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    
    # Token usage & Cost accounting (measured vs estimate distinction)
    tokens_used: int = Field(default=0, description="Total tokens consumed during extraction")
    input_tokens: Optional[int] = Field(default=None, description="Measured prompt/input tokens if from LLM API")
    output_tokens: Optional[int] = Field(default=None, description="Measured completion/output tokens if from LLM API")
    tokens_is_measured: bool = Field(default=False, description="True if token count was directly reported by the provider API usage object")
    estimated_cost_usd: float = Field(default=0.0, description="Monetary cost calculated on explicit pricing basis")
    cost_pricing_basis: Optional[str] = Field(default=None, description="Explanation of pricing formula used")
    decision_reason: Optional[str] = Field(default=None, description="Audit reason why rule or LLM fallback path was selected")

    raw_text: Optional[str] = Field(default=None, description="Source sentence or snippet")
    
    # Evolution and Graph links
    superseded_by: Optional[str] = Field(default=None, description="Fact ID that superseded this fact")
    supersedes_fact_id: Optional[str] = Field(default=None, description="Older Fact ID that this fact replaced")

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: dict):
        if not isinstance(data, dict):
            return data
        # Sync episode id
        if "source_episode_id" in data and "episode_id" not in data:
            data["episode_id"] = data["source_episode_id"]
        elif "episode_id" in data and "source_episode_id" not in data:
            data["source_episode_id"] = data["episode_id"]

        # Sync created_at / tx_time
        if "created_at" in data and "tx_time" not in data:
            data["tx_time"] = data["created_at"]
        elif "tx_time" in data and "created_at" not in data:
            data["created_at"] = data["tx_time"]

        # Sync source / extraction_method
        if "extraction_method" in data and "source" not in data:
            data["source"] = data["extraction_method"]
        elif "source" in data and "extraction_method" not in data:
            data["extraction_method"] = data["source"]

        # Sync status and is_current
        if "status" in data:
            if data["status"] == "superseded":
                data["is_current"] = False
            elif data["status"] == "active" and not data.get("valid_to"):
                data["is_current"] = True
        elif "is_current" in data:
            data["status"] = "active" if data["is_current"] else "superseded"

        return data

class FactFilter(BaseModel):
    as_of: Optional[datetime] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    only_current: bool = False
    status: Optional[str] = None
    source: Optional[str] = None
    limit: int = 100
    offset: int = 0
