"""Conversation package."""

from support_bot.conversation.context import (
    ChatMessage,
    ConversationContext,
    MessageRole,
)
from support_bot.conversation.manager import ConversationManager

__all__ = [
    "ChatMessage",
    "ConversationContext",
    "MessageRole",
    "ConversationManager",
]
