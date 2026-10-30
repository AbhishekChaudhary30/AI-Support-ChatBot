"""Base Model Provider interface and provider capabilities.

Defines the contract that all LLM provider adapters must implement.
Ensures provider independence, modularity, streaming generation, and strict session isolation.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from support_bot.core.config import SessionModelConfig
from support_bot.security.secrets import SessionSecret


class ProviderCapabilities:
    """Declared capabilities and constraints of a model provider adapter."""

    def __init__(
        self,
        provider_name: str,
        display_name: str,
        is_local: bool = False,
        requires_api_key: bool = True,
        supports_streaming: bool = True,
        supports_tools: bool = False,
        default_endpoint: Optional[str] = None,
        default_model: str = "",
        supported_models: Optional[List[str]] = None,
        description: str = "",
    ):
        self.provider_name = provider_name
        self.display_name = display_name
        self.is_local = is_local
        self.requires_api_key = requires_api_key
        self.supports_streaming = supports_streaming
        self.supports_tools = supports_tools
        self.default_endpoint = default_endpoint
        self.default_model = default_model
        self.supported_models = supported_models or []
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary for frontend presentation."""
        return {
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_local": self.is_local,
            "requires_api_key": self.requires_api_key,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
            "default_endpoint": self.default_endpoint,
            "default_model": self.default_model,
            "supported_models": self.supported_models,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<ProviderCapabilities provider={self.provider_name} model={self.default_model} local={self.is_local}>"


class BaseModelProvider(ABC):
    """Abstract base class for LLM provider adapters."""

    def __init__(self, capabilities: ProviderCapabilities):
        self.capabilities = capabilities

    @property
    def provider_name(self) -> str:
        return self.capabilities.provider_name

    @abstractmethod
    async def check_health(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Check whether the provider service/endpoint is reachable and authenticated.
        
        Returns:
            Dict containing:
                - 'is_healthy': bool
                - 'message': str
                - 'latency_ms': Optional[float]
                - 'details': Optional[Dict[str, Any]]
        """
        pass

    @abstractmethod
    async def list_available_models(
        self,
        endpoint_url: Optional[str] = None,
        session_secret: Optional[SessionSecret] = None,
    ) -> List[str]:
        """Discover models available for this provider."""
        pass

    @abstractmethod
    def validate_configuration(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> None:
        """Validate that the session-specific parameters and secrets satisfy provider requirements.
        
        Raises:
            ProviderAuthenticationError: If required credentials are missing.
            SecurityValidationError: If endpoints or parameters are invalid.
        """
        pass

    @abstractmethod
    def get_chat_model(
        self,
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> BaseChatModel:
        """Instantiate and return a LangChain ChatModel configured for this session.
        
        Must NOT cache the model instance across distinct user sessions when secrets are present.
        """
        pass

    async def astream(
        self,
        messages: List[BaseMessage],
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously from the provider."""
        chat_model = self.get_chat_model(session_config, session_secret)
        if self.capabilities.supports_streaming and hasattr(chat_model, "astream"):
            async for chunk in chat_model.astream(messages):
                if hasattr(chunk, "content"):
                    c = chunk.content
                    if isinstance(c, str) and c:
                        yield c
                    elif isinstance(c, list):
                        for part in c:
                            if isinstance(part, str) and part:
                                yield part
                            elif isinstance(part, dict) and part.get("text"):
                                yield part["text"]
                elif chunk:
                    yield str(chunk)
        else:
            # Fallback for models or integrations that do not support streaming
            response = await chat_model.ainvoke(messages)
            if hasattr(response, "content"):
                c = response.content
                if isinstance(c, str):
                    yield c
                elif isinstance(c, list):
                    for part in c:
                        if isinstance(part, str):
                            yield part
                        elif isinstance(part, dict) and part.get("text"):
                            yield part["text"]
            else:
                yield str(response)

    async def agenerate(
        self,
        messages: List[BaseMessage],
        session_config: SessionModelConfig,
        session_secret: Optional[SessionSecret] = None,
    ) -> str:
        """Generate complete response asynchronously."""
        chat_model = self.get_chat_model(session_config, session_secret)
        response = await chat_model.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)
