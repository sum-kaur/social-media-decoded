"""Application settings loaded from environment variables via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    llm_model: str = Field("claude-sonnet-4-6", alias="LLM_MODEL")
    llm_max_retries: int = Field(3, alias="LLM_MAX_RETRIES")
    llm_retry_base_delay: float = Field(1.0, alias="LLM_RETRY_BASE_DELAY")
    llm_max_tokens: int = Field(4096, alias="LLM_MAX_TOKENS")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    db_pool_min_size: int = Field(2, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(10, alias="DB_POOL_MAX_SIZE")

    # Embeddings
    embedding_model: str = Field("voyage-3", alias="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(96, alias="EMBEDDING_BATCH_SIZE")

    # App
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    api_port: int = Field(8000, alias="API_PORT")

    # Cache
    cache_backend: str = Field("memory", alias="CACHE_BACKEND")
    redis_url: str | None = Field(None, alias="REDIS_URL")
    cache_max_size: int = Field(512, alias="CACHE_MAX_SIZE")

    model_config = {"populate_by_name": True, "env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
