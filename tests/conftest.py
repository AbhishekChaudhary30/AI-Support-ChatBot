"""Pytest fixtures and configuration."""

import pytest
from support_bot.core.config import AppSettings, SessionModelConfig
from support_bot.retrieval.chunking import DocumentChunk
from support_bot.retrieval.loader import SupportDocument
from support_bot.security.secrets import SessionSecret


@pytest.fixture
def mock_app_settings() -> AppSettings:
    """Fixture providing clean test AppSettings."""
    return AppSettings(
        app_name="AI Customer Support Test",
        app_env="test",
        log_level="DEBUG",
        default_provider="ollama",
        ollama_base_url="http://localhost:11434",
        default_ollama_model="llama3.2:latest",
        max_message_length=1000,
        request_timeout_seconds=5,
    )


@pytest.fixture
def sample_session_config() -> SessionModelConfig:
    """Fixture providing standard session model configuration."""
    return SessionModelConfig(
        provider_name="ollama",
        model_name="llama3.2:latest",
        endpoint_url="http://localhost:11434",
        temperature=0.2,
        max_tokens=512,
    )


@pytest.fixture
def sample_session_secret() -> SessionSecret:
    """Fixture providing valid session secret."""
    return SessionSecret("sk-proj-test1234567890abcdefghijklmnopqrstuvwxyz")


@pytest.fixture
def sample_support_document() -> SupportDocument:
    """Fixture providing a mock support document."""
    return SupportDocument(
        title="Test Billing FAQ",
        content="We offer a 14-day refund policy on all standard subscriptions.",
        source_path="knowledge_base/faqs/billing.md",
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Fixture providing a list of document chunks."""
    return [
        DocumentChunk(
            chunk_id="chunk_1",
            content="We offer a 14-day refund policy on all standard subscriptions.",
            source_title="Billing Policy",
            source_path="knowledge_base/faqs/billing.md",
            chunk_index=0,
        ),
        DocumentChunk(
            chunk_id="chunk_2",
            content="Support hours are Monday through Friday 9am to 6pm EST.",
            source_title="Support Hours",
            source_path="knowledge_base/faqs/hours.md",
            chunk_index=1,
        ),
    ]
