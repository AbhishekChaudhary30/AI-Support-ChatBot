"""Regression and unit tests for GroqProvider adapter.

Verifies:
1. Canonical Groq endpoint (https://api.groq.com/openai/v1) and default model (llama-3.3-70b-versatile).
2. Prevention of accidental Ollama localhost:11434 endpoint mixing.
3. Rejection of generic provider placeholder 'groq' as model ID.
4. Session-scoped API key enforcement and isolation.
5. Truthful health checks (200 success, 401 auth error, 429 rate limit, connection failure).
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import (
    ProviderAuthenticationError,
    SecurityValidationError,
)
from support_bot.providers.groq_provider import (
    GroqProvider,
    GROQ_DEFAULT_ENDPOINT,
    GROQ_DEFAULT_MODEL,
    GROQ_SUPPORTED_MODELS,
)
from support_bot.security.secrets import SessionSecret


@pytest.mark.unit
def test_groq_provider_capabilities():
    """Verify Groq provider capabilities and canonical defaults."""
    provider = GroqProvider()
    assert provider.provider_name == "groq"
    assert provider.capabilities.is_local is False
    assert provider.capabilities.requires_api_key is True
    assert provider.capabilities.default_endpoint == "https://api.groq.com/openai/v1"
    assert provider.capabilities.default_model == "llama-3.3-70b-versatile"
    assert "llama-3.3-70b-versatile" in provider.capabilities.supported_models
    assert "llama-3.1-8b-instant" in provider.capabilities.supported_models


@pytest.mark.unit
def test_groq_missing_credentials_raises_auth_error():
    """Verify missing Groq API key raises ProviderAuthenticationError."""
    provider = GroqProvider()
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url=GROQ_DEFAULT_ENDPOINT,
    )
    with pytest.raises(ProviderAuthenticationError, match="API key is required"):
        provider.validate_configuration(config, session_secret=None)

    empty_secret = SessionSecret(None)
    with pytest.raises(ProviderAuthenticationError, match="API key is required"):
        provider.validate_configuration(config, session_secret=empty_secret)


@pytest.mark.unit
def test_groq_rejects_ollama_localhost_endpoint():
    """Verify Groq rejects Ollama localhost:11434 endpoint."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_mock_groq_api_key_12345")
    
    ollama_endpoints = [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://localhost:11434/api",
        "http://127.0.0.1:8000",
    ]
    for ep in ollama_endpoints:
        config = SessionModelConfig(
            provider_name="groq",
            model_name="llama-3.3-70b-versatile",
            endpoint_url=ep,
        )
        with pytest.raises(SecurityValidationError, match="invalid for cloud provider"):
            provider.validate_configuration(config, session_secret=secret)


@pytest.mark.unit
def test_groq_rejects_generic_groq_model_name():
    """Verify Groq rejects generic placeholder 'groq' as model identifier."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_mock_groq_api_key_12345")
    
    placeholders = ["groq", "GROQ", "provider", "model", "default"]
    for ph in placeholders:
        config = SessionModelConfig(
            provider_name="groq",
            model_name=ph,
            endpoint_url=GROQ_DEFAULT_ENDPOINT,
        )
        with pytest.raises(SecurityValidationError, match="placeholder"):
            provider.validate_configuration(config, session_secret=secret)


@pytest.mark.unit
def test_groq_valid_configuration_passes():
    """Verify valid Groq model and endpoint pass validation."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_valid_mock_key_test_123")
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url=GROQ_DEFAULT_ENDPOINT,
    )
    provider.validate_configuration(config, session_secret=secret)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_missing_key():
    """Verify health check reports missing key truthfully."""
    provider = GroqProvider()
    health = await provider.check_health(session_secret=None)
    assert health["is_healthy"] is False
    assert "API key required" in health["message"]
    assert health["details"]["key_missing"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_invalid_endpoint():
    """Verify health check reports Ollama localhost endpoint rejection."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_test_key_12345")
    health = await provider.check_health(
        endpoint_url="http://localhost:11434",
        session_secret=secret,
        model_name="llama-3.3-70b-versatile",
    )
    assert health["is_healthy"] is False
    assert "Ollama" in health["message"] or "invalid" in health["message"]
    assert health["details"]["invalid_endpoint"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_placeholder_model():
    """Verify health check reports generic 'groq' model name rejection."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_test_key_12345")
    health = await provider.check_health(
        endpoint_url=GROQ_DEFAULT_ENDPOINT,
        session_secret=secret,
        model_name="groq",
    )
    assert health["is_healthy"] is False
    assert "provider name" in health["message"]
    assert health["details"]["invalid_model"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_success_200():
    """Verify health check succeeds when Groq responds with 200."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_mock_valid_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "llama-3.3-70b-versatile"},
            {"id": "llama-3.1-8b-instant"},
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        health = await provider.check_health(
            endpoint_url=GROQ_DEFAULT_ENDPOINT,
            session_secret=secret,
            model_name="llama-3.3-70b-versatile",
        )
        assert health["is_healthy"] is True
        assert "Groq LPU active and authenticated" in health["message"]
        assert health["details"]["count"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_auth_failure_401():
    """Verify health check truthfully reports 401 authentication failure."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_invalid_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        health = await provider.check_health(
            endpoint_url=GROQ_DEFAULT_ENDPOINT,
            session_secret=secret,
            model_name="llama-3.3-70b-versatile",
        )
        assert health["is_healthy"] is False
        assert "Authentication failed" in health["message"]
        assert health["details"]["status_code"] == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_groq_health_check_rate_limit_429():
    """Verify health check truthfully reports 429 rate limit / quota."""
    provider = GroqProvider()
    secret = SessionSecret("gsk_rate_limited_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        health = await provider.check_health(
            endpoint_url=GROQ_DEFAULT_ENDPOINT,
            session_secret=secret,
            model_name="llama-3.3-70b-versatile",
        )
        assert health["is_healthy"] is False
        assert "rate limit or quota" in health["message"].lower()
        assert health["details"]["status_code"] == 429
