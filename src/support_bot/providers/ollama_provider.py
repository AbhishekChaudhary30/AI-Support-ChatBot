"""Ollama Local Model Provider Adapter.

Enables zero-cost, private local LLM inference without external API keys or cloud dependencies.
Provides active health checking, model discovery, and helpful setup guidance.
"""

import time
from typing import Any, Dict, List, Optional
import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import (
    ModelNotFoundError,
    ProviderConnectionError,
    SecurityValidationError,
)
from support_bot.providers.base import BaseModelProvider, ProviderCapabilities
from support_bot.security.input_validation import (
    validate_endpoint_url,
    validate_model_identifier,
)
from support_bot.security.secrets import SessionSecret


OLLAMA_DEFAULT_ENDPOINT = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2:latest"
OLLAMA_SUPPORTED_MODELS = [
    "llama3.2:latest",
    "llama3.2:1b",
    "llama3.1:8b",
    "mistral:latest",
    "qwen2.5:latest",
    "phi3:latest",
    "gemma2:latest",
]


class OllamaProvider(BaseModelProvider):
    """Adapter for local Ollama instances."""

    def __init__(
        self,
        default_endpoint: str = OLLAMA_DEFAULT_ENDPOINT,
        default_model: str = OLLAMA_DEFAULT_MODEL,
    ):
        capabilities = ProviderCapabilities(
            provider_name="ollama",
            display_name="Ollama (Local Open-Weight Models)",
            is_local=True,
            requires_api_key=False,
            supports_streaming=True,
            supports_tools=True,
            default_endpoint=default_endpoint,
            default_model=default_model,
            supported_models=OLLAMA_SUPPORTED_MODELS,
            description="Runs locally on your machine. Completely private and free with zero cloud API keys required.",
        )
        super().__init__(capabilities)

    async def check_health(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify if the Ollama daemon is active and whether the model is available."""
        base_url = (endpoint_url or self.capabilities.default_endpoint or OLLAMA_DEFAULT_ENDPOINT).rstrip("/")
        tags_endpoint = f"{base_url}/api/tags"

        # Check if generic placeholder was supplied as model
        if model_name and model_name.lower().strip() in ("ollama", "groq", "openai", "provider", "model", "default"):
            return {
                "is_healthy": False,
                "message": (
                    f"'{model_name}' is a provider name, not a valid model ID. "
                    f"Please enter an installed model (e.g. '{self.capabilities.default_model}')."
                ),
                "latency_ms": None,
                "details": {"invalid_model": True},
            }
        
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(tags_endpoint)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    
                    if model_name:
                        # Check base name (e.g. llama3.2 matches llama3.2:latest)
                        base_model = model_name.split(":")[0]
                        matched = any(model_name in m or base_model in m for m in models)
                        if not matched and models:
                            return {
                                "is_healthy": False,
                                "message": (
                                    f"Ollama is running at '{base_url}', but model '{model_name}' is not installed locally. "
                                    f"Run 'ollama pull {model_name}' in your terminal to download it."
                                ),
                                "latency_ms": latency,
                                "details": {"models": models, "model_missing": True},
                            }
                    
                    return {
                        "is_healthy": True,
                        "message": f"Ollama is active and running. {len(models)} model(s) installed.",
                        "latency_ms": latency,
                        "details": {"models": models, "count": len(models)},
                    }
                else:
                    return {
                        "is_healthy": False,
                        "message": f"Ollama returned HTTP status {response.status_code}.",
                        "latency_ms": latency,
                        "details": None,
                    }
        except Exception as e:
            return {
                "is_healthy": False,
                "message": (
                    f"Cannot connect to local Ollama daemon at '{base_url}'. "
                    "Ensure Ollama is installed and running (command: 'ollama serve')."
                ),
                "latency_ms": None,
                "details": {"daemon_offline": True, "error_type": type(e).__name__},
            }

    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Fetch list of pulled local models from Ollama."""
        base_url = (endpoint_url or self.capabilities.default_endpoint or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models if models else ["llama3.2:latest", "mistral:latest"]
        except Exception:
            pass
        return ["llama3.2:latest", "mistral:latest", "qwen2.5:latest"]

    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Validate endpoint and model identifier."""
        if session_config.endpoint_url:
            validate_endpoint_url(session_config.endpoint_url)
        validate_model_identifier(session_config.model_name)

    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate LangChain ChatOllama with session parameters."""
        self.validate_configuration(session_config, session_secret)
        
        endpoint = session_config.endpoint_url or self.capabilities.default_endpoint or "http://localhost:11434"
        
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=session_config.model_name,
                base_url=endpoint,
                temperature=session_config.temperature,
                top_p=session_config.top_p,
            )
        except ImportError:
            # Fallback import if langchain_community is used
            from langchain_community.chat_models import ChatOllama as CommunityChatOllama
            return CommunityChatOllama(
                model=session_config.model_name,
                base_url=endpoint,
                temperature=session_config.temperature,
                top_p=session_config.top_p,
            )
