"""Global settings accessor.

Allows importing application settings as `from config.settings import settings`.
"""

from support_bot.core.config import AppSettings, get_settings

settings: AppSettings = get_settings()

__all__ = ["settings", "AppSettings", "get_settings"]
