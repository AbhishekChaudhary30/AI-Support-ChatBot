"""UI component formatting helpers for Chainlit interface.

Handles brand logo verification, social profile links, technology cards formatting,
and footer generation.
"""

from pathlib import Path
from typing import Optional
from support_bot.core.config import AppSettings, get_settings
from support_bot.ui.project_info import (
    ABOUT_PROJECT_TEXT,
    ARCHITECTURE_FLOW_DIAGRAM,
    PRIVACY_EXPLANATION,
    TECHNOLOGY_CARDS,
)


def get_brand_badge(logo_path: str = "assets/logo.png") -> str:
    """Return brand header markup with image or graceful fallback."""
    candidate_paths = [Path("public/logo.png"), Path(logo_path), Path("logo.png")]
    for p in candidate_paths:
        if p.exists() and p.is_file():
            return '<img src="/public/logo.png" alt="Brand Logo" style="max-height: 42px; width: auto; object-fit: contain; vertical-align: middle; margin-right: 10px;" /> **AI Customer Support**'
    return '<span style="display:inline-block; padding: 4px 10px; background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 6px; font-weight: 700; color: #a78bfa; margin-right: 8px;">SUPPORT AI</span> **Customer Support Chatbot**'


def render_technology_stack_markdown() -> str:
    """Format technology architecture cards into clean Markdown."""
    lines = [
        "### Architecture & Technology Flow",
        ARCHITECTURE_FLOW_DIAGRAM,
        "\n### Core Technologies & Responsibilities",
    ]
    for card in TECHNOLOGY_CARDS:
        lines.append(
            f"- **{card['name']}**\n"
            f"  - **Role:** {card['role']}\n"
            f"  - **Why Needed:** {card['why_needed']}\n"
            f"  - **Communicates With:** `{card['communicates_with']}`"
        )
    return "\n".join(lines)


def render_about_section_markdown() -> str:
    """Return full About This Project markdown text."""
    return f"{ABOUT_PROJECT_TEXT}\n\n{PRIVACY_EXPLANATION}"


def render_footer_markdown(settings: Optional[AppSettings] = None) -> str:
    """Generate professional footer with strictly configured LinkedIn and GitHub links.
    
    Adheres strictly to the requirement:
    'Follow and Connect only on LinkedIn and GitHub'
    Never invents URLs if not configured in settings.
    """
    cfg = settings or get_settings()
    linkedin_url = cfg.user_linkedin_url
    github_url = cfg.user_github_url

    linkedin_part = (
        f'<a href="{linkedin_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; text-decoration: none; font-weight: 600;">LinkedIn</a>'
        if linkedin_url
        else '<span style="color: #cbd5e1; font-weight: 600;">LinkedIn</span>'
    )

    github_part = (
        f'<a href="{github_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; text-decoration: none; font-weight: 600;">GitHub</a>'
        if github_url
        else '<span style="color: #cbd5e1; font-weight: 600;">GitHub</span>'
    )

    return (
        '<div style="text-align: center; margin-top: 30px; padding: 16px; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.85rem; color: #94a3b8;">'
        '<div><strong>AI Customer Support Chatbot</strong> — Production-Grade Portfolio Architecture</div>'
        f'<div style="margin-top: 6px;">Follow and Connect only on {linkedin_part} and {github_part}</div>'
        '</div>'
    )
