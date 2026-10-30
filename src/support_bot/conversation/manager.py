"""Conversation session management.

Bridges raw conversation history with LangChain chat models and formats prompts cleanly.
"""

from typing import List, Optional
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from support_bot.conversation.context import ChatMessage, ConversationContext, MessageRole

DEFAULT_SYSTEM_PROMPT = (
    "You are a professional, helpful, and concise AI Customer Support Assistant. "
    "Your objective is to provide accurate, transparent answers to customer questions. "
    "If you are provided with retrieved context from the company knowledge base, prioritize "
    "that information. If you cannot answer a question based on available support documentation, "
    "politely inform the user and suggest escalating to human support."
)


class ConversationManager:
    """Manages active session context and prepares prompt message sequences."""

    def __init__(self, session_id: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.context = ConversationContext(session_id=session_id)

    def record_user_message(self, content: str) -> ChatMessage:
        """Record an incoming user message."""
        return self.context.add_message(role=MessageRole.USER, content=content)

    def record_assistant_message(self, content: str, sources: Optional[List] = None) -> ChatMessage:
        """Record an assistant response along with any source citations."""
        return self.context.add_message(role=MessageRole.ASSISTANT, content=content, sources=sources)

    def build_messages_for_llm(self, query: str, retrieved_context: Optional[str] = None) -> List[BaseMessage]:
        """Assemble the complete prompt sequence including system prompt, prior turns, and optional context.
        
        Args:
            query: The latest user question.
            retrieved_context: Optional text extracted from knowledge base retrieval.
            
        Returns:
            List of LangChain BaseMessage objects ready for model invocation.
        """
        messages: List[BaseMessage] = [SystemMessage(content=self.system_prompt)]
        
        # Add prior conversational turns for conversational continuity
        for msg in self.context.get_messages():
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=msg.content))
                
        # Format current user query with retrieved context if available
        if retrieved_context:
            final_user_content = (
                f"Knowledge Base Context:\n---\n{retrieved_context}\n---\n\n"
                f"Customer Question: {query}\n\n"
                "Please answer the customer question using the context above. If the context does not contain the answer, "
                "state so clearly and offer helpful guidance."
            )
        else:
            final_user_content = query
            
        messages.append(HumanMessage(content=final_user_content))
        return messages

    def clear(self) -> None:
        """Clear session conversational context."""
        self.context.clear()
