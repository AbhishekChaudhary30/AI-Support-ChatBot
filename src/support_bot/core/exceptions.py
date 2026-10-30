"""Custom application exceptions for AI Customer Support Chatbot.

Provides a unified, structured hierarchy of exceptions to ensure sensitive details,
API keys, or internal stack traces are never exposed indiscriminately to end users.
"""

from typing import Optional


class SupportBotException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.user_friendly_message = user_friendly_message or (
            "An internal error occurred while processing your request. Please try again."
        )


class ConfigurationError(SupportBotException):
    """Raised when application or provider settings are missing or invalid."""

    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=user_friendly_message
            or "Configuration error: Please verify your application or model settings.",
        )


class SecurityValidationError(SupportBotException):
    """Raised when user input violates validation boundaries or security policies."""

    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=user_friendly_message
            or "Input validation failed: Your message could not be processed.",
        )


class ProviderError(SupportBotException):
    """Base exception for model provider and inference failures."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        self.provider_name = provider_name
        full_msg = f"[{provider_name}] {message}"
        super().__init__(
            message=full_msg,
            user_friendly_message=user_friendly_message
            or f"Inference provider '{provider_name}' encountered an error.",
        )


class ProviderConnectionError(ProviderError):
    """Raised when a model provider endpoint is unreachable or times out."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        super().__init__(
            provider_name=provider_name,
            message=message,
            user_friendly_message=user_friendly_message
            or f"Could not connect to provider '{provider_name}'. Please verify the service is running and reachable.",
        )


class ProviderAuthenticationError(ProviderError):
    """Raised when credentials are missing, rejected, or expired."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        super().__init__(
            provider_name=provider_name,
            message=message,
            user_friendly_message=user_friendly_message
            or f"Authentication failed for '{provider_name}'. Please check your API key in Model Configuration.",
        )


class ModelNotFoundError(ProviderError):
    """Raised when the specified model identifier is not available on the provider."""

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        self.model_name = model_name
        super().__init__(
            provider_name=provider_name,
            message=f"Model '{model_name}' not found: {message}",
            user_friendly_message=user_friendly_message
            or f"Model '{model_name}' was not found on provider '{provider_name}'.",
        )


class ModelIncompatibleError(ProviderError):
    """Raised when the requested operation or parameter is unsupported by the model."""

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        self.model_name = model_name
        super().__init__(
            provider_name=provider_name,
            message=f"Model '{model_name}' incompatible: {message}",
            user_friendly_message=user_friendly_message
            or f"The selected model '{model_name}' does not support this operation.",
        )


class ProviderRateLimitError(ProviderError):
    """Raised when the provider enforces a rate limit or quota exhaustion."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        user_friendly_message: Optional[str] = None,
    ):
        super().__init__(
            provider_name=provider_name,
            message=message,
            user_friendly_message=user_friendly_message
            or f"Rate limit reached for '{provider_name}'. Please wait a moment before trying again.",
        )


class RetrievalError(SupportBotException):
    """Raised when knowledge base document loading, chunking, or retrieval fails."""

    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=user_friendly_message
            or "Knowledge base retrieval error: Unable to load or query support documents.",
        )


class WorkflowError(SupportBotException):
    """Raised when support workflow automation or intent handling fails."""

    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=user_friendly_message
            or "Support workflow processing failed. Escalating to standard assistance.",
        )
