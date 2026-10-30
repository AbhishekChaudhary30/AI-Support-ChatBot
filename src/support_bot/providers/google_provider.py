"""Google Gemini Model Provider Adapter.

Supports Google Gemini models (e.g. gemini-2.0-flash, gemini-1.5-pro)
via langchain-google-genai with session-scoped credentials.
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

GOOGLE_DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com"
GOOGLE_DEFAULT_MODEL = "gemini-1.5-flash"
GOOGLE_SUPPORTED_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


class GoogleGeminiProvider(BaseModelProvider):
    """Adapter for official Google Gemini AI Studio API."""

    def __init__(
        self,
        default_endpoint: str = GOOGLE_DEFAULT_ENDPOINT,
        default_model: str = GOOGLE_DEFAULT_MODEL,
    ):
        capabilities = ProviderCapabilities(
            provider_name="google",
            display_name="Google Gemini (Gemini 2.0 / 1.5)",
            is_local=False,
            requires_api_key=True,
            supports_streaming=True,
            supports_tools=True,
            default_endpoint=default_endpoint,
            default_model=default_model,
            supported_models=GOOGLE_SUPPORTED_MODELS,
            description="Google Gemini multimodal and high-speed reasoning models. Requires Google AI Studio API key.",
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
                "message": "API key required for Google Gemini. Enter your key in Model Configuration.",
                "latency_ms": None,
                "details": {"key_missing": True},
            }

        raw_url = endpoint_url or self.capabilities.default_endpoint or GOOGLE_DEFAULT_ENDPOINT
        try:
            base_url = normalize_endpoint_url(raw_url, provider_name="google")
        except SecurityValidationError as sve:
            return {
                "is_healthy": False,
                "message": sve.user_friendly_message,
                "latency_ms": None,
                "details": {"invalid_endpoint": True},
            }

        api_key = session_secret.get_secret_value()
        models_url = f"{base_url}/v1beta/models?key={api_key}"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(models_url)
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    models = [
                        m.get("name", "").replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return {
                        "is_healthy": True,
                        "message": f"Google Gemini API authenticated and active. {len(models)} model(s) available.",
                        "latency_ms": latency,
                        "details": {"models": models},
                    }
                elif response.status_code in (400, 403):
                    return {
                        "is_healthy": False,
                        "message": "Authentication failed. The supplied Google Gemini API key is invalid.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
                else:
                    return {
                        "is_healthy": False,
                        "message": f"Google Gemini endpoint returned HTTP status {response.status_code}.",
                        "latency_ms": latency,
                        "details": {"status_code": response.status_code},
                    }
        except Exception as e:
            return {
                "is_healthy": False,
                "message": f"Could not reach Google Gemini endpoint: {str(e)}",
                "latency_ms": None,
                "details": {"error_type": type(e).__name__},
            }

    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Fetch models from Google or return curated model identifiers."""
        if session_secret and session_secret.is_configured():
            try:
                api_key = session_secret.get_secret_value()
                base_url = (endpoint_url or self.capabilities.default_endpoint or "https://generativelanguage.googleapis.com").rstrip("/")
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(f"{base_url}/v1beta/models?key={api_key}")
                    if resp.status_code == 200:
                        return [
                            m.get("name", "").replace("models/", "")
                            for m in resp.json().get("models", [])
                            if "generateContent" in m.get("supportedGenerationMethods", [])
                        ]
            except Exception:
                pass
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Verify API key and model identifier."""
        if not session_secret or not session_secret.is_configured():
            raise ProviderAuthenticationError(
                provider_name="google",
                message="An API key is required for Google Gemini.",
                user_friendly_message="Please enter your Google Gemini API key in Model Configuration.",
            )
        if session_config.endpoint_url:
            normalize_endpoint_url(session_config.endpoint_url, provider_name="google")
        validate_model_identifier(session_config.model_name, provider_name="google")

    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate LangChain ChatGoogleGenerativeAI with session credentials."""
        self.validate_configuration(session_config, session_secret)
        api_key = session_secret.get_secret_value() if session_secret else ""

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=session_config.model_name,
            google_api_key=api_key,
            temperature=session_config.temperature,
            max_output_tokens=session_config.max_tokens or 1024,
            top_p=session_config.top_p,
        )
