import time
from fastapi import APIRouter
from app.db.graph_store import graph_store
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

START_TIME = time.time()

@router.get("")
def get_health():
    """
    Health check endpoint reporting Neo4j status, storage metrics,
    and server telemetry.
    """
    status = graph_store.get_status()
    uptime_sec = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "service": "chronos-temporal-memory",
        "version": "1.0.0",
        "uptime_seconds": uptime_sec,
        "environment": settings.ENVIRONMENT,
        "llm_fallback_enabled": settings.ENABLE_LLM_FALLBACK,
        "llm_api_configured": bool(settings.OPENAI_API_KEY),
        "llm_model": settings.OPENAI_MODEL,
        "storage": status
    }
