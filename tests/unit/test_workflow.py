"""Unit tests for conversation management and workflow coordinator."""

import pytest
from support_bot.conversation.manager import ConversationManager
from support_bot.core.config import SessionModelConfig
from support_bot.workflows.support_workflow import SupportWorkflowCoordinator


@pytest.mark.unit
def test_conversation_context_tracking():
    """Verify messages are recorded in sequence."""
    cm = ConversationManager(session_id="test_session_1")
    cm.record_user_message("Hello support")
    cm.record_assistant_message("Hello! How can I help you today?")
    
    messages = cm.context.get_messages()
    assert len(messages) == 2
    assert messages[0].content == "Hello support"
    assert messages[1].content == "Hello! How can I help you today?"


@pytest.mark.unit
def test_session_isolation():
    """Verify distinct session IDs do not leak message state across sessions."""
    cm1 = ConversationManager(session_id="session_A")
    cm2 = ConversationManager(session_id="session_B")
    
    cm1.record_user_message("Message for session A only")
    
    assert cm1.context.message_count == 1
    assert cm2.context.message_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_workflow_coordinator_catches_invalid_input():
    """Verify coordinator intercepts injection and invalid input safely."""
    coordinator = SupportWorkflowCoordinator(session_id="test_session")
    session_config = SessionModelConfig(provider_name="ollama", model_name="llama3.2")
    
    result = await coordinator.process_user_query(
        raw_message="   ",
        session_config=session_config,
    )
    assert result.is_error is True
    assert "cannot be empty" in result.answer.lower()
