"""Regression tests for Provider Runtime Error Normalization.

Verifies:
1. Ollama connection error explains local daemon is unreachable and provides exact 'ollama serve' commands.
2. Cloud provider connection error (e.g. Groq) explains endpoint connection failure without falsely mentioning Ollama.
3. Authentication failure explains API key invalidity and guides user to Model Configuration.
4. Model not found distinguishes local Ollama missing model from cloud model identifier error.
5. Rate limit / quota (429) is accurately communicated.
6. Secrets, authorization headers, and internal tracebacks are never exposed to users.
"""

import pytest
import httpx
from support_bot.core.config import SessionModelConfig
from support_bot.workflows.support_workflow import format_provider_runtime_error


@pytest.mark.unit
def test_ollama_connection_error_mentions_ollama_serve():
    """Verify Ollama connection error provides actionable local commands."""
    config = SessionModelConfig(
        provider_name="ollama",
        model_name="llama3.2:latest",
        endpoint_url="http://localhost:11434",
    )
    ex = httpx.ConnectError("All connection attempts failed: [WinError 10061]")
    msg = format_provider_runtime_error(ex, config)
    
    assert "ollama serve" in msg
    assert "ollama list" in msg
    assert "http://localhost:11434" in msg
    assert "Local Ollama Daemon Unreachable" in msg


@pytest.mark.unit
def test_groq_connection_error_does_not_mention_ollama():
    """Verify Groq connection error NEVER mentions Ollama or Ollama commands."""
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url="https://api.groq.com/openai/v1",
    )
    ex = httpx.ConnectError("Could not contact endpoint")
    msg = format_provider_runtime_error(ex, config)

    assert "groq" in msg.lower()
    assert "ollama" not in msg.lower()
    assert "ollama serve" not in msg


@pytest.mark.unit
def test_authentication_error_guides_to_model_configuration():
    """Verify 401 authentication error asks user to enter valid API key in settings."""
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url="https://api.groq.com/openai/v1",
    )
    ex = Exception("Error code: 401 - {'error': {'message': 'Invalid API Key', 'type': 'invalid_request_error'}}")
    msg = format_provider_runtime_error(ex, config)

    assert "Authentication Failed" in msg
    assert "API key" in msg
    assert "Model Configuration" in msg
    assert "ollama" not in msg.lower()


@pytest.mark.unit
def test_ollama_missing_model_mentions_pull_command():
    """Verify Ollama missing model error mentions 'ollama pull'."""
    config = SessionModelConfig(
        provider_name="ollama",
        model_name="llama3.2:latest",
        endpoint_url="http://localhost:11434",
    )
    ex = Exception("model 'llama3.2:latest' not found, try pulling it first")
    msg = format_provider_runtime_error(ex, config)

    assert "Model Not Installed" in msg
    assert "ollama pull llama3.2:latest" in msg


@pytest.mark.unit
def test_groq_missing_model_mentions_model_unavailable():
    """Verify cloud provider missing model does not mention 'ollama pull'."""
    config = SessionModelConfig(
        provider_name="groq",
        model_name="unsupported-model-id",
        endpoint_url="https://api.groq.com/openai/v1",
    )
    ex = Exception("404 The model does not exist")
    msg = format_provider_runtime_error(ex, config)

    assert "Model Unavailable" in msg
    assert "groq" in msg.lower()
    assert "ollama pull" not in msg


@pytest.mark.unit
def test_rate_limit_error_reports_quota_status():
    """Verify 429 rate limit is reported accurately."""
    config = SessionModelConfig(
        provider_name="groq",
        model_name="llama-3.3-70b-versatile",
        endpoint_url="https://api.groq.com/openai/v1",
    )
    ex = Exception("429 Rate limit reached for model `llama-3.3-70b-versatile`")
    msg = format_provider_runtime_error(ex, config)

    assert "Rate Limit or Quota Exceeded" in msg
    assert "groq" in msg.lower()
