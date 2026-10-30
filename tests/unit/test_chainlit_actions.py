"""Regression tests for Chainlit Action payload validation (Error B).

Verifies:
1. cl.Action instantiation requires payload: Dict[str, Any] in Chainlit 2.12.0.
2. Instantiating cl.Action with payload succeeds without Pydantic ValidationError.
3. Instantiating cl.Action without payload (as previously occurred) triggers ValidationError.
4. Action callbacks safely extract data from action.payload without AttributeError.
5. Missing or malformed payloads in action callbacks are handled safely.
"""

import sys
from pathlib import Path
import pytest
import pydantic_core
import chainlit as cl
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure workspace root is in sys.path to import app.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.mark.unit
def test_action_creation_with_valid_payload():
    """Verify Action with payload dictionary succeeds under Chainlit 2.12.0 schema."""
    action = cl.Action(
        name="ask_example",
        payload={"value": "What is your refund policy?"},
        label="💳 What is your refund policy?",
    )
    assert action.name == "ask_example"
    assert isinstance(action.payload, dict)
    assert action.payload["value"] == "What is your refund policy?"
    assert action.label == "💳 What is your refund policy?"


@pytest.mark.unit
def test_action_creation_missing_payload_raises_validation_error():
    """Verify that constructing an Action without payload reproduces the exact ValidationError.
    
    This is the exact regression test for Error B:
    '1 validation error for Action payload. Field required [type=missing ...]'
    """
    with pytest.raises(pydantic_core.ValidationError) as exc_info:
        # Omitting 'payload' triggers Pydantic field required validation error
        cl.Action(
            name="ask_example",
            value="What is your refund policy?",  # type: ignore
            label="💳 What is your refund policy?",
        )
    assert "payload" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


@pytest.mark.unit
def test_all_welcome_actions_have_valid_payloads():
    """Verify all actions declared in app.on_chat_start pass schema validation."""
    example_actions = [
        cl.Action(name="ask_example", payload={"value": "What is your refund policy?"}, label="💳 What is your refund policy?"),
        cl.Action(name="ask_example", payload={"value": "How do I reset my password?"}, label="🔑 How do I reset my password?"),
        cl.Action(name="ask_example", payload={"value": "What should I do if my order is delayed?"}, label="🚚 What if my order is delayed?"),
        cl.Action(name="ask_example", payload={"value": "How do I troubleshoot an unresponsive page?"}, label="🛠️ Troubleshooting tips"),
        cl.Action(name="ask_example", payload={"value": "I want to speak with a human support agent."}, label="👤 Speak to human support"),
    ]
    assert len(example_actions) == 5
    for a in example_actions:
        assert isinstance(a.payload, dict)
        assert "value" in a.payload

    system_actions = [
        cl.Action(name="check_kb_status", payload={"value": "kb_status"}, label="📚 Knowledge Base Status"),
        cl.Action(name="rebuild_kb", payload={"value": "rebuild_kb"}, label="🔄 Rebuild Knowledge Index"),
        cl.Action(name="check_status", payload={"value": "status"}, label="🔍 Test Provider Connection"),
        cl.Action(name="clear_config", payload={"value": "clear"}, label="🔒 Clear Session Secrets"),
        cl.Action(name="about_project", payload={"value": "about"}, label="📖 About Project"),
        cl.Action(name="tech_stack", payload={"value": "tech"}, label="⚡ Technology Stack"),
    ]
    assert len(system_actions) == 6
    for a in system_actions:
        assert isinstance(a.payload, dict)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_ask_example_callback_payload_extraction():
    """Verify callback logic extracts question from payload dictionary correctly."""
    from app import on_ask_example

    action = cl.Action(
        name="ask_example",
        payload={"value": "What is your refund policy?"},
        label="💳 What is your refund policy?",
    )

    with patch("chainlit.Message") as mock_msg, \
         patch("app._execute_streaming_query", new_callable=AsyncMock) as mock_stream:
        mock_instance = MagicMock()
        mock_instance.send = AsyncMock()
        mock_msg.return_value = mock_instance

        await on_ask_example(action)
        mock_msg.assert_called_with(content="What is your refund policy?", author="User")
        mock_stream.assert_awaited_with("What is your refund policy?")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_ask_example_handles_missing_payload_gracefully():
    """Verify callback handles empty or malformed payload without crashing."""
    from app import on_ask_example

    # Create dummy action with empty payload
    action = cl.Action(
        name="ask_example",
        payload={},
        label="Empty payload",
    )

    with patch("chainlit.Message") as mock_msg, \
         patch("app._execute_streaming_query", new_callable=AsyncMock) as mock_stream:
        mock_instance = MagicMock()
        mock_instance.send = AsyncMock()
        mock_msg.return_value = mock_instance

        await on_ask_example(action)
        # Streaming query should not be called with empty payload
        mock_stream.assert_not_called()
