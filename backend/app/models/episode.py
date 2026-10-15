from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

class EpisodeCreate(BaseModel):
    session_id: str = Field(default="default_session", description="Conversation session ID")
    speaker: str = Field(default="user", description="Speaker: 'user' or 'assistant'")
    text: str = Field(..., description="Utterance text")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Utterance timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")

class Episode(BaseModel):
    id: str = Field(default_factory=lambda: f"ep_{uuid.uuid4().hex[:12]}")
    session_id: str
    speaker: str
    text: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
