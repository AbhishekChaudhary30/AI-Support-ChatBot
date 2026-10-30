"""Unit tests for heading-aware TextChunker."""

import pytest
from support_bot.retrieval.chunking import TextChunker
from support_bot.retrieval.loader import SupportDocument


@pytest.mark.unit
def test_heading_aware_chunking():
    """Verify Markdown headers create distinct cohesive chunks."""
    doc_content = (
        "# Main Title\n\n"
        "## Refund Policy\n"
        "We offer a 14-day refund policy for all subscribers.\n\n"
        "## Cancellation Policy\n"
        "You can cancel your plan anytime from Billing & Plans."
    )
    doc = SupportDocument(
        title="Test Policies",
        content=doc_content,
        source_path="knowledge_base/faqs/test.md",
    )
    chunker = TextChunker(chunk_size=400, chunk_overlap=50, preserve_headings=True)
    chunks = chunker.split_document(doc)

    assert len(chunks) >= 2
    headings = [c.section_heading for c in chunks]
    assert "Refund Policy" in headings
    assert "Cancellation Policy" in headings
    assert "14-day refund" in chunks[0].content or "14-day refund" in chunks[1].content


@pytest.mark.unit
def test_chunker_parameter_validation():
    """Verify invalid chunk size and overlap raise ValueError."""
    with pytest.raises(ValueError):
        TextChunker(chunk_size=50)  # Too small

    with pytest.raises(ValueError):
        TextChunker(chunk_size=200, chunk_overlap=250)  # Overlap >= size
