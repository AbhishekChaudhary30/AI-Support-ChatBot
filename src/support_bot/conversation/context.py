"""Conversation context and message representation data structures.

Maintains in-memory conversation state for an active session with strict session scoping.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role associated with a conversational turn."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Individual message within a conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationContext:
    """Manages conversational history for a single user session."""

    def __init__(self, session_id: str, max_turns: int = 20):
        self.session_id = session_id
        self.max_turns = max_turns
        self._messages: List[ChatMessage] = []

    def add_message(
        self,
        role: MessageRole,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Append a message to the conversation."""
        msg = ChatMessage(
            role=role,
            content=content,
            sources=sources,
            metadata=metadata or {},
        )
        self._messages.append(msg)
        
        # Enforce history boundary to keep context manageable
        if len(self._messages) > self.max_turns * 2:
            self._messages = self._messages[-(self.max_turns * 2):]
            
        return msg

    def get_messages(self) -> List[ChatMessage]:
        """Return shallow copy of all messages in current session."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear conversation history for this session."""
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)
