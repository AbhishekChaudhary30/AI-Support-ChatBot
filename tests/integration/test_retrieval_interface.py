"""Integration tests verifying the Knowledge Base Retrieval Subsystem interfaces."""

import pytest
from support_bot.retrieval.chunking import TextChunker
from support_bot.retrieval.embeddings import DeterministicFallbackEmbeddingProvider
from support_bot.retrieval.loader import KnowledgeBaseLoader
from support_bot.retrieval.retriever import InMemoryVectorRetriever


@pytest.mark.integration
def test_knowledge_base_loader():
    """Verify sample FAQ document is found and loaded correctly."""
    loader = KnowledgeBaseLoader(directory_path="knowledge_base")
    docs = loader.load_documents()
    assert len(docs) >= 1
    sample = docs[0]
    assert "FAQ" in sample.title or "Sample" in sample.title
    assert "refund" in sample.content.lower() or "password" in sample.content.lower()


@pytest.mark.integration
def test_document_chunker_boundaries(sample_support_document):
    """Verify document chunker preserves content and respects chunk size."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.split_document(sample_support_document)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.source_title == sample_support_document.title
        assert len(c.content) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_retrieval_pipeline():
    """Verify loader -> chunker -> embedding -> retriever index -> query retrieval flow."""
    # 1. Load
    loader = KnowledgeBaseLoader(directory_path="knowledge_base")
    docs = loader.load_documents()
    assert len(docs) > 0

    # 2. Chunk
    chunker = TextChunker(chunk_size=300, chunk_overlap=30)
    chunks = chunker.split_documents(docs)
    assert len(chunks) > 0

    # 3. Index & Retrieve
    embedding_provider = DeterministicFallbackEmbeddingProvider()
    retriever = InMemoryVectorRetriever(embedding_provider=embedding_provider)
    await retriever.index_chunks(chunks)
    assert retriever.is_ready() is True

    # 4. Search query
    results = await retriever.retrieve(query="What is the refund policy?", top_k=2)
    assert len(results) > 0
    top_result = results[0]
    assert top_result.score >= 0.0
    citation = top_result.to_citation_dict()
    assert "title" in citation
    assert "snippet" in citation
    assert "score" in citation
