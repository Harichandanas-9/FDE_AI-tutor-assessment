"""
Configuration Management
========================
Centralized settings using Pydantic BaseSettings.
All config values are loaded from environment variables / .env file.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Provides type validation and default values for all config.
    """

    # --- Application ---
    APP_NAME: str = "AI Multi-Agent Smart Learning Assistant"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # --- Server ---
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=1, env="WORKERS")

    # --- OpenAI ---
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL"
    )
    OPENAI_MAX_TOKENS: int = Field(default=4096, env="OPENAI_MAX_TOKENS")
    OPENAI_TEMPERATURE: float = Field(default=0.3, env="OPENAI_TEMPERATURE")

    # --- LangSmith ---
    LANGCHAIN_TRACING_V2: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = Field(
        default="ai-learning-assistant", env="LANGCHAIN_PROJECT"
    )
    LANGCHAIN_ENDPOINT: str = Field(
        default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT"
    )

    # --- Security ---
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173", env="ALLOWED_ORIGINS"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # --- Database ---
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/learning_assistant.db",
        env="DATABASE_URL",
    )

    # --- Redis ---
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    REDIS_TTL: int = Field(default=3600, env="REDIS_TTL")

    # --- ChromaDB ---
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="./data/vectordb", env="CHROMA_PERSIST_DIRECTORY"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="learning_materials", env="CHROMA_COLLECTION_NAME"
    )

    # --- File Storage ---
    UPLOAD_DIR: str = Field(default="./data/uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE_MB: int = Field(default=50, env="MAX_FILE_SIZE_MB")

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    # --- Evaluation ---
    DEEPEVAL_API_KEY: Optional[str] = Field(default=None, env="DEEPEVAL_API_KEY")
    EVALUATION_THRESHOLD_FAITHFULNESS: float = Field(
        default=0.7, env="EVALUATION_THRESHOLD_FAITHFULNESS"
    )
    EVALUATION_THRESHOLD_RELEVANCE: float = Field(
        default=0.7, env="EVALUATION_THRESHOLD_RELEVANCE"
    )
    EVALUATION_THRESHOLD_PRECISION: float = Field(
        default=0.6, env="EVALUATION_THRESHOLD_PRECISION"
    )

    # --- Rate Limiting ---
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    # --- Agents ---
    MAX_REFLECTION_ITERATIONS: int = Field(default=3, env="MAX_REFLECTION_ITERATIONS")
    MAX_RETRIEVAL_DOCS: int = Field(default=10, env="MAX_RETRIEVAL_DOCS")
    RETRIEVAL_TOP_K: int = Field(default=5, env="RETRIEVAL_TOP_K")
    HYBRID_SEARCH_ALPHA: float = Field(default=0.5, env="HYBRID_SEARCH_ALPHA")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Singleton settings instance
settings = Settings()
