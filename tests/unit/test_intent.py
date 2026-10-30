"""Unit tests for Support Intent Classification."""

import pytest
from support_bot.workflows.intent import IntentClassifier, SupportIntentCategory


@pytest.fixture
def classifier():
    return IntentClassifier()


@pytest.mark.unit
def test_classify_human_escalation(classifier):
    queries = [
        "I want to speak to a human please",
        "Connect me to an agent",
        "Can I talk to a real person?",
        "I need to escalate this issue",
        "Transfer me to customer support staff",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.HUMAN_ESCALATION
        assert result.requires_retrieval is False


@pytest.mark.unit
def test_classify_refund_cancellation(classifier):
    queries = [
        "What is your refund policy?",
        "Can I get my money back?",
        "How do I cancel my subscription?",
        "Where can I find my invoice receipt?",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.REFUND_CANCELLATION
        assert result.requires_retrieval is True


@pytest.mark.unit
def test_classify_account_access(classifier):
    queries = [
        "How do I reset my password?",
        "My account is locked out",
        "How do I enable two-factor authentication?",
        "I want to change my email address",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.ACCOUNT_ACCESS
        assert result.requires_retrieval is True


@pytest.mark.unit
def test_classify_order_shipping(classifier):
    queries = [
        "What are your standard shipping times?",
        "How do I track my order delivery?",
        "My shipment is delayed by two days",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.ORDER_SHIPPING
        assert result.requires_retrieval is True


@pytest.mark.unit
def test_classify_troubleshooting(classifier):
    queries = [
        "The web application is frozen and unresponsive",
        "How do I clear my browser cache and cookies?",
        "I am seeing an HTTP 500 error",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.TROUBLESHOOTING
        assert result.requires_retrieval is True


@pytest.mark.unit
def test_classify_general_chat(classifier):
    queries = [
        "Hello!",
        "Good morning",
        "Thank you so much",
    ]
    for q in queries:
        result = classifier.classify(q)
        assert result.category == SupportIntentCategory.GENERAL_CHAT
        assert result.requires_retrieval is False


@pytest.mark.unit
def test_classify_unclear():
    classifier = IntentClassifier()
    result = classifier.classify("..")
    assert result.category == SupportIntentCategory.UNCLEAR_AMBIGUOUS
