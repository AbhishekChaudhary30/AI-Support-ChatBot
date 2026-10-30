"""Retriever implementation, vector store abstraction, and atomic rebuilding.

Indexes document chunks, computes cosine similarity, and supports score thresholding
to guard against irrelevant context generation.
"""

from abc import ABC, abstractmethod
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from support_bot.retrieval.chunking import DocumentChunk, TextChunker
from support_bot.retrieval.embeddings import BaseEmbeddingProvider, DeterministicFallbackEmbeddingProvider
from support_bot.retrieval.loader import KnowledgeBaseLoader
from support_bot.retrieval.manifest import IndexManifest, IndexStatus, ManifestManager


class RetrievalResult(BaseModel):
    """Retrieved document chunk accompanied by relevance score."""
    chunk: DocumentChunk
    score: float

    def to_citation_dict(self) -> Dict[str, Any]:
        """Format citation for frontend presentation."""
        return {
            "title": self.chunk.source_title,
            "section": self.chunk.section_heading or "General",
            "source": self.chunk.source_path,
            "snippet": self.chunk.content[:240] + ("..." if len(self.chunk.content) > 240 else ""),
            "score": round(self.score, 3),
        }


class BaseRetriever(ABC):
    """Abstract interface for knowledge base retrievers."""

    @abstractmethod
    async def index_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Embed and index a list of document chunks."""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> List[RetrievalResult]:
        """Retrieve most relevant chunks for a customer query above min_score."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check whether the vector index contains documents."""
        pass


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class InMemoryVectorRetriever(BaseRetriever):
    """In-memory vector retriever with atomic rebuild, scoring threshold, and manifest tracking."""

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        manifest_manager: Optional[ManifestManager] = None,
        default_min_score: float = 0.20,
    ):
        self.embedding_provider = embedding_provider or DeterministicFallbackEmbeddingProvider()
        self.manifest_manager = manifest_manager or ManifestManager()
        self.default_min_score = default_min_score
        self._chunks: List[DocumentChunk] = []
        self._vectors: List[List[float]] = []
        self._status: IndexStatus = IndexStatus.NOT_INITIALIZED

    @property
    def status(self) -> IndexStatus:
        return self._status

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def is_ready(self) -> bool:
        """Check if any chunks have been indexed and index is marked ready."""
        return self._status == IndexStatus.READY and len(self._chunks) > 0

    def clear(self) -> None:
        """Empty the active vector index."""
        self._chunks.clear()
        self._vectors.clear()
        self._status = IndexStatus.NOT_INITIALIZED

    async def index_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Embed and store document chunks in memory."""
        if not chunks:
            self._status = IndexStatus.READY
            return

        self._status = IndexStatus.INITIALIZING
        texts = [c.content for c in chunks]
        vectors = await self.embedding_provider.embed_documents(texts)
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)
        self._status = IndexStatus.READY

    async def rebuild_from_knowledge_base(
        self,
        loader: KnowledgeBaseLoader,
        chunker: TextChunker,
    ) -> Dict[str, Any]:
        """Perform an atomic index rebuild from raw files."""
        # Snapshot previous state for safe atomic rollback on failure
        prev_chunks = list(self._chunks)
        prev_vectors = list(self._vectors)
        prev_status = self._status

        self._status = IndexStatus.INITIALIZING
        try:
            docs, report = loader.load_with_report()
            if not docs:
                self.clear()
                self._status = IndexStatus.READY
                self.manifest_manager.mark_ready([], 0, self.embedding_provider.model_name)
                return {
                    "success": True,
                    "documents_indexed": 0,
                    "chunks_indexed": 0,
                    "skipped_files": report.skipped_files,
                }

            chunks = chunker.split_documents(docs)
            texts = [c.content for c in chunks]
            vectors = await self.embedding_provider.embed_documents(texts)

            # Atomic swap only after full successful generation
            self._chunks = chunks
            self._vectors = vectors
            self._status = IndexStatus.READY

            self.manifest_manager.mark_ready(docs, len(chunks), self.embedding_provider.model_name)
            return {
                "success": True,
                "documents_indexed": len(docs),
                "chunks_indexed": len(chunks),
                "skipped_files": report.skipped_files,
            }
        except Exception as e:
            # Preserve existing working index if available to maintain service availability
            if prev_status == IndexStatus.READY and prev_chunks:
                self._chunks = prev_chunks
                self._vectors = prev_vectors
                self._status = IndexStatus.READY
            else:
                self._status = IndexStatus.ERROR
            self.manifest_manager.mark_error(str(e))
            raise e

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """Rank and return top_k matching chunks above score threshold."""
        if not self._chunks:
            return []

        threshold = min_score if min_score is not None else self.default_min_score
        query_vec = await self.embedding_provider.embed_query(query)
        scored: List[RetrievalResult] = []

        for chunk, chunk_vec in zip(self._chunks, self._vectors):
            score = _cosine_similarity(query_vec, chunk_vec)
            if score >= threshold:
                scored.append(RetrievalResult(chunk=chunk, score=score))

        # Sort descending by score
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
