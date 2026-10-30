"""Unit tests verifying strict multi-user session isolation.

Guarantees that distinct user sessions:
1. Cannot access another session's API keys or credentials.
2. Cannot read or leak another session's conversational turns or context.
3. Maintain isolated workflow coordinators and model configurations.
"""

import pytest
from support_bot.conversation.context import MessageRole
from support_bot.conversation.manager import ConversationManager
from support_bot.core.config import SessionModelConfig
from support_bot.security.secrets import SessionSecret
from support_bot.workflows.support_workflow import SupportWorkflowCoordinator


@pytest.mark.unit
def test_conversation_history_session_isolation():
    """Verify messages added in Session A are completely invisible to Session B."""
    cm_a = ConversationManager(session_id="user_session_alice")
    cm_b = ConversationManager(session_id="user_session_bob")

    cm_a.record_user_message("Alice's confidential question about account #12345")
    cm_a.record_assistant_message("Answer for Alice only.")

    assert cm_a.context.message_count == 2
    assert cm_b.context.message_count == 0
    assert len(cm_b.context.get_messages()) == 0


@pytest.mark.unit
def test_credential_session_isolation():
    """Verify API keys held in Session A do not contaminate Session B."""
    secret_a = SessionSecret("mock-alice-session-secret-987654321")
    secret_b = SessionSecret(None)

    assert secret_a.is_configured() is True
    assert secret_b.is_configured() is False
    assert secret_b.get_secret_value() is None

    # Clearing Session A's secret does not affect Session B
    secret_a.clear()
    assert secret_a.is_configured() is False


@pytest.mark.unit
def test_workflow_coordinator_session_isolation():
    """Verify workflow coordinators maintain isolated conversational state."""
    cm_a = ConversationManager(session_id="session_A")
    cm_b = ConversationManager(session_id="session_B")

    coord_a = SupportWorkflowCoordinator(session_id="session_A", conversation_manager=cm_a)
    coord_b = SupportWorkflowCoordinator(session_id="session_B", conversation_manager=cm_b)

    assert coord_a.session_id != coord_b.session_id
    assert coord_a.conversation_manager is not coord_b.conversation_manager

    coord_a.conversation_manager.record_user_message("Query from A")
    assert len(coord_b.conversation_manager.context.get_messages()) == 0


@pytest.mark.unit
def test_independent_session_clear():
    """Verify clearing credentials in Session A does not affect Session B's active key."""
    secret_a = SessionSecret("mock-key-alice-12345")
    secret_b = SessionSecret("mock-key-bob-67890")

    assert secret_a.is_configured() is True
    assert secret_b.is_configured() is True

    # User A clicks "Clear Session Secrets"
    secret_a.clear()

    # Session A is cleared; Session B retains its active key undisturbed
    assert secret_a.is_configured() is False
    assert secret_a.get_secret_value() is None
    assert secret_b.is_configured() is True
    assert secret_b.get_secret_value() == "mock-key-bob-67890"


@pytest.mark.unit
def test_provider_client_credential_isolation():
    """Verify provider adapters instantiate distinct clients with their respective session credentials."""
    from support_bot.providers.registry import registry
    openai_provider = registry.get_provider("openai")

    config_a = SessionModelConfig(provider_name="openai", model_name="gpt-4o-mini")
    config_b = SessionModelConfig(provider_name="openai", model_name="gpt-4o-mini")

    secret_a = SessionSecret("mock-key-alice")
    secret_b = SessionSecret("mock-key-bob")

    client_a = openai_provider.get_chat_model(config_a, secret_a)
    client_b = openai_provider.get_chat_model(config_b, secret_b)

    # Clients are distinct instances
    assert client_a is not client_b
    assert client_a.openai_api_key.get_secret_value() == "mock-key-alice"
    assert client_b.openai_api_key.get_secret_value() == "mock-key-bob"

