"""Groq LPU Model Provider Adapter.

Supports ultra-low-latency inference using Groq Cloud API and open-weight models
(such as Llama 3.3 70B, Llama 3.1 8B, and Mixtral).
Requires session-scoped Groq API credentials. Never persists credentials to disk, database, or logs.
"""

import time
from typing import Any, Dict, List, Optional
import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    SecurityValidationError,
)
from support_bot.providers.base import BaseModelProvider, ProviderCapabilities
from support_bot.security.input_validation import (
    normalize_endpoint_url,
    validate_model_identifier,
)
from support_bot.security.secrets import SessionSecret

GROQ_DEFAULT_ENDPOINT = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_SUPPORTED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class GroqProvider(BaseModelProvider):
    """Adapter for Groq Cloud ultra-fast LPU inference."""

    def __init__(
        self,
        default_endpoint: str = GROQ_DEFAULT_ENDPOINT,
        default_model: str = GROQ_DEFAULT_MODEL,
    ):
        capabilities = ProviderCapabilities(
            provider_name="groq",
            display_name="Groq Cloud (LPU Ultra-Fast Inference)",
            is_local=False,
            requires_api_key=True,
            supports_streaming=True,
            supports_tools=True,
            default_endpoint=default_endpoint,
            default_model=default_model,
            supported_models=GROQ_SUPPORTED_MODELS,
            description="Ultra-low latency inference for Llama 3 and open models. Requires Groq API key.",
        )
        super().__init__(capabilities)

    async def check_health(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Verify reachability, authentication, and model availability against Groq API."""
        raw_url = endpoint_url or self.capabilities.default_endpoint or GROQ_DEFAULT_ENDPOINT
        
        # Verify endpoint is not an accidental loopback / Ollama port
        try:
            base_url = normalize_endpoint_url(raw_url, provider_name="groq")
        except SecurityValidationError as sve:
            return {
                "is_healthy": False,
                "message": sve.user_friendly_message,
                "latency_ms": None,
                "details": {"invalid_endpoint": True},
            }

        if not session_secret or not session_secret.is_configured():
            return {
                "is_healthy": False,
                "message": "API key required for Groq Cloud. Enter your key in Model Configuration.",
                "latency_ms": None,
                "details": {"key_missing": True},
            }

        # Validate that model_name is not generic placeholder
        if model_name and model_name.lower().strip() in ("groq", "provider", "model", "default"):
            return {
                "is_healthy": False,
                "message": (
                    f"'{model_name}' is a provider name, not a valid model ID. "
                    f"Please enter an actual Groq model ID (recommended: '{self.capabilities.default_model}')."
                ),
                "latency_ms": None,
                "details": {"invalid_model": True},
            }

        models_endpoint = f"{base_url}/models"
        headers = {"Authorization": f"Bearer {session_secret.get_secret_value()}"}
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(models_endpoint, headers=headers)
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    models_data = data.get("data", [])
                    discovered_models = [m.get("id") for m in models_data if m.get("id")]
                    
                    if model_name and discovered_models and model_name not in discovered_models and model_name not in GROQ_SUPPORTED_MODELS:
                        return {
                            "is_healthy": True,
                            "message": (
                                f"Groq API active, but model '{model_name}' was not found in provider model list. "
                                f"Recommended: '{self.capabilities.default_model}'."
                            ),
                            "latency_ms": latency,
                            "details": {"count": len(discovered_models), "model_unlisted": True},
                        }

                    return {
                        "is_healthy": True,
                        "message": f"Groq LPU active and authenticated. {len(discovered_models)} model(s) available.",
                        "latency_ms": latency,
                        "details": {"count": len(discovered_models)},
                    }
                elif response.status_code in (401, 403):
                    return {
                        "is_healthy": False,
                        "message": "Authentication failed. The supplied Groq API key is invalid or unauthorized.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
                elif response.status_code == 429:
                    return {
                        "is_healthy": False,
                        "message": "Groq rate limit or quota exceeded. Please wait a moment or check your Groq tier.",
                        "latency_ms": latency,
                        "details": {"status_code": 429},
                    }
                else:
                    return {
                        "is_healthy": False,
                        "message": f"Groq endpoint responded with HTTP status {response.status_code}.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
        except Exception as e:
            return {
                "is_healthy": False,
                "message": f"Connection error: Could not contact Groq endpoint '{base_url}'. Verify URL and network connectivity.",
                "latency_ms": None,
                "details": {"error_type": type(e).__name__},
            }

    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Fetch models from Groq or return curated list."""
        if session_secret and session_secret.is_configured():
            try:
                base_url = normalize_endpoint_url(endpoint_url or GROQ_DEFAULT_ENDPOINT, provider_name="groq")
                headers = {"Authorization": f"Bearer {session_secret.get_secret_value()}"}
                async with httpx.AsyncClient(timeout=4.0) as client:
                    response = await client.get(f"{base_url}/models", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                        if models:
                            return models
            except Exception:
                pass
        return list(GROQ_SUPPORTED_MODELS)

    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Verify API key, endpoint URL, and model identifier for Groq."""
        if not session_secret or not session_secret.is_configured():
            raise ProviderAuthenticationError(
                provider_name="groq",
                message="An API key is required for Groq Cloud.",
                user_friendly_message="Please enter your Groq API key in Model Configuration.",
            )

        endpoint = session_config.endpoint_url or self.capabilities.default_endpoint or GROQ_DEFAULT_ENDPOINT
        normalize_endpoint_url(endpoint, provider_name="groq")
        
        # Disallow generic placeholder 'groq'
        if session_config.model_name.lower().strip() in ("groq", "ollama", "openai", "anthropic", "google", "mistral", "default"):
            raise SecurityValidationError(
                message=f"Model identifier '{session_config.model_name}' is a provider placeholder, not a valid model ID.",
                user_friendly_message=(
                    f"'{session_config.model_name}' is a provider name. "
                    f"Please enter an actual Groq model ID such as '{self.capabilities.default_model}'."
                ),
            )
        validate_model_identifier(session_config.model_name, provider_name="groq")

    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate LangChain ChatGroq or ChatOpenAI configured with session credentials."""
        self.validate_configuration(session_config, session_secret)
        
        endpoint = normalize_endpoint_url(
            session_config.endpoint_url or self.capabilities.default_endpoint or GROQ_DEFAULT_ENDPOINT,
            provider_name="groq",
        )
        api_key = session_secret.get_secret_value() if session_secret else ""

        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=session_config.model_name,
                groq_api_key=api_key,
                temperature=session_config.temperature,
                max_tokens=session_config.max_tokens,
            )
        except ImportError:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=session_config.model_name,
                base_url=endpoint,
                api_key=api_key,
                temperature=session_config.temperature,
                max_tokens=session_config.max_tokens,
                top_p=session_config.top_p,
            )
