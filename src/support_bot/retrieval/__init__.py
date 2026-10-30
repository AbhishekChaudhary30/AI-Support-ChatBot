"""Retrieval subsystem package."""

from support_bot.retrieval.chunking import DocumentChunk, TextChunker
from support_bot.retrieval.embeddings import (
    BaseEmbeddingProvider,
    DeterministicFallbackEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from support_bot.retrieval.loader import (
    IngestionReport,
    KnowledgeBaseLoader,
    SupportDocument,
)
from support_bot.retrieval.manifest import (
    IndexManifest,
    IndexStatus,
    ManifestManager,
)
from support_bot.retrieval.retriever import (
    BaseRetriever,
    InMemoryVectorRetriever,
    RetrievalResult,
)

__all__ = [
    "SupportDocument",
    "IngestionReport",
    "KnowledgeBaseLoader",
    "DocumentChunk",
    "TextChunker",
    "BaseEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "DeterministicFallbackEmbeddingProvider",
    "IndexManifest",
    "IndexStatus",
    "ManifestManager",
    "BaseRetriever",
    "InMemoryVectorRetriever",
    "RetrievalResult",
]
