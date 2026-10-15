from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat & Conversational Retrieval"])

@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Conversational Retrieval Endpoint:
    Processes natural language queries against the temporal knowledge graph and conversation history.
    - Resolves current vs historical questions (never answers past queries using only latest facts)
    - Resolves point-in-time state ("Where did Alice live in 2021?")
    - Generates chronological evolution ("Show the history of my backend framework")
    - Falls back to semantic episode retrieval when graph queries alone are insufficient
    - Strictly reports grounded evidence status, supporting fact IDs, and episode provenance
    """
    try:
        return await chat_service.process_chat(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversational retrieval failed: {str(e)}")
