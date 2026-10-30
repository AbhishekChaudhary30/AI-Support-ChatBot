"""Support Intent Classification and Routing.

Classifies incoming customer messages into distinct support categories
using deterministic heuristic patterns and keyword signatures.
Determines whether knowledge base retrieval is required or if deterministic
actions (e.g., human escalation) should be triggered.
"""

from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class SupportIntentCategory(str, Enum):
    """Categorized customer support intents."""
    FAQ_INFORMATIONAL = "faq_informational"
    ACCOUNT_ACCESS = "account_access"
    ORDER_SHIPPING = "order_shipping"
    REFUND_CANCELLATION = "refund_cancellation"
    TROUBLESHOOTING = "troubleshooting"
    HUMAN_ESCALATION = "human_escalation"
    UNCLEAR_AMBIGUOUS = "unclear_ambiguous"
    GENERAL_CHAT = "general_chat"


class IntentClassificationResult(BaseModel):
    """Outcome of intent classification."""
    category: SupportIntentCategory
    confidence: float
    requires_retrieval: bool
    matched_keywords: List[str] = Field(default_factory=list)
    suggested_faq_topic: Optional[str] = None


# Intent signature patterns mapped to category and relevant topic
INTENT_PATTERNS: Dict[SupportIntentCategory, Dict[str, Any]] = {
    SupportIntentCategory.HUMAN_ESCALATION: {
        "patterns": [
            re.compile(r"\b(speak|talk)\s+to\s+(an?\s+|the\s+)?(real\s+)?(human|person|agent|representative|manager)\b", re.IGNORECASE),
            re.compile(r"\b(connect|transfer)\s+me\s+to\s+(an?\s+|the\s+)?(customer\s+support\s+|customer\s+)?(human|agent|person|rep|support\s+staff)\b", re.IGNORECASE),
            re.compile(r"\b(human\s+support|live\s+agent|real\s+person|human\s+help)\b", re.IGNORECASE),
            re.compile(r"\b(escalat(e|ion)|file\s+a\s+ticket|create\s+ticket|open\s+ticket)\b", re.IGNORECASE),
        ],
        "requires_retrieval": False,
        "topic": "support_escalation",
    },
    SupportIntentCategory.REFUND_CANCELLATION: {
        "patterns": [
            re.compile(r"\b(refund|money\s*back|cancel\s+(my\s+)?(subscription|order|plan)|return\s+policy|guarantee)\b", re.IGNORECASE),
            re.compile(r"\b(billing|charge|invoice|payment|receipt|credit\s+card)\b", re.IGNORECASE),
            re.compile(r"\b(prorated|upgrade|downgrade)\b", re.IGNORECASE),
        ],
        "requires_retrieval": True,
        "topic": "billing_refunds",
    },
    SupportIntentCategory.ACCOUNT_ACCESS: {
        "patterns": [
            re.compile(r"\b(password|reset\s+password|forgot\s+password|change\s+password)\b", re.IGNORECASE),
            re.compile(r"\b(account\s+(is\s+)?locked(\s*out)?|locked\s*out|unlock\s+account|login|sign\s*in|2fa|two[- ]factor|authenticator)\b", re.IGNORECASE),
            re.compile(r"\b(email\s+address|change\s+email)\b", re.IGNORECASE),
        ],
        "requires_retrieval": True,
        "topic": "account_security",
    },
    SupportIntentCategory.ORDER_SHIPPING: {
        "patterns": [
            re.compile(r"\b(shipping|delivery|shipment|courier|fedex|usps|dhl)\b", re.IGNORECASE),
            re.compile(r"\b(tracking|track\s+(my\s+)?(order|package)|where\s+is\s+my\s+package)\b", re.IGNORECASE),
            re.compile(r"\b(delayed|missing\s+order|lost\s+package|order\s+status)\b", re.IGNORECASE),
        ],
        "requires_retrieval": True,
        "topic": "orders_shipping",
    },
    SupportIntentCategory.TROUBLESHOOTING: {
        "patterns": [
            re.compile(r"\b(troubleshoot|bug|freeze|unresponsive|slow|crash|frozen|500\s+error)\b", re.IGNORECASE),
            re.compile(r"\b(clear\s+cache|cookies|browser|chrome|firefox|safari|edge)\b", re.IGNORECASE),
            re.compile(r"\b(mobile\s+app|pwa|ios|android)\b", re.IGNORECASE),
        ],
        "requires_retrieval": True,
        "topic": "product_troubleshooting",
    },
    SupportIntentCategory.GENERAL_CHAT: {
        "patterns": [
            re.compile(r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings)\b", re.IGNORECASE),
            re.compile(r"^(thanks|thank\s+you|bye|goodbye|see\s+you)\b", re.IGNORECASE),
            re.compile(r"^(who\s+are\s+you|what\s+can\s+you\s+do)\b", re.IGNORECASE),
        ],
        "requires_retrieval": False,
        "topic": "general",
    },
}


class IntentClassifier:
    """Classifies user queries into support intent categories."""

    def classify(self, text: str) -> IntentClassificationResult:
        """Classify user query text into a support intent."""
        cleaned = text.strip()
        if not cleaned or len(cleaned) < 3:
            return IntentClassificationResult(
                category=SupportIntentCategory.UNCLEAR_AMBIGUOUS,
                confidence=0.0,
                requires_retrieval=False,
            )

        # 1. Check priority intents (Human escalation highest priority)
        for category, config in INTENT_PATTERNS.items():
            matched: List[str] = []
            for pattern in config["patterns"]:
                match = pattern.search(cleaned)
                if match:
                    matched.append(match.group(0))

            if matched:
                return IntentClassificationResult(
                    category=category,
                    confidence=0.90 if len(matched) > 1 else 0.80,
                    requires_retrieval=config["requires_retrieval"],
                    matched_keywords=matched,
                    suggested_faq_topic=config.get("topic"),
                )

        # 2. General FAQ fallback if question contains question words
        if any(w in cleaned.lower() for w in ["what", "how", "why", "when", "where", "can i", "is there", "policy"]):
            return IntentClassificationResult(
                category=SupportIntentCategory.FAQ_INFORMATIONAL,
                confidence=0.65,
                requires_retrieval=True,
                suggested_faq_topic="general_faq",
            )

        # 3. Default to FAQ retrieval if query is substantial, otherwise unclear
        if len(cleaned.split()) >= 3:
            return IntentClassificationResult(
                category=SupportIntentCategory.FAQ_INFORMATIONAL,
                confidence=0.50,
                requires_retrieval=True,
                suggested_faq_topic="general_faq",
            )

        return IntentClassificationResult(
            category=SupportIntentCategory.UNCLEAR_AMBIGUOUS,
            confidence=0.20,
            requires_retrieval=False,
        )
