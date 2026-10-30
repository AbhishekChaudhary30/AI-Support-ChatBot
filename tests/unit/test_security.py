"""Unit tests for security, secret handling, and token redaction."""

from pathlib import Path
import pytest
from support_bot.security.secrets import (
    SessionSecret,
    mask_secret,
    redact_text,
    sanitize_dict_for_logging,
)


@pytest.mark.unit
def test_session_secret_lifecycle():
    """Verify session secret hides raw string in repr/str and clears cleanly."""
    raw_key = "sk-proj-supersecretkey123456789"
    secret = SessionSecret(raw_key)
    
    assert secret.is_configured() is True
    assert secret.get_secret_value() == raw_key
    assert str(secret) == "[REDACTED]"
    assert raw_key not in repr(secret)
    
    secret.clear()
    assert secret.is_configured() is False
    assert secret.get_secret_value() is None


@pytest.mark.unit
def test_mask_secret():
    """Verify masking behaves safely for varying string lengths."""
    assert mask_secret(None) == "[EMPTY]"
    assert mask_secret("") == "[EMPTY]"
    assert mask_secret("short") == "*****"
    masked = mask_secret("sk-1234567890abcdef")
    assert masked.startswith("sk-...")
    assert "1234567890" not in masked


@pytest.mark.unit
def test_redact_text():
    """Verify known credential tokens are scrubbed from log strings."""
    test_str = "Error calling endpoint with Authorization: Bearer secret_token_xyz and api_key=sk-abcdef123456789"
    redacted = redact_text(test_str)
    assert "sk-abcdef123456789" not in redacted
    assert "***REDACTED***" in redacted


@pytest.mark.unit
def test_sanitize_dict_for_logging():
    """Verify dictionary scrubber sanitizes nested structures."""
    payload = {
        "user": "alice",
        "api_key": "sk-realtestkey987654321",
        "nested": {
            "password": "mypassword123",
            "model": "gpt-4o",
        },
    }
    clean = sanitize_dict_for_logging(payload)
    assert clean["user"] == "alice"
    assert clean["api_key"] != "sk-realtestkey987654321"
    assert clean["nested"]["password"] != "mypassword123"
    assert clean["nested"]["model"] == "gpt-4o"


@pytest.mark.unit
def test_no_real_secrets_in_tracked_code():
    """Scan project files to ensure no real API keys are hardcoded."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    import re
    # Check for actual candidate key tokens (prefix followed by 16+ alphanumeric characters)
    real_secret_patterns = [
        re.compile(r"sk-proj-[A-Za-z0-9_-]{16,}"),
        re.compile(r"AIzaSy[A-Za-z0-9_-]{16,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),
    ]

    # Check .py, .md, .toml, .env.example
    for ext in ["*.py", "*.md", "*.toml"]:
        for file_path in root_dir.rglob(ext):
            if ".venv" in str(file_path) or ".git" in str(file_path):
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # In test files we might have mock tokens or regex pattern explanations
            if "tests" in file_path.parts:
                continue
            for pattern in real_secret_patterns:
                match = pattern.search(content)
                assert match is None, f"Real-looking secret token found in {file_path}: {match.group(0)}"
