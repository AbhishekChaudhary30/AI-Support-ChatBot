"""Embedding provider interfaces and adapters.

Clearly separates embedding generation from chat model inference.
Provides adapters for local embeddings (Ollama), cloud embeddings (OpenAI),
and a deterministic test/fallback embedding provider for zero-dependency operation.
"""

from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import List, Optional
import httpx


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding models."""

    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of document strings."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate a vector embedding for a single search query."""
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using a local Ollama embedding model (e.g. nomic-embed-text)."""

    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434", dimension: int = 768):
        super().__init__(model_name=model_name, dimension=dimension)
        self.base_url = base_url.rstrip("/")

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model_name, "prompt": text},
                )
                if resp.status_code == 200:
                    embeddings.append(resp.json().get("embedding", []))
                else:
                    # Fallback to zero vector on error
                    embeddings.append([0.0] * self.dimension)
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        results = await self.embed_documents([text])
        return results[0] if results else [0.0] * self.dimension


# High-frequency English functional words down-weighted/filtered to improve semantic keyword matching
_STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "who", "will", "with", "do", "how", "can", "i",
    "my", "you", "your", "we", "our", "us", "if", "not", "so", "me",
}
_TOKEN_PATTERN = re.compile(r"\b[a-z0-9_-]+\b")


class DeterministicFallbackEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic hash-based embedding provider.
    
    Produces normalized 128-dimensional vectors from text with stop-word filtering and punctuation stripping.
    Enables local testing, offline verification, and failover without external network calls or heavy weights.
    """

    def __init__(self, dimension: int = 128):
        super().__init__(model_name="deterministic-fallback-128", dimension=dimension)

    def _hash_text(self, text: str) -> List[float]:
        tokens = [
            w for w in _TOKEN_PATTERN.findall(text.lower())
            if w not in _STOP_WORDS and len(w) > 1
        ]
        # If all words were stop words, fall back to all tokens
        if not tokens:
            tokens = _TOKEN_PATTERN.findall(text.lower())

        vector = [0.0] * self.dimension
        for word in tokens:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vector[idx] += 1.0
            
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_text(t) for t in texts]

    async def embed_query(self, text: str) -> List[float]:
        return self._hash_text(text)
