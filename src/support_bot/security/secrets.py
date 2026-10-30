"""Session-only secret handling and redaction utilities.

Ensures API keys, authorization tokens, and credentials:
1. Never appear in raw form in log files or exception strings.
2. Are held in ephemeral, session-scoped memory structures with clear lifecycle boundaries.
3. Cannot be accidentally serialized to disk, database, or UI metadata.
"""

import re
from typing import Any, Dict, Optional

# Patterns matching sensitive token structures and credentials
SENSITIVE_PATTERNS = [
    # OpenAI / generic Bearer keys (sk-...)
    re.compile(r"sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE),
    # Anthropic keys (sk-ant-...)
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}", re.IGNORECASE),
    # Google AI keys (AIza...)
    re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),
    # Generic bearer tokens
    re.compile(r"(Bearer\s+)[A-Za-z0-9_.-]+", re.IGNORECASE),
    # Common secret query params or keys in URLs
    re.compile(r"(api[_-]?key=)[^&\s]+", re.IGNORECASE),
    re.compile(r"(password=)[^&\s]+", re.IGNORECASE),
    re.compile(r"(secret=)[^&\s]+", re.IGNORECASE),
]

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "token",
    "access_token",
    "auth_token",
    "authorization",
    "credential",
    "credentials",
}


def mask_secret(value: Optional[str]) -> str:
    """Return a masked representation of a secret string.
    
    If length is 8 or fewer chars, all are masked.
    If longer, shows first 3 and last 3 characters.
    """
    if not value:
        return "[EMPTY]"
    length = len(value)
    if length <= 8:
        return "*" * length
    return f"{value[:3]}...{value[-3:]} (len: {length})"


def redact_text(text: str) -> str:
    """Scan and redact any known secret formats in a freeform string."""
    if not text:
        return text
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r"\1***REDACTED***" if r"\1" in pattern.pattern else "***REDACTED***", sanitized)
    return sanitized


def sanitize_dict_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize a dictionary for safe structured logging.
    
    Keys that match SENSITIVE_KEYS have their values replaced with a masked summary.
    """
    clean: Dict[str, Any] = {}
    for k, v in data.items():
        lower_k = k.lower()
        if any(s in lower_k for s in SENSITIVE_KEYS):
            clean[k] = mask_secret(str(v)) if v else None
        elif isinstance(v, dict):
            clean[k] = sanitize_dict_for_logging(v)
        elif isinstance(v, str):
            clean[k] = redact_text(v)
        else:
            clean[k] = v
    return clean


class SessionSecret:
    """Ephemeral in-memory wrapper for a sensitive credential.
    
    Prevents accidental printing, logging, or repr leak.
    Provides explicit `clear()` method for session teardown.
    """

    __slots__ = ("_secret_value",)

    def __init__(self, value: Optional[str]):
        self._secret_value: Optional[str] = value.strip() if value else None

    def get_secret_value(self) -> Optional[str]:
        """Retrieve the raw secret value for authenticating an API request."""
        return self._secret_value

    def is_configured(self) -> bool:
        """Check whether a non-empty secret is set."""
        return bool(self._secret_value)

    def clear(self) -> None:
        """Explicitly clear the secret from memory."""
        self._secret_value = None

    def __repr__(self) -> str:
        status = "Configured" if self._secret_value else "Empty"
        return f"<SessionSecret: [{status}]>"

    def __str__(self) -> str:
        return "[REDACTED]"
