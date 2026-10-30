"""Knowledge Base Index Lifecycle & Document Fingerprinting Manifest.

Tracks document changes, embedding model compatibility, and index states to prevent
unnecessary embedding recalculation and support controlled, atomic rebuilding.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from support_bot.retrieval.loader import SupportDocument


class IndexStatus(str, Enum):
    """Lifecycle status of the vector index."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    REBUILD_REQUIRED = "rebuild_required"
    ERROR = "error"


class IndexManifest(BaseModel):
    """Metadata record of indexed knowledge base state."""
    status: IndexStatus = IndexStatus.NOT_INITIALIZED
    embedding_model: str = "deterministic-fallback-128"
    document_count: int = 0
    chunk_count: int = 0
    file_hashes: Dict[str, str] = Field(default_factory=dict)
    last_indexed_at: Optional[str] = None
    error_message: Optional[str] = None


def compute_document_hash(content: str) -> str:
    """Calculate SHA256 digest of document text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ManifestManager:
    """Manages index manifest persistence and change detection."""

    def __init__(self, manifest_file_path: Optional[str] = None):
        self.manifest_path = Path(manifest_file_path) if manifest_file_path else None
        self._manifest = IndexManifest()
        if self.manifest_path and self.manifest_path.exists():
            self._load_from_disk()

    @property
    def manifest(self) -> IndexManifest:
        return self._manifest

    def _load_from_disk(self) -> None:
        """Load manifest state from file."""
        try:
            if self.manifest_path and self.manifest_path.exists():
                data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                self._manifest = IndexManifest(**data)
        except Exception:
            self._manifest = IndexManifest(status=IndexStatus.NOT_INITIALIZED)

    def save_to_disk(self) -> None:
        """Save manifest state to file if path is configured."""
        if self.manifest_path:
            try:
                self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
                self.manifest_path.write_text(
                    json.dumps(self._manifest.model_dump(), indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def check_needs_rebuild(
        self,
        current_docs: List[SupportDocument],
        embedding_model_name: str,
    ) -> bool:
        """Determine whether documents or embedding model have changed since last indexing."""
        if self._manifest.status != IndexStatus.READY:
            return True

        if self._manifest.embedding_model != embedding_model_name:
            return True

        if len(current_docs) != self._manifest.document_count:
            return True

        for doc in current_docs:
            current_hash = compute_document_hash(doc.content)
            cached_hash = self._manifest.file_hashes.get(doc.source_path)
            if cached_hash != current_hash:
                return True

        return False

    def mark_ready(
        self,
        docs: List[SupportDocument],
        chunk_count: int,
        embedding_model_name: str,
    ) -> None:
        """Update manifest to READY after successful indexing."""
        hashes = {doc.source_path: compute_document_hash(doc.content) for doc in docs}
        self._manifest = IndexManifest(
            status=IndexStatus.READY,
            embedding_model=embedding_model_name,
            document_count=len(docs),
            chunk_count=chunk_count,
            file_hashes=hashes,
            last_indexed_at=datetime.now(timezone.utc).isoformat(),
            error_message=None,
        )
        self.save_to_disk()

    def mark_error(self, message: str) -> None:
        """Record indexing failure in manifest."""
        self._manifest.status = IndexStatus.ERROR
        self._manifest.error_message = message
        self.save_to_disk()

    def mark_initializing(self) -> None:
        """Record indexing in progress."""
        self._manifest.status = IndexStatus.INITIALIZING
