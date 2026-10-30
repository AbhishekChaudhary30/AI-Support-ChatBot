"""Structured, security-hardened logging configuration for AI Customer Support Chatbot.

Enforces:
1. Secret and token redaction across all log records via custom RedactingFilter.
2. Structured output formatting for operational traceability.
3. Separation of debug diagnostics from user-facing error reporting.
"""

import logging
import sys
from typing import Optional
from support_bot.security.secrets import redact_text


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials, keys, and tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                clean_args = {k: redact_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
                record.args = clean_args
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_text(str(arg)) if isinstance(arg, str) else arg for arg in record.args)
        return True


def setup_logging(level: str = "INFO", app_name: str = "support_bot") -> logging.Logger:
    """Configure application-wide logger with redacting filter and clean format."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)

    # Avoid adding duplicate handlers if already initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)

    return logger
