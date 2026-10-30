"""Anthropic Claude Model Provider Adapter.

Supports native Anthropic Claude models (e.g. claude-3-5-sonnet, claude-3-5-haiku)
via langchain-anthropic with session-scoped credentials.
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

ANTHROPIC_DEFAULT_ENDPOINT = "https://api.anthropic.com/v1"
ANTHROPIC_DEFAULT_MODEL = "claude-3-5-haiku-latest"
ANTHROPIC_SUPPORTED_MODELS = [
    "claude-3-5-haiku-latest",
    "claude-3-5-sonnet-latest",
    "claude-3-opus-latest",
]


class AnthropicProvider(BaseModelProvider):
    """Adapter for official Anthropic Claude API."""

    def __init__(
        self,
        default_endpoint: str = ANTHROPIC_DEFAULT_ENDPOINT,
        default_model: str = ANTHROPIC_DEFAULT_MODEL,
    ):
        capabilities = ProviderCapabilities(
            provider_name="anthropic",
            display_name="Anthropic (Claude 3.5 Models)",
            is_local=False,
            requires_api_key=True,
            supports_streaming=True,
            supports_tools=True,
            default_endpoint=default_endpoint,
            default_model=default_model,
            supported_models=ANTHROPIC_SUPPORTED_MODELS,
            description="Leading AI reasoning and safety models (Claude 3.5 Sonnet, Claude 3.5 Haiku). Requires Anthropic API key.",
        )
        super().__init__(capabilities)

    async def check_health(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform reachability and authentication verification."""
        if not session_secret or not session_secret.is_configured():
            return {
                "is_healthy": False,
                "message": "API key required for Anthropic Claude. Enter your key in Model Configuration.",
                "latency_ms": None,
                "details": {"key_missing": True},
            }

        raw_url = endpoint_url or self.capabilities.default_endpoint or ANTHROPIC_DEFAULT_ENDPOINT
        try:
            base_url = normalize_endpoint_url(raw_url, provider_name="anthropic")
        except SecurityValidationError as sve:
            return {
                "is_healthy": False,
                "message": sve.user_friendly_message,
                "latency_ms": None,
                "details": {"invalid_endpoint": True},
            }
        headers = {
            "x-api-key": session_secret.get_secret_value(),
            "anthropic-version": "2023-06-01",
        }

        start_time = time.perf_counter()
        try:
            # Send lightweight GET to models endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/models", headers=headers)
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return {
                        "is_healthy": True,
                        "message": f"Anthropic API authenticated and active. {len(models)} model(s) available.",
                        "latency_ms": latency,
                        "details": {"models": models},
                    }
                elif response.status_code in (401, 403):
                    return {
                        "is_healthy": False,
                        "message": "Authentication failed. The supplied Anthropic API key is invalid or unauthorized.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
                else:
                    return {
                        "is_healthy": False,
                        "message": f"Anthropic endpoint responded with HTTP status {response.status_code}.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
        except Exception as e:
            return {
                "is_healthy": False,
                "message": f"Could not connect to Anthropic endpoint. Check network connectivity: {str(e)}",
                "latency_ms": None,
                "details": {"error_type": type(e).__name__},
            }

    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Fetch models from Anthropic or return curated model identifiers."""
        if session_secret and session_secret.is_configured():
            try:
                base_url = (endpoint_url or self.capabilities.default_endpoint or "https://api.anthropic.com/v1").rstrip("/")
                headers = {
                    "x-api-key": session_secret.get_secret_value(),
                    "anthropic-version": "2023-06-01",
                }
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(f"{base_url}/models", headers=headers)
                    if resp.status_code == 200:
                        return [m.get("id") for m in resp.json().get("data", []) if m.get("id")]
            except Exception:
                pass
        return [
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-opus-latest",
        ]

    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Verify API key and model identifier."""
        if not session_secret or not session_secret.is_configured():
            raise ProviderAuthenticationError(
                provider_name="anthropic",
                message="An API key is required for Anthropic Claude.",
                user_friendly_message="Please enter your Anthropic API key in Model Configuration.",
            )
        if session_config.endpoint_url:
            normalize_endpoint_url(session_config.endpoint_url, provider_name="anthropic")
        validate_model_identifier(session_config.model_name, provider_name="anthropic")

    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate LangChain ChatAnthropic with session credentials."""
        self.validate_configuration(session_config, session_secret)
        api_key = session_secret.get_secret_value() if session_secret else ""

        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=session_config.model_name,
            api_key=api_key,
            temperature=session_config.temperature,
            max_tokens=session_config.max_tokens or 1024,
        )
