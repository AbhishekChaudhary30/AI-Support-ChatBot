"""Input validation and security boundaries for AI Customer Support Chatbot.

Enforces:
1. Message length boundaries and non-empty checks.
2. Character sanitization and basic prompt injection pattern detection.
3. Provider configuration validation (endpoint URLs, model identifiers, hyperparameter limits).
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from support_bot.core.exceptions import SecurityValidationError

# Model identifier regex: allows letters, numbers, colons (e.g. llama3:8b), dashes, slashes, underscores, dots
VALID_MODEL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-\.\:\/]{1,120}$")

# Suspicious prompt injection and jailbreak signatures
SUSPICIOUS_PROMPT_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)", re.IGNORECASE),
    re.compile(r"(disregard|forget)\s+(all\s+)?(previous|prior)\s+(rules|guidelines)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbreak)", re.IGNORECASE),
    re.compile(r"(reveal|print|output|display)\s+(the\s+)?(system\s+prompt|initial\s+prompt|hidden\s+instructions)", re.IGNORECASE),
    re.compile(r"base64\s+decode\s+the\s+following", re.IGNORECASE),
]


def validate_user_message(text: Optional[str], max_length: int = 3000) -> str:
    """Validate and clean user chat message input.
    
    Args:
        text: The raw user input string.
        max_length: Maximum allowed character length.
        
    Returns:
        Cleaned, stripped string.
        
    Raises:
        SecurityValidationError: If the message is empty, exceeds length, or contains high-risk patterns.
    """
    if text is None:
        raise SecurityValidationError(
            message="Message cannot be None.",
            user_friendly_message="Please enter a valid message.",
        )
    
    cleaned = text.strip()
    if not cleaned:
        raise SecurityValidationError(
            message="Message is empty or whitespace only.",
            user_friendly_message="Message cannot be empty. Please ask a customer support question.",
        )
    
    if len(cleaned) > max_length:
        raise SecurityValidationError(
            message=f"Message length ({len(cleaned)}) exceeds limit ({max_length}).",
            user_friendly_message=f"Your message is too long (maximum {max_length} characters). Please shorten your question.",
        )
    
    # Check for direct prompt injection signatures
    for pattern in SUSPICIOUS_PROMPT_PATTERNS:
        if pattern.search(cleaned):
            raise SecurityValidationError(
                message=f"Security alert: Potential prompt injection detected matching pattern '{pattern.pattern}'.",
                user_friendly_message=(
                    "Your message triggered our safety filters. Please rephrase your question using standard "
                    "customer support inquiries."
                ),
            )
            
    return cleaned


GENERIC_PROVIDER_PLACEHOLDERS = {
    "groq",
    "ollama",
    "openai",
    "anthropic",
    "google",
    "mistral",
    "provider",
    "model",
    "default",
}

BLOCKED_CLOUD_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",
}


def validate_model_identifier(model_name: Optional[str], provider_name: Optional[str] = None) -> str:
    """Validate model name syntax and reject generic provider placeholders."""
    if not model_name or not model_name.strip():
        raise SecurityValidationError(
            message="Model name cannot be empty.",
            user_friendly_message="Please specify a valid model name (e.g. 'llama3.2:latest' or 'llama-3.3-70b-versatile').",
        )
    
    stripped = model_name.strip()
    if stripped.lower() in GENERIC_PROVIDER_PLACEHOLDERS:
        raise SecurityValidationError(
            message=f"'{stripped}' is a generic provider or placeholder name, not a valid model ID.",
            user_friendly_message=(
                f"'{stripped}' is a provider name, not a model identifier. "
                "Please enter a valid model ID (e.g. 'llama-3.3-70b-versatile' for Groq or 'llama3.2:latest' for Ollama)."
            ),
        )

    if not VALID_MODEL_IDENTIFIER_PATTERN.match(stripped):
        raise SecurityValidationError(
            message=f"Invalid model identifier format: '{stripped}'",
            user_friendly_message=(
                f"The model name '{stripped}' contains invalid characters. "
                "Only letters, numbers, colons, slashes, dashes, and periods are permitted."
            ),
        )
    return stripped


def normalize_endpoint_url(url: Optional[str], provider_name: str = "") -> str:
    """Normalize and validate HTTP/HTTPS endpoint URL format.
    
    Ensures safe normalization of trailing slashes, validates URL structure,
    and prevents loopback/private IP SSRF or Ollama port contamination for cloud providers.
    """
    if not url or not url.strip():
        raise SecurityValidationError(
            message="Endpoint URL cannot be empty.",
            user_friendly_message="Please specify a valid endpoint URL (e.g. 'http://localhost:11434' or 'https://api.openai.com/v1').",
        )
    
    stripped = url.strip().rstrip("/")
    parsed = urlparse(stripped)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise SecurityValidationError(
            message=f"Invalid endpoint URL '{stripped}'. Must be an http or https URL.",
            user_friendly_message="Please enter a valid URL starting with http:// or https://.",
        )
    
    prov = (provider_name or "").lower().strip()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    # Prevent accidental mixing of local Ollama daemon port into cloud providers
    cloud_providers = {"groq", "openai", "anthropic", "google", "mistral"}
    if prov in cloud_providers:
        if hostname in BLOCKED_CLOUD_HOSTS or port == 11434:
            raise SecurityValidationError(
                message=f"Local/loopback address '{stripped}' is invalid for cloud provider '{provider_name}'.",
                user_friendly_message=(
                    f"Invalid endpoint for {provider_name}: '{stripped}' points to a local address or Ollama port. "
                    "Cloud providers require an official cloud API endpoint (e.g. https://api.groq.com/openai/v1)."
                ),
            )
            
    return stripped


def validate_endpoint_url(url: Optional[str], allow_local: bool = True, provider_name: str = "") -> str:
    """Validate HTTP/HTTPS endpoint URL format."""
    effective_prov = provider_name if provider_name else ("ollama" if allow_local else "cloud")
    return normalize_endpoint_url(url, provider_name=effective_prov)


def validate_generation_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate generation hyperparameters like temperature, top_p, and max_tokens."""
    clean: Dict[str, Any] = {}
    
    if "temperature" in params and params["temperature"] is not None:
        try:
            temp = float(params["temperature"])
            if not (0.0 <= temp <= 2.0):
                raise ValueError()
            clean["temperature"] = temp
        except (ValueError, TypeError):
            raise SecurityValidationError(
                message=f"Invalid temperature: {params['temperature']}",
                user_friendly_message="Temperature must be a number between 0.0 and 2.0.",
            )
            
    if "max_tokens" in params and params["max_tokens"] is not None:
        try:
            tokens = int(params["max_tokens"])
            if tokens <= 0 or tokens > 32768:
                raise ValueError()
            clean["max_tokens"] = tokens
        except (ValueError, TypeError):
            raise SecurityValidationError(
                message=f"Invalid max_tokens: {params['max_tokens']}",
                user_friendly_message="Max tokens must be a positive integer up to 32768.",
            )
            
    if "top_p" in params and params["top_p"] is not None:
        try:
            top_p = float(params["top_p"])
            if not (0.0 <= top_p <= 1.0):
                raise ValueError()
            clean["top_p"] = top_p
        except (ValueError, TypeError):
            raise SecurityValidationError(
                message=f"Invalid top_p: {params['top_p']}",
                user_friendly_message="Top-P must be a number between 0.0 and 1.0.",
            )
            
    return clean
