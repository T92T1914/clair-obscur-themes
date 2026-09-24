"""Build native Chrome themes without page access or executable content."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import struct
import tempfile
import zlib

from .legal import license_text


# Reviewed against Chromium's kOverwritableColorTable. See docs/chrome-contract.md.
COLOR_TOKENS = {
    "frame": "canvas",
    "frame_inactive": "control",
    "background_tab": "control",
    "background_tab_inactive": "selected",
    "tab_text": "text",
    "tab_background_text": "muted",
    "tab_background_text_inactive": "muted",
    "toolbar": "panel",
    "toolbar_text": "text",
    "toolbar_button_icon": "text",
    "bookmark_text": "text",
    "button_background": "control",
    "omnibox_background": "control",
    "omnibox_text": "text",
    "ntp_background": "canvas",
    "ntp_text": "text",
    "ntp_link": "accent",
    "ntp_header": "divider",
}

_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
_VERSION = re.compile(r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){0,3}\Z")
_FILES = {"manifest.json", "icon128.png", "LICENSE.txt"}


def _rgb(value: str, name: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError(f"Token {name!r} must be a six-digit RGB hex color")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def _icon(colors: dict[str, tuple[int, int, int]]) -> bytes:
    """Encode an original flat page emblem with no font or external asset."""
    rows = bytearray()
    for y in range(128):
        rows.append(0)  # PNG filter: none.
        for x in range(128):
            color = None
            if 16 <= x < 112 and 16 <= y < 112:
                color = colors["panel"]
                if x in (16, 111) or y in (16, 111):
                    color = colors["divider"]
                elif 31 <= x < 37 and 32 <= y < 96:
                    color = colors["accent"]
                elif 49 <= x < 96 and (40 <= y < 45 or 61 <= y < 66):
                    color = colors["text"]
                elif 49 <= x < 83 and 82 <= y < 87:
                    color = colors["muted"]
            rows.extend((*color, 255) if color else (0, 0, 0, 0))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">2I5B", 128, 128, 8, 6, 0, 0, 0))
            + chunk(b"sRGB", b"\x00")
            + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
            + chunk(b"IEND", b""))


def _write_atomic(path: Path, payload: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".theme-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_theme(name: str, tokens: dict, destination: Path, version: str) -> Path:
    """Write a native theme to destination/name.lower() and return its directory.

    Validate inputs before writing. Refuse unrelated files or a different manifest
    in an existing output directory. Shared tokens without native theme mappings
    are deliberately omitted rather than emitted as unsupported Chrome fields.
    """
    if not isinstance(name, str) or name.lower() not in ("clair", "obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    name = name.capitalize()
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError("Version must contain one to four integers without leading zeroes")
    components = [int(component) for component in version.split(".")]
    if max(components) > 65535 or not any(components):
        raise ValueError("Version components must be 0..65535 and not all zero")
    if not isinstance(tokens, dict):
        raise ValueError("Tokens must be a dictionary of semantic RGB colors")
    required = set(COLOR_TOKENS.values())
    missing = sorted(required - tokens.keys())
    if missing:
        raise ValueError("Missing native Chrome tokens: " + ", ".join(missing))
    colors = {key: _rgb(tokens[key], key) for key in sorted(required)}
    manifest = {
        "manifest_version": 3,
        "name": name,
        "version": version,
        "description": (
            "Warm paper and clear ink. A restrained native Chrome theme."
            if name == "Clair" else
            "Deep neutral surfaces and clear type. A restrained native Chrome theme."
        ),
        "icons": {"128": "icon128.png"},
        "theme": {"colors": {key: colors[token] for key, token in COLOR_TOKENS.items()}},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    icon_bytes = _icon(colors)
    license_bytes = license_text().encode("utf-8")

    root = Path(destination).resolve()
    target = root / name.lower()
    if target.is_symlink() or target.resolve().parent != root:
        raise ValueError("Theme output must be a direct directory inside the destination")
    if target.exists():
        if not target.is_dir():
            raise ValueError("Theme output already exists and is not a directory")
        if any(item.name not in _FILES or not item.is_file() or item.is_symlink()
               for item in target.iterdir()):
            raise ValueError("Theme output contains unrelated files or links")
        old_manifest = target / "manifest.json"
        if old_manifest.exists():
            try:
                previous = json.loads(old_manifest.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as error:
                raise ValueError("Existing theme manifest cannot be identified safely") from error
            if not isinstance(previous, dict) or previous.get("name") != name or "theme" not in previous:
                raise ValueError("Existing manifest belongs to a different package")
    target.mkdir(parents=True, exist_ok=True)
    _write_atomic(target / "icon128.png", icon_bytes)
    _write_atomic(target / "LICENSE.txt", license_bytes)
    _write_atomic(target / "manifest.json", manifest_bytes)
    return target
