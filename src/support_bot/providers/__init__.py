"""Model provider package."""

from support_bot.providers.anthropic_provider import AnthropicProvider
from support_bot.providers.base import BaseModelProvider, ProviderCapabilities
from support_bot.providers.compatible_provider import OpenAICompatibleProvider
from support_bot.providers.google_provider import GoogleGeminiProvider
from support_bot.providers.ollama_provider import OllamaProvider
from support_bot.providers.registry import ProviderRegistry, registry

__all__ = [
    "BaseModelProvider",
    "ProviderCapabilities",
    "OpenAICompatibleProvider",
    "OllamaProvider",
    "GoogleGeminiProvider",
    "AnthropicProvider",
    "ProviderRegistry",
    "registry",
]
