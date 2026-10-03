"""Map the shared palette to Firefox's color-only static-theme contract."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .equicord import TOKEN_NAMES


# Current Mozilla theme keys. Deprecated tab/field separators are excluded.
COLOR_TOKENS = {
    "frame": "canvas", "frame_inactive": "control",
    "tab_background_text": "muted", "tab_selected": "panel",
    "tab_text": "text", "tab_line": "focus", "tab_loading": "accent",
    "toolbar": "panel", "toolbar_text": "text",
    "icons": "text", "icons_attention": "accent",
    "button_background_hover": "hover", "button_background_active": "selected",
    "toolbar_field": "control", "toolbar_field_text": "text",
    "toolbar_field_border": "border", "toolbar_field_focus": "panel",
    "toolbar_field_text_focus": "text", "toolbar_field_border_focus": "focus",
    "toolbar_field_highlight": "accent", "toolbar_field_highlight_text": "on_accent",
    "toolbar_top_separator": "divider", "toolbar_bottom_separator": "divider",
    "toolbar_vertical_separator": "divider",
    "popup": "panel", "popup_text": "text", "popup_border": "border",
    "popup_highlight": "accent", "popup_highlight_text": "on_accent",
    "sidebar": "canvas", "sidebar_text": "text", "sidebar_border": "divider",
    "sidebar_highlight": "accent", "sidebar_highlight_text": "on_accent",
    "ntp_background": "canvas", "ntp_text": "text", "ntp_card_background": "panel",
}


def theme_manifest(name: str, tokens: Mapping[str, str], version: str) -> dict:
    """Return a manual-choice desktop theme without executable capabilities."""
    if name not in ("Clair", "Obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Firefox version must contain three integers")
    for key in TOKEN_NAMES:
        if not isinstance(tokens.get(key), str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", tokens[key]):
            raise ValueError(f"Token {key} must be a six-digit hex color")
    mode = "light" if name == "Clair" else "dark"
    return {
        "manifest_version": 2,
        "name": name,
        "version": version,
        "author": "T92T1914",
        "description": f"{name} native color theme. Manual {mode} appearance. Firefox keeps its interface font.",
        "browser_specific_settings": {
            "gecko": {"id": f"{name.lower()}@themes.t92t1914.github.io", "strict_min_version": "128.0"},
        },
        "theme": {
            "colors": {key: tokens[token].lower() for key, token in COLOR_TOKENS.items()},
            # The browser's built-in chrome follows the chosen family. Websites
            # retain the system preference rather than being forcibly restyled.
            "properties": {"color_scheme": mode, "content_color_scheme": "system"},
        },
    }
