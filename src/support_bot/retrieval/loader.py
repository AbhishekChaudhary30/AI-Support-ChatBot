"""Document loading, path validation, and security sanitization for knowledge base ingestion.

Reads markdown and text FAQ files from the approved knowledge base directory.
Enforces:
1. Directory traversal prevention (strict path confinement).
2. Allowed file extension whitelisting (.md, .txt).
3. Maximum file-size limits (prevent memory exhaustion / denial of service).
4. UTF-8 decoding with error recovery.
5. Ingestion auditing and skipped file reporting.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from support_bot.core.exceptions import RetrievalError

# Maximum document size in bytes (2 MB limit protects against denial-of-service)
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS: Set[str] = {".md", ".txt"}


class SupportDocument(BaseModel):
    """Normalized document representation from the knowledge base."""
    title: str
    content: str
    source_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionReport(BaseModel):
    """Auditing report detailing knowledge base discovery and loading outcomes."""
    total_files_discovered: int = 0
    loaded_documents: int = 0
    skipped_files: List[Dict[str, str]] = Field(default_factory=list)
    total_bytes_loaded: int = 0


def _extract_title_from_text(text: str, default_title: str) -> str:
    """Extract first top-level Markdown heading '# ...' or fallback to default."""
    for line in text.splitlines():
        line_s = line.strip()
        if line_s.startswith("# ") and len(line_s) > 2:
            title = line_s[2:].strip()
            # Clean unwanted formatting
            title = re.sub(r"[\*\_`]", "", title)
            if title:
                return title
    return default_title


class KnowledgeBaseLoader:
    """Loads documents securely from a designated knowledge base directory."""

    def __init__(
        self,
        directory_path: str = "knowledge_base",
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ):
        self.directory = Path(directory_path).resolve()
        self.max_file_size = max_file_size

    def _validate_path_containment(self, target_path: Path) -> bool:
        """Ensure path does not escape the configured knowledge base directory (path traversal check)."""
        try:
            resolved = target_path.resolve()
            return resolved == self.directory or self.directory in resolved.parents
        except Exception:
            return False

    def load_with_report(self) -> Tuple[List[SupportDocument], IngestionReport]:
        """Load and validate all documents, returning documents and a detailed auditing report."""
        if not self.directory.exists():
            raise RetrievalError(
                message=f"Knowledge base directory '{self.directory}' does not exist.",
                user_friendly_message="Knowledge base directory was not found. Please verify project setup.",
            )

        report = IngestionReport()
        documents: List[SupportDocument] = []

        # Recursively scan for potential knowledge base files
        for file_path in self.directory.rglob("*"):
            if not file_path.is_file():
                continue

            report.total_files_discovered += 1

            # Check 1: Directory traversal confinement
            if not self._validate_path_containment(file_path):
                report.skipped_files.append({
                    "path": str(file_path),
                    "reason": "Security rejection: Path traversal outside knowledge base directory.",
                })
                continue

            # Check 2: Skip internal README files or dotfiles
            if file_path.name.lower().startswith("readme") or file_path.name.startswith("."):
                continue

            # Check 3: File extension allowlist
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                report.skipped_files.append({
                    "path": file_path.name,
                    "reason": f"Disallowed file extension '{file_path.suffix}'. Only .md and .txt are supported.",
                })
                continue

            # Check 4: Enforce file size limit
            try:
                size = file_path.stat().st_size
                if size > self.max_file_size:
                    report.skipped_files.append({
                        "path": file_path.name,
                        "reason": f"File exceeds maximum size limit ({size} > {self.max_file_size} bytes).",
                    })
                    continue
                if size == 0:
                    report.skipped_files.append({
                        "path": file_path.name,
                        "reason": "File is empty (0 bytes).",
                    })
                    continue
            except OSError as oe:
                report.skipped_files.append({
                    "path": file_path.name,
                    "reason": f"File stat error: {str(oe)}",
                })
                continue

            # Check 5: Read and decode content safely
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                cleaned = text.strip()
                if not cleaned:
                    continue

                default_title = file_path.stem.replace("_", " ").title()
                extracted_title = _extract_title_from_text(cleaned, default_title)

                doc = SupportDocument(
                    title=extracted_title,
                    content=cleaned,
                    source_path=str(file_path.relative_to(self.directory.parent).as_posix()),
                    metadata={
                        "size_bytes": len(cleaned.encode("utf-8")),
                        "filename": file_path.name,
                        "category": file_path.parent.name,
                    },
                )
                documents.append(doc)
                report.loaded_documents += 1
                report.total_bytes_loaded += len(cleaned.encode("utf-8"))
            except Exception as e:
                report.skipped_files.append({
                    "path": file_path.name,
                    "reason": f"Read error: {str(e)}",
                })

        return documents, report

    def load_documents(self) -> List[SupportDocument]:
        """Convenience method returning loaded documents directly."""
        docs, _ = self.load_with_report()
        return docs
