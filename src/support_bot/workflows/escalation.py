"""Human Support Escalation Workflow.

Handles escalation requests when a customer needs to connect with human representatives.
Generates structured escalation summary cards containing contextual dialogue history
without making false claims about automatic ticket creation.
"""

from datetime import datetime, timezone
from typing import List, Optional
from support_bot.conversation.context import ChatMessage, MessageRole


class SupportEscalationManager:
    """Manages escalation workflows and formats support briefing cards."""

    @staticmethod
    def generate_escalation_card(
        query: str,
        category: str = "General Assistance",
        session_id: str = "default_session",
        recent_messages: Optional[List[ChatMessage]] = None,
    ) -> str:
        """Construct a formatted Markdown escalation card for human support review."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Format recent context turns
        context_lines: List[str] = []
        if recent_messages:
            for msg in recent_messages[-4:]:
                prefix = "Customer" if msg.role == MessageRole.USER else "AI Assistant"
                # Truncate lengthy turns to keep summary readable
                snippet = msg.content[:180] + ("..." if len(msg.content) > 180 else "")
                context_lines.append(f"- **{prefix}:** {snippet}")
        context_str = "\n".join(context_lines) if context_lines else "- No prior turns recorded."

        return (
            "### 👤 Human Support Escalation Request\n\n"
            "I understand you would like to speak directly with a human support representative. "
            "Our human customer support team is available **Monday through Friday, 9:00 AM – 6:00 PM EST**.\n\n"
            "Here is your compiled **Support Escalation Briefing**: You can copy this summary to provide "
            "our staff with complete context immediately.\n\n"
            "```text\n"
            f"=== CUSTOMER SUPPORT ESCALATION BRIEFING ===\n"
            f"Timestamp:       {now_str}\n"
            f"Session ID:      {session_id}\n"
            f"Category:        {category}\n"
            f"Primary Inquiry: {query}\n\n"
            f"Recent Context:\n"
            f"{context_str}\n"
            f"============================================\n"
            "```\n\n"
            "**Recommended Next Steps:**\n"
            "1. **Email:** Forward this summary to `help@support.example.com`.\n"
            "2. **Help Desk Portal:** Paste into a new ticket at `support.example.com/tickets`.\n\n"
            "> [!NOTE]\n"
            "> **Transparency Notice:** This is an AI assistant. No external ticket has been automatically created, "
            "> and no personal information was transmitted outside your active session."
        )
