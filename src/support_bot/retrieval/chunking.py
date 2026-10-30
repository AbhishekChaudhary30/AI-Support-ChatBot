"""Heading-aware document chunking strategies for knowledge base retrieval.

Splits loaded documents into semantically coherent chunks:
1. Preserves Markdown heading sections (## and ###) so FAQ questions and answers stay together.
2. Applies length-based chunking with configurable overlap if a section exceeds chunk_size.
3. Preserves metadata, source titles, and relative file paths.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from support_bot.retrieval.loader import SupportDocument


class DocumentChunk(BaseModel):
    """An individual indexed chunk derived from a source document."""
    chunk_id: str
    content: str
    source_title: str
    source_path: str
    chunk_index: int
    section_heading: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """Splits documents into semantically coherent overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        preserve_headings: bool = True,
    ):
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100 characters")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_headings = preserve_headings

    def _split_by_markdown_sections(self, text: str) -> List[Dict[str, str]]:
        """Split text by ## and ### Markdown headers to keep question/answer pairs unified."""
        # Regex matching Markdown H2 or H3 headers at beginning of line
        header_pattern = re.compile(r"(^#{2,3}\s+[^\n]+)", re.MULTILINE)
        splits = header_pattern.split(text)

        sections: List[Dict[str, str]] = []
        current_heading = "General"

        for part in splits:
            part_s = part.strip()
            if not part_s:
                continue

            if part_s.startswith("## ") or part_s.startswith("### "):
                current_heading = part_s.lstrip("#").strip()
            else:
                # Content block following heading
                sections.append({
                    "heading": current_heading,
                    "content": part_s,
                })

        return sections if sections else [{"heading": "Overview", "content": text.strip()}]

    def split_document(self, document: SupportDocument) -> List[DocumentChunk]:
        """Split a single SupportDocument into chunks."""
        text = document.content.strip()
        chunks: List[DocumentChunk] = []

        if not text:
            return chunks

        # Strategy 1: Heading-aware section segmentation
        if self.preserve_headings:
            sections = self._split_by_markdown_sections(text)
        else:
            sections = [{"heading": document.title, "content": text}]

        chunk_idx = 0
        for sec in sections:
            sec_heading = sec["heading"]
            sec_text = sec["content"]

            # If section fits within chunk_size, keep it intact
            if len(sec_text) <= self.chunk_size:
                formatted_chunk = f"[{sec_heading}]\n{sec_text}" if sec_heading != "General" else sec_text
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.title}_{chunk_idx}",
                        content=formatted_chunk.strip(),
                        source_title=document.title,
                        source_path=document.source_path,
                        chunk_index=chunk_idx,
                        section_heading=sec_heading,
                        metadata=document.metadata,
                    )
                )
                chunk_idx += 1
            else:
                # Sub-divide large section with overlap
                start = 0
                step = self.chunk_size - self.chunk_overlap
                while start < len(sec_text):
                    end = start + self.chunk_size
                    chunk_slice = sec_text[start:end]

                    if end < len(sec_text):
                        last_break = chunk_slice.rfind("\n")
                        if last_break > self.chunk_overlap:
                            chunk_slice = chunk_slice[:last_break]
                            end = start + last_break

                    cleaned = chunk_slice.strip()
                    if cleaned:
                        formatted_chunk = f"[{sec_heading}]\n{cleaned}" if sec_heading != "General" else cleaned
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"{document.title}_{chunk_idx}",
                                content=formatted_chunk.strip(),
                                source_title=document.title,
                                source_path=document.source_path,
                                chunk_index=chunk_idx,
                                section_heading=sec_heading,
                                metadata=document.metadata,
                            )
                        )
                        chunk_idx += 1

                    start = end
                    if start >= len(sec_text):
                        break

        return chunks

    def split_documents(self, documents: List[SupportDocument]) -> List[DocumentChunk]:
        """Split a batch of documents into chunks."""
        all_chunks: List[DocumentChunk] = []
        for doc in documents:
            all_chunks.extend(self.split_document(doc))
        return all_chunks
