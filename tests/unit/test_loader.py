"""Unit tests for KnowledgeBaseLoader security and loading rules."""

from pathlib import Path
import pytest
from support_bot.retrieval.loader import KnowledgeBaseLoader


@pytest.mark.unit
def test_loader_loads_approved_markdown():
    """Verify loader reads valid FAQ markdown files."""
    loader = KnowledgeBaseLoader(directory_path="knowledge_base")
    docs, report = loader.load_with_report()
    assert len(docs) >= 5
    assert report.loaded_documents == len(docs)
    assert report.total_bytes_loaded > 0

    titles = [d.title for d in docs]
    assert any("Account" in t or "Security" in t for t in titles)
    assert any("Billing" in t or "Refund" in t for t in titles)


@pytest.mark.unit
def test_loader_skips_unsupported_extensions(tmp_path):
    """Verify files with non-allowed extensions are safely skipped."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "faq.md").write_text("# Valid FAQ\nContent", encoding="utf-8")
    (kb_dir / "script.py").write_text("print('not allowed')", encoding="utf-8")
    (kb_dir / "binary.bin").write_bytes(b"\x00\x01\x02")

    loader = KnowledgeBaseLoader(directory_path=str(kb_dir))
    docs, report = loader.load_with_report()

    assert len(docs) == 1
    assert docs[0].title == "Valid FAQ"
    skipped_reasons = [s["reason"] for s in report.skipped_files]
    assert any("Disallowed file extension" in r for r in skipped_reasons)


@pytest.mark.unit
def test_loader_enforces_size_limit(tmp_path):
    """Verify oversized files are rejected."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    # Create small limit (100 bytes)
    (kb_dir / "huge.md").write_text("A" * 500, encoding="utf-8")

    loader = KnowledgeBaseLoader(directory_path=str(kb_dir), max_file_size=100)
    docs, report = loader.load_with_report()

    assert len(docs) == 0
    assert len(report.skipped_files) == 1
    assert "exceeds maximum size limit" in report.skipped_files[0]["reason"]
