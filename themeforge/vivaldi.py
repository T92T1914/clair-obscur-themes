"""Original color-only settings for Vivaldi's shareable-theme route."""

from __future__ import annotations

from collections.abc import Mapping
import re
from uuid import NAMESPACE_URL, uuid5


# Export field names were inspected in an original exported theme. The official
# help documents the ZIP/JSON route, not a machine-readable settings schema.
COLOR_TOKENS = {
    "colorBg": "canvas",
    "colorFg": "text",
    "colorAccentBg": "panel",
    "colorHighlightBg": "accent",
    "colorWindowBg": "canvas",
}


def theme_id(name: str) -> str:
    if name not in ("Clair", "Obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    return str(uuid5(NAMESPACE_URL, f"https://t92t1914.github.io/clair-obscur-themes/vivaldi/{name.lower()}"))


def theme_settings(name: str, tokens: Mapping[str, str]) -> dict:
    """Keep initial export revision 1 separate from the adapter's version."""
    identity = theme_id(name)
    for key in set(COLOR_TOKENS.values()):
        if not isinstance(tokens.get(key), str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", tokens[key]):
            raise ValueError(f"Token {key} must be a six-digit hex color")
    return {
        "engineVersion": 1,
        "id": identity,
        "name": name,
        "version": 1,
        **{field: tokens[token].lower() for field, token in COLOR_TOKENS.items()},
    }
