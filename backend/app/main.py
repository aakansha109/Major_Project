import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.db.neo4j import neo4j_client
from app.api.health import router as health_router
from app.api.episodes import router as episodes_router
from app.api.facts import router as facts_router
from app.api.graph import router as graph_router
from app.api.retrieval import router as retrieval_router
from app.api.inference import router as inference_router
from app.api.evaluation import router as evaluation_router
from app.api.seed import router as seed_router
from app.api.chat import router as chat_router
from app.api.memory import router as memory_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chronos")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Try connecting to Neo4j
    logger.info("Initializing Chronos Temporal Memory Engine...")
    connected = neo4j_client.connect()
    if connected:
        logger.info("Neo4j database connected and verified.")
    else:
        logger.warning("Neo4j not reachable. Operating with local resilient SQLite persistence layer.")
    yield
    # Shutdown
    logger.info("Shutting down Chronos Temporal Memory Engine...")
    neo4j_client.close()

app = FastAPI(
    title="Chronos Memory API",
    description=(
        "Cost-Efficient Temporal Knowledge Graph Memory for Conversational AI Agents. "
        "B.Tech CSE (AI & ML) Major Project featuring hybrid rule-based & LLM extraction, "
        "temporal contradiction resolution, point-in-time retrieval, and empirical benchmarks."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register direct /health endpoint (and /api/health)
app.include_router(health_router)

# Register routers under /api
app.include_router(health_router, prefix="/api")
app.include_router(episodes_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(facts_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(retrieval_router, prefix="/api")
app.include_router(inference_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")
app.include_router(seed_router, prefix="/api")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
