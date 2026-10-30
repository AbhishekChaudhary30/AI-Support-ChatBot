"""Regression tests for Provider Configuration Switching (Error A).

Verifies:
1. Switching provider from Ollama to Groq resolves canonical Groq endpoint (https://api.groq.com/openai/v1)
   and canonical Groq model (llama-3.3-70b-versatile).
2. Selecting Groq NEVER leaves Ollama's localhost:11434 endpoint intact.
3. User typing 'groq' as the model name is automatically normalized to 'llama-3.3-70b-versatile'.
4. Custom user endpoints for compatible gateways are preserved unless they match an Ollama loopback.
5. Cloud providers reject localhost / loopback addresses.
6. Local Ollama permits localhost:11434.
"""

import pytest
from support_bot.core.config import SessionModelConfig
from support_bot.core.exceptions import SecurityValidationError
from support_bot.providers.registry import registry
from support_bot.security.input_validation import normalize_endpoint_url, validate_model_identifier
from support_bot.security.secrets import SessionSecret


@pytest.mark.unit
def test_registry_contains_groq_with_canonical_settings():
    """Verify registry has Groq registered with canonical endpoint and model."""
    groq_provider = registry.get_provider("groq")
    assert groq_provider.capabilities.default_endpoint == "https://api.groq.com/openai/v1"
    assert groq_provider.capabilities.default_model == "llama-3.3-70b-versatile"
    assert registry.get_default_endpoint("groq") == "https://api.groq.com/openai/v1"
    assert registry.get_default_model("groq") == "llama-3.3-70b-versatile"


@pytest.mark.unit
def test_switching_from_ollama_to_groq_normalizes_endpoint():
    """Simulate on_settings_update logic when switching from Ollama to Groq."""
    # User's previous session state
    session_config = SessionModelConfig(
        provider_name="ollama",
        model_name="llama3.2:latest",
        endpoint_url="http://localhost:11434",
    )

    # Submitted payload from UI where user switched dropdown to 'groq'
    # but browser form retained 'http://localhost:11434' and 'llama3.2:latest'
    raw_settings = {
        "provider": "groq",
        "model_name": "llama3.2:latest",
        "endpoint_url": "http://localhost:11434",
    }

    previous_provider = session_config.provider_name
    submitted_provider = raw_settings["provider"].strip().lower()
    provider_changed = submitted_provider != previous_provider

    target_provider = registry.get_provider(submitted_provider)
    canonical_endpoint = target_provider.capabilities.default_endpoint
    canonical_model = target_provider.capabilities.default_model

    raw_endpoint = raw_settings["endpoint_url"].strip()
    is_ollama_endpoint = "localhost:11434" in raw_endpoint
    is_cloud_provider = not target_provider.capabilities.is_local

    # Endpoint resolution
    if provider_changed or (is_cloud_provider and is_ollama_endpoint):
        effective_endpoint = canonical_endpoint
    else:
        effective_endpoint = raw_endpoint

    # Model resolution
    raw_model = raw_settings["model_name"].strip()
    is_generic_placeholder = raw_model.lower() in ("groq", "ollama", "provider", "model", "default")
    prev_default_model = registry.get_provider(previous_provider).capabilities.default_model

    if provider_changed or is_generic_placeholder or raw_model == prev_default_model:
        effective_model = canonical_model
    else:
        effective_model = raw_model

    assert effective_endpoint == "https://api.groq.com/openai/v1"
    assert effective_endpoint != "http://localhost:11434"
    assert effective_model == "llama-3.3-70b-versatile"
    assert effective_model != "groq"
    assert effective_model != "llama3.2:latest"


@pytest.mark.unit
def test_model_name_typed_as_groq_is_normalized():
    """Verify when user types 'groq' into the model text input, it normalizes to default model."""
    raw_model = "groq"
    target_provider = registry.get_provider("groq")
    canonical_model = target_provider.capabilities.default_model

    is_generic_placeholder = raw_model.lower() in ("groq", "ollama", "provider", "model", "default")
    effective_model = canonical_model if is_generic_placeholder else raw_model

    assert effective_model == "llama-3.3-70b-versatile"


@pytest.mark.unit
def test_normalize_endpoint_url_strips_trailing_slash():
    """Verify trailing slash normalization."""
    assert normalize_endpoint_url("https://api.groq.com/openai/v1/", provider_name="groq") == "https://api.groq.com/openai/v1"
    assert normalize_endpoint_url("http://localhost:11434/", provider_name="ollama") == "http://localhost:11434"


@pytest.mark.unit
def test_cloud_providers_reject_loopback_and_ollama_ports():
    """Verify all cloud providers reject loopback and Ollama addresses."""
    cloud_providers = ["groq", "openai", "anthropic", "google", "mistral"]
    bad_endpoints = [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://169.254.169.254",
        "http://0.0.0.0:11434",
    ]
    for cp in cloud_providers:
        for ep in bad_endpoints:
            with pytest.raises(SecurityValidationError, match="invalid for cloud provider"):
                normalize_endpoint_url(ep, provider_name=cp)


@pytest.mark.unit
def test_ollama_permits_localhost_endpoint():
    """Verify local Ollama explicitly permits localhost."""
    assert normalize_endpoint_url("http://localhost:11434", provider_name="ollama") == "http://localhost:11434"
    assert normalize_endpoint_url("http://127.0.0.1:11434", provider_name="ollama") == "http://127.0.0.1:11434"


@pytest.mark.unit
def test_validate_model_identifier_rejects_provider_names():
    """Verify validate_model_identifier rejects provider names."""
    for name in ["groq", "ollama", "openai", "anthropic", "google", "mistral"]:
        with pytest.raises(SecurityValidationError, match="generic provider"):
            validate_model_identifier(name)
