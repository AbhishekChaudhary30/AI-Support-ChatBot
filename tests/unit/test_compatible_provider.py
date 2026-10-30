"""Unit tests for OpenAICompatibleProvider adapter."""

import pytest
from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import ProviderAuthenticationError, SecurityValidationError
from support_bot.providers.compatible_provider import OpenAICompatibleProvider
from support_bot.security.secrets import SessionSecret


@pytest.mark.unit
def test_openai_compatible_capabilities():
    """Verify capabilities require API keys."""
    provider = OpenAICompatibleProvider()
    assert provider.capabilities.is_local is False
    assert provider.capabilities.requires_api_key is True


@pytest.mark.unit
def test_missing_credentials_raises_auth_error():
    """Verify missing session secret raises ProviderAuthenticationError."""
    provider = OpenAICompatibleProvider()
    config = SessionModelConfig(
        provider_name="openai_compatible",
        model_name="gpt-4o",
        endpoint_url="https://api.openai.com/v1",
    )
    with pytest.raises(ProviderAuthenticationError, match="API key is required"):
        provider.validate_configuration(config, session_secret=None)

    empty_secret = SessionSecret(None)
    with pytest.raises(ProviderAuthenticationError, match="API key is required"):
        provider.validate_configuration(config, session_secret=empty_secret)


@pytest.mark.unit
def test_valid_credentials_pass_validation(sample_session_secret):
    """Verify valid credentials and endpoint succeed."""
    provider = OpenAICompatibleProvider()
    config = SessionModelConfig(
        provider_name="openai_compatible",
        model_name="gpt-4o-mini",
        endpoint_url="https://api.openai.com/v1",
    )
    provider.validate_configuration(config, session_secret=sample_session_secret)
