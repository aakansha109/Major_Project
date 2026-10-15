from app.api.health import router as health_router
from app.api.episodes import router as episodes_router
from app.api.facts import router as facts_router
from app.api.graph import router as graph_router
from app.api.retrieval import router as retrieval_router
from app.api.inference import router as inference_router
from app.api.evaluation import router as evaluation_router
from app.api.seed import router as seed_router

__all__ = [
    "health_router",
    "episodes_router",
    "facts_router",
    "graph_router",
    "retrieval_router",
    "inference_router",
    "evaluation_router",
    "seed_router"
]
