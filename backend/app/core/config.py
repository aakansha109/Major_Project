import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Neo4j Graph DB Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "chronos_memory_2026"
    NEO4J_DATABASE: str = "neo4j"

    # LLM Provider & Model Configuration (OpenAI-compatible)
    LLM_PROVIDER: str = "openai_compatible"
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    ENABLE_LLM_FALLBACK: bool = True
    EXTRACTION_CONFIDENCE_THRESHOLD: float = 0.80
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.0
    LIVE_LLM_TESTS_ENABLED: bool = False

    # Storage paths
    LOCAL_DATA_DIR: str = str(BASE_DIR / "data")
    
    # Cost tracking constants (standard GPT-4o-mini costs in USD per 1M tokens)
    # Basis: OpenAI pricing as of 2024-2026 ($0.15 / 1M prompt tokens, $0.60 / 1M completion tokens)
    COST_PROMPT_PER_1M: float = 0.150
    COST_COMPLETION_PER_1M: float = 0.600
    COST_PRICING_BASIS_DESC: str = "GPT-4o-mini reference rate: $0.15/1M input tokens, $0.60/1M output tokens"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
