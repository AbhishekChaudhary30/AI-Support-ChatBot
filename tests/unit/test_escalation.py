"""Unit tests for Support Escalation workflow."""

import pytest
from support_bot.conversation.context import ChatMessage, MessageRole
from support_bot.workflows.escalation import SupportEscalationManager


@pytest.mark.unit
def test_escalation_card_structure():
    """Verify escalation card formats briefing and includes transparency notice."""
    messages = [
        ChatMessage(role=MessageRole.USER, content="My payment failed three times."),
        ChatMessage(role=MessageRole.ASSISTANT, content="I can help review accepted payment methods."),
    ]
    card = SupportEscalationManager.generate_escalation_card(
        query="Connect me with an agent now",
        category="Payment Issue",
        session_id="session_xyz_123",
        recent_messages=messages,
    )
    assert "Human Support Escalation Request" in card
    assert "session_xyz_123" in card
    assert "Payment Issue" in card
    assert "My payment failed three times." in card
    assert "Transparency Notice" in card
    assert "No external ticket has been automatically created" in card
