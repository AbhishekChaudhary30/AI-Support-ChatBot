"""Unit tests for configuration management."""

import pytest
from support_bot.core.config import AppSettings, SessionModelConfig, get_settings


@pytest.mark.unit
def test_default_app_settings():
    """Verify default application settings are properly loaded."""
    settings = AppSettings()
    assert settings.app_name == "AI Customer Support Chatbot"
    assert settings.default_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.default_ollama_model == "llama3.2:latest"
    assert settings.max_message_length > 0
    assert settings.request_timeout_seconds > 0


@pytest.mark.unit
def test_session_model_config_serialization():
    """Verify SessionModelConfig does not expose or store secrets."""
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url="https://api.groq.com/openai/v1",
        temperature=0.7,
        max_tokens=2048,
    )
    data = config.to_dict()
    assert data["provider_name"] == "groq"
    assert data["model_name"] == "llama-3.3-70b-versatile"
    assert "api_key" not in data
    assert "secret" not in data
    assert repr(config).startswith("<SessionModelConfig")


@pytest.mark.unit
def test_get_settings_singleton():
    """Verify get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
