"""OpenAI-Compatible Model Provider Adapter.

Supports configurable cloud and self-hosted inference services adhering to the
OpenAI chat completions specification (e.g. OpenAI, Groq, Together AI, Mistral, LocalAI, vLLM).
Requires session-scoped API credentials.
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


class OpenAICompatibleProvider(BaseModelProvider):
    """Adapter for OpenAI-compatible REST endpoints."""

    def __init__(
        self,
        provider_name: str = "openai_compatible",
        display_name: str = "OpenAI-Compatible Service",
        default_endpoint: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        supported_models: Optional[List[str]] = None,
        description: str = "Connects to any service implementing the OpenAI chat completions standard.",
    ):
        capabilities = ProviderCapabilities(
            provider_name=provider_name,
            display_name=display_name,
            is_local=False,
            requires_api_key=True,
            supports_streaming=True,
            supports_tools=True,
            default_endpoint=default_endpoint,
            default_model=default_model,
            supported_models=supported_models or ["gpt-4o-mini", "gpt-4o"],
            description=description,
        )
        super().__init__(capabilities)

    async def check_health(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform a non-destructive reachability ping to the provider's /models endpoint."""
        raw_url = endpoint_url or self.capabilities.default_endpoint or "https://api.openai.com/v1"
        try:
            base_url = normalize_endpoint_url(raw_url, provider_name=self.provider_name)
        except SecurityValidationError as sve:
            return {
                "is_healthy": False,
                "message": sve.user_friendly_message,
                "latency_ms": None,
                "details": {"invalid_endpoint": True},
            }

        models_endpoint = f"{base_url}/models"
        
        if not session_secret or not session_secret.is_configured():
            return {
                "is_healthy": False,
                "message": f"API key required for {self.capabilities.display_name}. Enter your key in Model Configuration.",
                "latency_ms": None,
                "details": {"key_missing": True},
            }

        if model_name and model_name.lower().strip() in (self.provider_name, "provider", "model", "default"):
            return {
                "is_healthy": False,
                "message": f"'{model_name}' is a provider name, not a valid model ID. Please enter an actual model ID (e.g. '{self.capabilities.default_model}').",
                "latency_ms": None,
                "details": {"invalid_model": True},
            }

        headers = {"Authorization": f"Bearer {session_secret.get_secret_value()}"}
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(models_endpoint, headers=headers)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    data = response.json()
                    models_count = len(data.get("data", []))
                    return {
                        "is_healthy": True,
                        "message": f"Endpoint active and authenticated. {models_count} model(s) discovered.",
                        "latency_ms": latency,
                        "details": {"count": models_count},
                    }
                elif response.status_code in (401, 403):
                    return {
                        "is_healthy": False,
                        "message": "Authentication failed. The supplied API key is invalid, missing, or unauthorized.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
                else:
                    return {
                        "is_healthy": False,
                        "message": f"Endpoint responded with unexpected HTTP status {response.status_code}.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
        except Exception as e:
            return {
                "is_healthy": False,
                "message": f"Connection error: Could not contact endpoint '{base_url}'. Verify URL and network.",
                "latency_ms": None,
                "details": {"error_type": type(e).__name__},
            }

    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Fetch model names from the provider if an authenticated key is available."""
        base_url = (endpoint_url or self.capabilities.default_endpoint or "https://api.openai.com/v1").rstrip("/")
        if not session_secret or not session_secret.is_configured():
            return ["gpt-4o-mini", "gpt-4o", "llama-3.3-70b-versatile"]
            
        try:
            headers = {"Authorization": f"Bearer {session_secret.get_secret_value()}"}
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{base_url}/models", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return [m.get("id") for m in data.get("data", []) if m.get("id")]
        except Exception:
            pass
        return ["gpt-4o-mini", "gpt-4o"]

    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Verify API key, endpoint URL, and model identifier."""
        if not session_secret or not session_secret.is_configured():
            raise ProviderAuthenticationError(
                provider_name=self.provider_name,
                message="An API key is required for this cloud provider.",
                user_friendly_message="Please enter your API key in Model Configuration.",
            )
            
        endpoint = session_config.endpoint_url or self.capabilities.default_endpoint
        normalize_endpoint_url(endpoint, provider_name=self.provider_name)
        validate_model_identifier(session_config.model_name, provider_name=self.provider_name)

    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate LangChain ChatOpenAI configured for this specific session."""
        self.validate_configuration(session_config, session_secret)
        
        endpoint = (session_config.endpoint_url or self.capabilities.default_endpoint or "https://api.openai.com/v1").rstrip("/")
        api_key = session_secret.get_secret_value() if session_secret else ""
        
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=session_config.model_name,
                base_url=endpoint,
                api_key=api_key,
                temperature=session_config.temperature,
                max_tokens=session_config.max_tokens,
                top_p=session_config.top_p,
            )
        except ImportError:
            from langchain_community.chat_models import ChatOpenAI as CommunityChatOpenAI
            return CommunityChatOpenAI(
                model_name=session_config.model_name,
                openai_api_base=endpoint,
                openai_api_key=api_key,
                temperature=session_config.temperature,
                max_tokens=session_config.max_tokens,
            )
