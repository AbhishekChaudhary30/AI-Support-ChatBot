"""UI package."""

from support_bot.ui.components import (
    get_brand_badge,
    render_about_section_markdown,
    render_footer_markdown,
    render_technology_stack_markdown,
)
from support_bot.ui.project_info import (
    ABOUT_PROJECT_TEXT,
    ARCHITECTURE_FLOW_DIAGRAM,
    PRIVACY_EXPLANATION,
    TECHNOLOGY_CARDS,
)

__all__ = [
    "get_brand_badge",
    "render_about_section_markdown",
    "render_footer_markdown",
    "render_technology_stack_markdown",
    "ABOUT_PROJECT_TEXT",
    "ARCHITECTURE_FLOW_DIAGRAM",
    "PRIVACY_EXPLANATION",
    "TECHNOLOGY_CARDS",
]
