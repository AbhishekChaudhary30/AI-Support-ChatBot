"""Unit tests for OllamaProvider adapter."""

import pytest
from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import SecurityValidationError
from support_bot.providers.ollama_provider import OllamaProvider


@pytest.mark.unit
def test_ollama_capabilities():
    """Verify Ollama adapter reports correct capabilities."""
    provider = OllamaProvider()
    assert provider.capabilities.is_local is True
    assert provider.capabilities.requires_api_key is False
    assert provider.capabilities.supports_streaming is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_health_offline_handling():
    """Verify health check returns clear status dict when Ollama daemon is offline."""
    # Use non-existent port to simulate offline daemon
    provider = OllamaProvider(default_endpoint="http://localhost:59999")
    health = await provider.check_health()
    assert health["is_healthy"] is False
    assert "ollama serve" in health["message"]


@pytest.mark.unit
def test_ollama_validate_configuration_success(sample_session_config):
    """Verify valid configuration passes validation."""
    provider = OllamaProvider()
    provider.validate_configuration(sample_session_config)


@pytest.mark.unit
def test_ollama_validate_configuration_invalid_url():
    """Verify invalid URL is caught."""
    provider = OllamaProvider()
    bad_config = SessionModelConfig(
        provider_name="ollama",
        model_name="llama3.2",
        endpoint_url="not-a-url",
    )
    with pytest.raises(SecurityValidationError):
        provider.validate_configuration(bad_config)
