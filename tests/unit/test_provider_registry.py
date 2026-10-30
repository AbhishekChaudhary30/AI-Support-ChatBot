"""Unit tests for Provider Registry."""

import pytest
from support_bot.core.exceptions import ConfigurationError
from support_bot.providers.registry import ProviderRegistry, registry


@pytest.mark.unit
def test_default_providers_registered():
    """Verify default providers exist in registry."""
    providers = registry.list_providers()
    assert "ollama" in providers
    assert "openai" in providers
    assert "groq" in providers
    assert "mistral" in providers
    assert "openai_compatible" in providers


@pytest.mark.unit
def test_get_provider_case_insensitive():
    """Verify provider lookup is case-insensitive."""
    p1 = registry.get_provider("Ollama")
    p2 = registry.get_provider("OLLAMA")
    p3 = registry.get_provider("ollama")
    assert p1 is p2 is p3


@pytest.mark.unit
def test_get_unknown_provider_raises_configuration_error():
    """Verify requesting an unknown provider raises ConfigurationError."""
    with pytest.raises(ConfigurationError, match="not registered"):
        registry.get_provider("non_existent_provider_123")


@pytest.mark.unit
def test_list_capabilities():
    """Verify capability metadata dictionary format."""
    caps = registry.list_capabilities()
    assert len(caps) >= 5
    for c in caps:
        assert "provider_name" in c
        assert "is_local" in c
        assert "requires_api_key" in c
