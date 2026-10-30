"""Application configuration and settings management.

Differentiates:
1. Static Application Settings (from .env / environment variables)
2. Ephemeral Session-Level Model Settings (configured dynamically per user session)
"""

from functools import lru_cache
from typing import Any, Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Immutable application-level settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Meta
    app_name: str = Field(default="AI Customer Support Chatbot", description="Brand name of the application")
    app_env: str = Field(default="development", description="Environment: development, test, production")
    log_level: str = Field(default="INFO", description="Structured logging level")
    debug: bool = Field(default=False, description="Debug flag for diagnostics")

    # Default Local Inference
    default_provider: str = Field(default="ollama", description="Default provider identifier")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API daemon URL")
    default_ollama_model: str = Field(default="llama3.2:latest", description="Default local LLM")

    # Timeouts & Limits
    request_timeout_seconds: int = Field(default=60, description="Network timeout for inference calls")
    max_message_length: int = Field(default=3000, description="Max allowed chat message characters")

    # Social & Connect Links (Configurable, no invented fake URLs)
    user_linkedin_url: Optional[str] = Field(default=None, description="Optional LinkedIn profile URL")
    user_github_url: Optional[str] = Field(default=None, description="Optional GitHub profile URL")

    # Knowledge Base & Retrieval
    knowledge_base_dir: str = Field(default="knowledge_base", description="Path to FAQ knowledge base files")
    chunk_size: int = Field(default=500, description="Chunk size in characters")
    chunk_overlap: int = Field(default=50, description="Chunk overlap in characters")
    embedding_model_name: str = Field(default="nomic-embed-text", description="Default embedding model")


class SessionModelConfig:
    """Session-scoped runtime configuration for the active model provider.
    
    Contains generation parameters and model identifiers for the current session.
    Secrets (API keys) are managed separately via SessionSecret to avoid accidental persistence.
    """

    def __init__(
        self,
        provider_name: str = "ollama",
        model_name: str = "llama3.2:latest",
        endpoint_url: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 1024,
        top_p: float = 0.9,
    ):
        self.provider_name = provider_name
        self.model_name = model_name
        self.endpoint_url = endpoint_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

    def to_dict(self) -> Dict[str, Any]:
        """Convert safe public configuration to dictionary (contains NO secrets)."""
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "endpoint_url": self.endpoint_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }

    def __repr__(self) -> str:
        return f"<SessionModelConfig provider={self.provider_name} model={self.model_name} endpoint={self.endpoint_url}>"


@lru_cache()
def get_settings() -> AppSettings:
    """Return cached singleton instance of AppSettings."""
    return AppSettings()
