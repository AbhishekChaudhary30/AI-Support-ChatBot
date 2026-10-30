"""Core package providing configuration, exceptions, and logging."""

from support_bot.core.config import AppSettings, SessionModelConfig, get_settings
from support_bot.core.exceptions import (
    ConfigurationError,
    ModelIncompatibleError,
    ModelNotFoundError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    RetrievalError,
    SecurityValidationError,
    SupportBotException,
    WorkflowError,
)
from support_bot.core.logging_config import setup_logging

__all__ = [
    "AppSettings",
    "SessionModelConfig",
    "get_settings",
    "SupportBotException",
    "ConfigurationError",
    "SecurityValidationError",
    "ProviderError",
    "ProviderConnectionError",
    "ProviderAuthenticationError",
    "ModelNotFoundError",
    "ModelIncompatibleError",
    "ProviderRateLimitError",
    "RetrievalError",
    "WorkflowError",
    "setup_logging",
]
