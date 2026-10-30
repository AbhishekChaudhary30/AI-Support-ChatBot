"""Model Provider Registry for dynamic provider lookup and lifecycle management.

Manages registered LLM providers, prevents hardcoded monolithic conditionals,
and enables clean extension for local and cloud models.
"""

from typing import Any, Dict, List, Optional
from support_bot.core.exceptions import ConfigurationError
from support_bot.providers.anthropic_provider import AnthropicProvider
from support_bot.providers.base import BaseModelProvider, ProviderCapabilities
from support_bot.providers.compatible_provider import OpenAICompatibleProvider
from support_bot.providers.google_provider import GoogleGeminiProvider
from support_bot.providers.groq_provider import GroqProvider
from support_bot.providers.ollama_provider import OllamaProvider


class ProviderRegistry:
    """Registry maintaining active model provider adapters."""

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Register default local and cloud provider adapters."""
        # 1. Primary local inference adapter (zero-cost default)
        self.register_provider(OllamaProvider())

        # 2. Standard OpenAI API adapter
        self.register_provider(OpenAICompatibleProvider(
            provider_name="openai",
            display_name="OpenAI (Official Cloud API)",
            default_endpoint="https://api.openai.com/v1",
            default_model="gpt-4o-mini",
            supported_models=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            description="Official OpenAI hosted models (e.g. gpt-4o, gpt-4o-mini). Requires OpenAI API key.",
        ))

        # 3. Google Gemini adapter
        self.register_provider(GoogleGeminiProvider())

        # 4. Anthropic Claude adapter
        self.register_provider(AnthropicProvider())

        # 5. Dedicated Groq ultra-fast LPU inference adapter
        self.register_provider(GroqProvider())

        # 6. Mistral AI cloud adapter
        self.register_provider(OpenAICompatibleProvider(
            provider_name="mistral",
            display_name="Mistral AI (European Cloud LLM)",
            default_endpoint="https://api.mistral.ai/v1",
            default_model="mistral-small-latest",
            supported_models=["mistral-small-latest", "mistral-large-latest", "open-mixtral-8x7b"],
            description="State-of-the-art European open and commercial models. Requires Mistral API key.",
        ))

        # 7. Generic OpenAI-compatible custom gateway / self-hosted adapter
        self.register_provider(OpenAICompatibleProvider(
            provider_name="openai_compatible",
            display_name="Custom OpenAI-Compatible Endpoint",
            default_endpoint="https://api.openai.com/v1",
            default_model="gpt-4o-mini",
            supported_models=["gpt-4o-mini", "gpt-4o", "custom"],
            description="Any custom or self-hosted gateway implementing OpenAI chat completions (e.g. vLLM, LocalAI).",
        ))

    def register_provider(self, provider: BaseModelProvider) -> None:
        """Register a new model provider adapter."""
        name = provider.provider_name.lower().strip()
        self._providers[name] = provider

    def get_provider(self, provider_name: str) -> BaseModelProvider:
        """Retrieve a registered provider by name.
        
        Raises:
            ConfigurationError: If the provider is not registered.
        """
        name = provider_name.lower().strip()
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise ConfigurationError(
                message=f"Provider '{provider_name}' is not registered. Available: {available}",
                user_friendly_message=f"Unknown model provider '{provider_name}'. Please choose from: {available}.",
            )
        return self._providers[name]

    def list_providers(self) -> List[str]:
        """Return list of all registered provider names."""
        return sorted(list(self._providers.keys()))

    def list_capabilities(self) -> List[Dict[str, Any]]:
        """Return list of provider capability dictionaries for UI presentation."""
        return [p.capabilities.to_dict() for p in self._providers.values()]

    def is_registered(self, provider_name: str) -> bool:
        """Check if provider name is registered."""
        return provider_name.lower().strip() in self._providers

    def get_default_endpoint(self, provider_name: str) -> str:
        """Return canonical default endpoint for provider."""
        provider = self.get_provider(provider_name)
        return provider.capabilities.default_endpoint or ""

    def get_default_model(self, provider_name: str) -> str:
        """Return canonical default model identifier for provider."""
        provider = self.get_provider(provider_name)
        return getattr(provider.capabilities, "default_model", "") or ""


# Global registry singleton
registry = ProviderRegistry()
