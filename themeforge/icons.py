"""Generate original functional SVG icons into a separate, new output folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

from .legal import license_text
from .tokens import load, validate
from .icon_apps import (
    APP_CATALOG, CATALOG_DATE, CATALOG_SCOPE,
    NEW_APP_CATALOG, NEW_CATALOG_DATE, NEW_CATALOG_SCOPE,
    THIRD_APP_CATALOG, THIRD_CATALOG_DATE, THIRD_CATALOG_SCOPE,
    FOURTH_APP_CATALOG, FOURTH_CATALOG_DATE, FOURTH_CATALOG_SCOPE,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.7.0"
VERSIONS = ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", VERSION)
SIZE = 512
STROKE = 16
FUNCTIONS = (
    "phone", "messages", "contacts", "camera", "gallery", "settings",
    "calendar", "clock", "files", "notes", "mail", "browser", "maps",
    "music", "video", "store", "wallet", "calculator", "weather", "health",
    "fitness", "voice-recorder", "home", "search",
)


def _shape(tag: str, **attributes: object) -> tuple[str, dict[str, str]]:
    return tag, {name: str(value) for name, value in attributes.items()}


def _path(data: str, *, accent: bool = False, filled: bool = False):
    attributes = {"d": data}
    if accent:
        attributes["stroke"] = "accent"
    if filled:
        attributes["fill"] = "accent" if accent else "text"
    return _shape("path", **attributes)


# Original geometric drawings use only absolute lines and Bezier control points.
# All centerlines/control hulls stay within 112..400; the 12px stroke stays 106..406.
GLYPHS = {
    "phone": [
        _path("M176 128 L208 192 Q216 208 200 224 L184 240 "
              "Q216 296 272 328 L288 312 Q304 296 320 304 L384 336 "
              "Q392 344 384 360 L360 384 Q344 400 320 392 "
              "C216 360 152 296 120 192 Q112 168 128 152 L152 128 Q168 120 176 128 Z"),
        _path("M280 136 Q352 152 376 224", accent=True),
    ],
    "messages": [
        _shape("rect", x=120, y=136, width=272, height=208, rx=48),
        _path("M200 344 L152 388 V328"),
        _path("M184 216 H328 M184 264 H288", accent=True),
    ],
    "contacts": [
        _shape("circle", cx=256, cy=204, r=48, stroke="accent"),
        _path("M160 376 V352 C160 304 200 280 256 280 C312 280 352 304 352 352 V376 Z"),
    ],
    "camera": [
        _path("M136 184 H184 L208 144 H304 L328 184 H376 "
              "Q392 184 392 200 V352 Q392 368 376 368 H136 "
              "Q120 368 120 352 V200 Q120 184 136 184 Z"),
        _shape("circle", cx=256, cy=272, r=56, stroke="accent"),
        _shape("line", x1=344, y1=216, x2=360, y2=216),
    ],
    "gallery": [
        _shape("rect", x=120, y=128, width=272, height=256, rx=36),
        _shape("circle", cx=304, cy=204, r=24, stroke="accent"),
        _path("M136 352 L208 264 L256 312 L280 288 L376 368"),
    ],
    "settings": [
        _path("M232 120 H280 L288 160 L320 176 L360 160 L384 200 "
              "L352 232 V280 L384 312 L360 352 L320 336 L288 352 "
              "L280 392 H232 L224 352 L192 336 L152 352 L128 312 "
              "L160 280 V232 L128 200 L152 160 L192 176 L224 160 Z"),
        _shape("circle", cx=256, cy=256, r=48, stroke="accent"),
    ],
    "calendar": [
        _shape("rect", x=120, y=136, width=272, height=256, rx=32),
        _path("M176 112 V160 M336 112 V160 M120 208 H392"),
        _shape("rect", x=176, y=248, width=56, height=56, rx=12, stroke="accent"),
        _path("M280 264 H328 M280 320 H328"),
    ],
    "clock": [
        _shape("circle", cx=256, cy=256, r=136),
        _path("M256 176 V256 H320", accent=True),
        _path("M256 128 V144 M384 256 H368 M256 384 V368 M128 256 H144"),
    ],
    "files": [
        _path("M120 184 V352 Q120 376 144 376 H368 Q392 376 392 352 "
              "V208 Q392 184 368 184 H248 L216 152 H144 Q120 152 120 184 Z"),
        _path("M144 240 H368", accent=True),
    ],
    "notes": [
        _shape("rect", x=144, y=120, width=224, height=272, rx=32),
        _path("M192 200 H320 M192 256 H320"),
        _path("M192 312 H272", accent=True),
    ],
    "mail": [
        _shape("rect", x=120, y=152, width=272, height=224, rx=32),
        _path("M136 176 L256 272 L376 176", accent=True),
        _path("M136 352 L208 280 M376 352 L304 280"),
    ],
    "browser": [
        _shape("circle", cx=256, cy=256, r=136),
        _path("M120 256 H392", accent=True),
        _path("M256 120 C176 184 176 328 256 392 "
              "M256 120 C336 184 336 328 256 392 M144 192 H368 M144 320 H368"),
    ],
    "maps": [
        _path("M128 144 L208 176 L304 136 L384 168 V368 L304 336 L208 376 L128 344 Z"),
        _path("M208 176 V376 M304 136 V184 M304 312 V336"),
        _path("M304 304 C280 280 256 256 256 232 C256 168 352 168 352 232 "
              "C352 256 328 280 304 304 Z", accent=True),
        _shape("circle", cx=304, cy=232, r=16, stroke="accent"),
    ],
    "music": [
        _path("M216 336 V176 L352 144 V304"),
        _shape("ellipse", cx=184, cy=336, rx=32, ry=24, stroke="accent"),
        _shape("ellipse", cx=320, cy=304, rx=32, ry=24, stroke="accent"),
        _path("M216 216 L352 184"),
    ],
    "video": [
        _shape("rect", x=120, y=144, width=272, height=224, rx=40),
        _path("M224 208 L312 256 L224 304 Z", accent=True),
    ],
    "store": [
        _path("M144 208 H368 V368 Q368 392 344 392 H168 Q144 392 144 368 Z"),
        _path("M200 208 V176 C200 112 312 112 312 176 V208", accent=True),
    ],
    "wallet": [
        _shape("rect", x=120, y=160, width=272, height=208, rx=40),
        _shape("rect", x=272, y=224, width=120, height=80, rx=24, stroke="accent"),
        _shape("circle", cx=312, cy=264, r=8, fill="accent", stroke="accent"),
    ],
    "calculator": [
        _shape("rect", x=152, y=112, width=208, height=288, rx=32),
        _shape("rect", x=184, y=152, width=144, height=56, rx=12, stroke="accent"),
        _path("M192 264 H224 M208 248 V280 M288 264 H320 "
              "M192 336 L224 368 M224 336 L192 368 M288 344 H320 M288 360 H320"),
    ],
    "weather": [
        _shape("circle", cx=196, cy=212, r=48, stroke="accent"),
        _path("M196 128 V144 M128 176 L144 184 M248 160 L260 144", accent=True),
        _path("M176 352 H352 C400 352 400 272 352 272 "
              "C336 208 240 208 224 280 C160 248 128 352 176 352 Z"),
    ],
    "health": [
        _path("M256 376 C208 344 128 280 128 216 C128 144 224 136 256 192 "
              "C288 136 384 144 384 216 C384 280 304 344 256 376 Z"),
        _path("M144 272 H208 L232 224 L264 312 L288 264 H368", accent=True),
    ],
    "fitness": [
        _shape("rect", x=136, y=184, width=48, height=144, rx=16),
        _shape("rect", x=328, y=184, width=48, height=144, rx=16),
        _path("M112 216 V296 M400 216 V296 M184 256 H328", accent=True),
    ],
    "voice-recorder": [
        _shape("rect", x=208, y=120, width=96, height=184, rx=48),
        _path("M168 248 V264 C168 312 208 344 256 344 "
              "C304 344 344 312 344 264 V248"),
        _path("M256 344 V392 M208 392 H304", accent=True),
    ],
    "home": [
        _path("M120 232 L256 120 L392 232 M152 216 V384 H360 V216"),
        _path("M224 384 V288 H288 V384", accent=True),
    ],
    "search": [
        _shape("circle", cx=232, cy=232, r=104),
        _path("M312 312 L392 392", accent=True),
    ],
}


# Keep the original geometry available for exact 0.1.0 rebuilds. The current
# drawings open crowded interiors and balance the lighter silhouettes at small sizes.
CURRENT_GLYPHS = {
    **GLYPHS,
    "messages": [
        _path("M168 136 H344 Q392 136 392 184 V296 Q392 344 344 344 "
              "H216 L152 392 V340 Q120 328 120 296 V184 Q120 136 168 136 Z"),
        _path("M184 216 H328 M184 264 H288", accent=True),
    ],
    "contacts": [
        _shape("circle", cx=256, cy=192, r=52, stroke="accent"),
        _path("M144 376 V348 C144 304 192 280 256 280 C320 280 368 304 368 348 V376 Z"),
    ],
    "browser": [
        _shape("circle", cx=256, cy=256, r=136),
        _path("M120 256 H392", accent=True),
        _path("M256 120 C176 184 176 328 256 392 "
              "M256 120 C336 184 336 328 256 392"),
    ],
    "maps": [
        _path("M128 144 L208 176 L304 136 L384 168 V368 L304 336 L208 376 L128 344 Z"),
        _path("M208 176 V376 M304 136 V160 M304 328 V336"),
        _path("M304 304 C280 280 256 256 256 232 C256 168 352 168 352 232 "
              "C352 256 328 280 304 304 Z", accent=True),
        _shape("circle", cx=304, cy=232, r=16, stroke="accent"),
    ],
    "music": [
        _path("M224 344 V168 L368 136 V304"),
        _shape("ellipse", cx=184, cy=344, rx=40, ry=28, stroke="accent"),
        _shape("ellipse", cx=328, cy=304, rx=40, ry=28, stroke="accent"),
        _path("M224 208 L368 176"),
    ],
    "calculator": [
        _shape("rect", x=152, y=112, width=208, height=288, rx=32),
        _shape("rect", x=184, y=152, width=144, height=56, rx=12, stroke="accent"),
        _path("M192 264 H224 M208 248 V280 M288 264 H320 "
              "M192 328 L224 360 M224 328 L192 360 M288 328 H320 M288 360 H320"),
    ],
    "fitness": [
        _shape("rect", x=136, y=168, width=48, height=176, rx=16),
        _shape("rect", x=328, y=168, width=48, height=176, rx=16),
        _path("M112 208 V304 M400 208 V304 M184 256 H328", accent=True),
    ],
}


# Original theme interpretations for the named collection. These are local
# geometric drawings, not downloaded publisher artwork or embedded logo assets.
APP_GLYPHS = {
    "google-chrome": [
        _shape("circle", cx=256, cy=256, r=136),
        _shape("circle", cx=256, cy=256, r=56, stroke="accent"),
        _path("M256 120 V200 M374 324 L304 284 M138 324 L208 284"),
    ],
    "youtube": [
        _shape("rect", x=120, y=168, width=272, height=176, rx=48),
        _path("M232 208 L304 256 L232 304 Z", accent=True),
    ],
    "google-maps": [
        _path("M256 392 C224 344 160 280 160 216 C160 112 352 112 352 216 "
              "C352 280 288 344 256 392 Z"),
        _shape("circle", cx=256, cy=216, r=40, stroke="accent"),
    ],
    "gmail": [
        _shape("rect", x=128, y=160, width=256, height=208, rx=32),
        _path("M128 176 L256 280 L384 176", accent=True),
        _path("M168 208 V328 M344 208 V328"),
    ],
    "google-photos": [
        _path("M256 256 V136 C192 136 160 168 160 216 V256 Z"),
        _path("M256 256 H376 C376 192 344 160 296 160 H256 Z", accent=True),
        _path("M256 256 V376 C320 376 352 344 352 296 V256 Z"),
        _path("M256 256 H136 C136 320 168 352 216 352 H256 Z", accent=True),
    ],
    "google-messages": [
        _shape("rect", x=152, y=128, width=224, height=176, rx=48, stroke="accent"),
        _path("M184 192 H296 Q344 192 344 240 V304 Q344 352 296 352 "
              "H216 L152 392 V344 Q120 328 120 296 V240 Q120 192 184 192 Z"),
    ],
    "google-calendar": [
        _shape("rect", x=136, y=128, width=240, height=256, rx=32),
        _path("M136 208 H376 M200 112 V152 M312 112 V152", accent=True),
        _path("M184 248 H232 V280 H200 M232 280 V328 H184 "
              "M280 264 L304 248 V328 M280 328 H328"),
    ],
    "google-drive": [
        _path("M256 128 L384 352 H128 Z"),
        _path("M256 208 L320 320 H192 Z", accent=True),
    ],
    "samsung-browser": [
        _shape("circle", cx=256, cy=256, r=104),
        _path("M136 328 C112 312 152 256 216 216 C280 176 360 144 384 160 "
              "C400 184 352 240 288 280 C224 320 160 352 136 328 Z", accent=True),
    ],
    "samsung-notes": [
        _shape("rect", x=144, y=128, width=224, height=256, rx=24),
        _path("M184 184 H296 M184 224 H272"),
        _path("M232 344 L336 240 L368 272 L264 376 L232 384 Z", accent=True),
    ],
    "samsung-health": [
        _shape("circle", cx=272, cy=152, r=24, stroke="accent"),
        _path("M248 208 L208 272 L160 256 M248 208 L296 240 H352 "
              "M248 208 L264 288 L224 368 M264 288 L336 352"),
    ],
    "garmin-connect": [
        _path("M128 336 L208 176 L272 280 L320 208 L384 336 Z"),
        _path("M176 240 H248 M272 280 L304 336", accent=True),
    ],
    "whatsapp": [
        _path("M256 128 C184 128 128 184 128 256 C128 288 144 320 160 336 "
              "L144 384 L200 368 C216 376 240 384 256 384 "
              "C328 384 384 328 384 256 C384 184 328 128 256 128 Z"),
        _path("M208 200 L232 240 L216 256 C232 280 248 296 272 304 "
              "L288 288 L328 312 C304 352 248 336 208 296 "
              "C176 264 168 224 208 200 Z", accent=True),
    ],
    "messenger": [
        _path("M256 128 C184 128 128 176 128 240 C128 288 152 320 192 344 "
              "V392 L248 360 H256 C328 360 384 312 384 240 "
              "C384 176 328 128 256 128 Z"),
        _path("M184 280 L248 208 L272 248 L328 216 L264 304 L240 264 Z", accent=True),
    ],
    "instagram": [
        _shape("rect", x=128, y=128, width=256, height=256, rx=64),
        _shape("circle", cx=256, cy=256, r=64),
        _shape("circle", cx=332, cy=180, r=16, stroke="accent"),
    ],
    "facebook": [
        _path("M208 384 V152 H336 V208 H264 V248 H320 V304 H264 V384 Z"),
        _path("M272 176 H312", accent=True),
    ],
    "snapchat": [
        _path("M184 264 V200 C184 112 328 112 328 200 V264 L368 288 "
              "L336 312 L344 344 L304 336 L280 360 L256 344 L232 360 "
              "L208 336 L168 344 L176 312 L144 288 Z"),
        _path("M232 208 V224 M280 208 V224", accent=True),
    ],
    "tiktok": [
        _path("M272 152 V320 C272 384 160 384 160 320 C160 264 232 264 272 288"),
        _path("M272 152 C280 208 312 224 352 224 "
              "M272 184 C296 240 320 256 352 256", accent=True),
    ],
    "discord": [
        _path("M168 184 H344 C368 184 384 232 384 280 V328 "
              "Q384 352 360 344 L304 320 H208 L152 344 "
              "Q128 352 128 328 V280 C128 232 144 184 168 184 Z"),
        _shape("circle", cx=216, cy=264, r=16, stroke="accent"),
        _shape("circle", cx=296, cy=264, r=16, stroke="accent"),
        _path("M216 304 Q256 328 296 304"),
    ],
    "reddit": [
        _shape("ellipse", cx=256, cy=280, rx=112, ry=80),
        _shape("circle", cx=128, cy=264, r=16),
        _shape("circle", cx=384, cy=264, r=16),
        _path("M256 200 L280 144 L336 160", accent=True),
        _shape("circle", cx=352, cy=160, r=16),
        _path("M216 256 V272 M296 256 V272", accent=True),
        _path("M208 304 Q256 344 304 304"),
    ],
    "pinterest": [
        _shape("circle", cx=256, cy=256, r=136),
        _path("M224 376 L264 200 M240 280 C328 328 376 192 304 160 "
              "C232 128 168 176 184 248", accent=True),
    ],
    "telegram": [
        _path("M128 232 L392 128 L312 384 L232 296 L176 344 L192 264 Z"),
        _path("M192 264 L352 168 L232 296", accent=True),
    ],
    "spotify": [
        _shape("circle", cx=256, cy=256, r=136),
        _path("M168 216 C224 184 288 184 344 216 "
              "M200 304 C232 288 272 288 312 304"),
        _path("M184 264 C224 240 280 240 328 264", accent=True),
    ],
    "netflix": [
        _path("M184 384 V128 M328 384 V128"),
        _path("M184 128 L328 384", accent=True),
    ],
    "amazon-shopping": [
        _shape("rect", x=136, y=184, width=240, height=200, rx=24),
        _path("M208 184 V152 Q208 128 256 128 Q304 128 304 152 V184"),
        _path("M208 320 L256 224 L304 320 M224 288 H288", accent=True),
    ],
    "walmart": [
        _path("M256 128 V192 M256 320 V384 M144 192 L200 224 "
              "M312 288 L368 320 M144 320 L200 288 M312 224 L368 192"),
        _shape("circle", cx=256, cy=256, r=24, stroke="accent"),
    ],
    "temu": [
        _shape("rect", x=136, y=160, width=240, height=224, rx=24),
        _path("M200 160 V128 H312 V160"),
        _path("M208 224 H304 M256 224 V336", accent=True),
    ],
    "uber": [
        _path("M176 144 V280 C176 384 336 384 336 280 V144"),
        _path("M136 384 H376 M256 336 V384", accent=True),
    ],
    "doordash": [
        _path("M136 184 H288 C360 184 392 232 392 280 "
              "C392 328 360 360 312 360 H232 L280 312 H312 "
              "C336 312 344 296 344 280 C344 256 328 232 304 232 H136 Z"),
        _path("M128 280 H232 M128 328 H184", accent=True),
    ],
    "paypal": [
        _path("M192 384 L224 128 H296 C376 128 384 240 304 256 H232"),
        _path("M248 384 L280 200 H320 C376 200 368 304 304 312 H264", accent=True),
    ],
    "outlook": [
        _path("M256 160 H384 V352 H256 M256 208 L320 256 L384 208"),
        _shape("rect", x=128, y=184, width=128, height=176, rx=16),
        _shape("ellipse", cx=192, cy=272, rx=24, ry=40, stroke="accent"),
    ],
    "chatgpt": [
        _path("M184 136 H328 Q376 136 376 184 V280 Q376 328 328 328 "
              "H256 L184 384 V328 Q136 328 136 280 V184 Q136 136 184 136 Z"),
        _path("M256 184 L272 232 L320 248 L272 264 L256 312 "
              "L240 264 L192 248 L240 232 Z", accent=True),
    ],
    "firefox": [
        _path("M184 144 L176 216 C112 264 136 352 224 376 "
              "C312 400 392 344 384 256 L352 176 L336 224 "
              "C304 160 240 160 208 208 Z"),
        _shape("circle", cx=256, cy=280, r=64, stroke="accent"),
    ],
}


# New drawings remain separate so the accepted 0.3.0 catalog and its geometry
# retain their own exact inventory and manifest when the current set grows.
# Original geometric interpretations for the second named-app collection.
# Shared 16-unit outlines and 112..400 control hulls retain the existing family.
NEW_APP_GLYPHS = {
    "x": [
        _path("M152 128 L360 384"),
        _path("M360 128 L152 384", accent=True),
    ],
    "threads": [
        _path("M352 200 C344 152 312 128 256 128 C176 128 144 176 144 256 "
              "C144 336 184 384 264 384 C328 384 368 352 368 304 "
              "C368 256 336 232 280 232 C232 232 200 256 200 288 "
              "C200 320 224 336 256 336 C304 336 320 296 312 248 "
              "C304 208 280 184 248 184 C224 184 208 192 200 208"),
        _path("M208 272 C232 248 280 248 304 272", accent=True),
    ],
    "signal": [
        _path("M208 128 Q256 112 304 128 M344 152 Q376 176 384 224 "
              "M384 272 Q376 320 344 344 M304 376 Q272 392 224 376 "
              "M184 360 L144 384 L160 328 M136 288 Q120 256 136 224 "
              "M152 184 Q168 160 184 152"),
        _path("M200 232 H312 M200 280 H280", accent=True),
    ],
    "twitch": [
        _path("M144 128 H384 V304 L304 384 H240 L200 400 V352 H144 Z"),
        _path("M256 192 V272 M320 192 V272", accent=True),
    ],
    "capcut": [
        _path("M128 168 L384 344 V368 L128 216 Z"),
        _path("M128 344 L384 168 V144 L128 296 Z", accent=True),
    ],
    "disney-plus": [
        _path("M184 192 V368 H248 C360 368 360 192 248 192 Z"),
        _path("M128 168 C200 112 304 112 360 152 "
              "M352 216 H400 M376 192 V240", accent=True),
    ],
    "prime-video": [
        _shape("rect", x=128, y=144, width=256, height=208, rx=32),
        _path("M168 232 H280 L312 256 L280 280 H168", accent=True),
        _path("M160 384 C216 400 304 400 360 368 M336 368 H360 V392"),
    ],
    "microsoft-teams": [
        _shape("circle", cx=312, cy=168, r=32),
        _path("M312 240 H344 Q376 240 376 272 V320 Q376 352 344 352 H312"),
        _shape("rect", x=128, y=200, width=160, height=176, rx=24),
        _path("M168 248 H248 M208 248 V328", accent=True),
    ],
    "zoom": [
        _shape("circle", cx=256, cy=256, r=136),
        _shape("rect", x=176, y=216, width=104, height=96, rx=16, stroke="accent"),
        _path("M280 240 L336 208 V320 L280 288", accent=True),
    ],
    "google-meet": [
        _path("M128 192 L176 144 H304 V368 H128 Z"),
        _path("M304 224 L384 176 V336 L304 288", accent=True),
    ],
    "google-docs": [
        _path("M160 120 H296 L368 192 V392 H160 Z"),
        _path("M296 120 V192 H368"),
        _path("M208 248 H320 M208 296 H320 M208 344 H280", accent=True),
    ],
    "google-sheets": [
        _path("M160 120 H296 L368 192 V392 H160 Z"),
        _path("M296 120 V192 H368"),
        _shape("rect", x=200, y=232, width=128, height=128, rx=8, stroke="accent"),
        _path("M200 272 H328 M200 312 H328 M240 232 V360", accent=True),
    ],
    "onedrive": [
        _path("M176 352 C120 352 112 272 168 256 C152 208 208 176 248 208 "
              "C288 144 360 192 352 240 C400 248 400 336 352 352 Z"),
        _path("M184 304 C232 280 280 280 328 304", accent=True),
    ],
    "google-translate": [
        _shape("rect", x=128, y=136, width=184, height=224, rx=24),
        _path("M312 208 H360 Q384 208 384 232 V376 H232 V360"),
        _path("M168 304 L220 192 L272 304 M188 264 H252", accent=True),
        _path("M320 248 V264 M296 280 H352 "
              "M304 280 Q312 320 352 336 M344 280 Q336 312 304 336"),
    ],
    "google-keep": [
        _path("M160 128 H304 L368 192 V384 H160 Z"),
        _path("M224 304 C224 280 200 264 200 232 C200 168 312 168 312 232 "
              "C312 264 288 280 288 304 Z", accent=True),
        _path("M232 336 H280"),
    ],
    "google-wallet": [
        _path("M144 208 L184 144 H328 L352 208"),
        _shape("rect", x=128, y=208, width=256, height=168, rx=32),
        _path("M144 264 H368 M304 312 H344", accent=True),
    ],
    "cash-app": [
        _shape("rect", x=144, y=128, width=224, height=256, rx=48),
        _path("M304 200 C288 176 224 176 208 208 C184 240 224 256 256 264 "
              "C296 272 320 288 304 320 C288 352 224 352 208 328 "
              "M256 152 V360", accent=True),
    ],
    "venmo": [
        _path("M152 152 L240 384 H288 L368 152"),
        _path("M208 152 L264 304 L312 152", accent=True),
    ],
    "ebay": [
        _path("M144 128 H288 L392 232 L240 384 L128 272 V144 Q128 128 144 128 Z"),
        _shape("circle", cx=184, cy=184, r=20, stroke="accent"),
        _path("M216 272 L296 192 M256 312 L336 232", accent=True),
    ],
    "mcdonalds": [
        _path("M128 376 V232 C128 112 256 112 256 232 V376"),
        _path("M256 232 C256 112 384 112 384 232 V376", accent=True),
    ],
    "starbucks": [
        _path("M160 208 H336 L312 376 H184 Z"),
        _path("M144 208 H352 V176 H144 Z"),
        _path("M216 144 Q200 128 216 112 M280 144 Q264 128 280 112 "
              "M248 232 L256 256 L280 264 L256 272 L248 296 "
              "L240 272 L216 264 L240 256 Z", accent=True),
    ],
    "duolingo": [
        _path("M152 144 L216 184 Q256 168 296 184 L360 144 V288 "
              "C360 392 152 392 152 288 Z"),
        _shape("ellipse", cx=212, cy=248, rx=32, ry=40),
        _shape("ellipse", cx=300, cy=248, rx=32, ry=40),
        _path("M240 296 L256 312 L272 296 Z", accent=True),
    ],
    "waze": [
        _path("M256 144 C184 144 136 192 136 256 C136 296 160 320 192 328 "
              "H312 L368 272 V256 C368 192 320 144 256 144 Z"),
        _shape("circle", cx=200, cy=360, r=24),
        _shape("circle", cx=312, cy=360, r=24),
        _path("M208 280 H280 L304 256", accent=True),
    ],
    "canva": [
        _path("M352 184 C328 144 296 128 256 128 C176 128 128 184 128 256 "
              "C128 328 176 384 256 384 C296 384 328 368 352 328"),
        _path("M208 312 L320 200 L352 232 L240 344 H208 Z", accent=True),
    ],
}


# Original vector interpretations for the third named-app collection.
# Distinct browser, account-approval and time-key silhouettes retain shared geometry.
THIRD_APP_GLYPHS = {
    "linkedin": [
        _shape("rect", x=128, y=128, width=256, height=256, rx=32),
        _shape("circle", cx=192, cy=200, r=16, stroke="accent"),
        _path("M192 248 V328", accent=True),
        _path("M248 328 V248 M248 280 C248 232 320 232 320 280 V328"),
    ],
    "github": [
        _shape("circle", cx=176, cy=168, r=28),
        _shape("circle", cx=336, cy=168, r=28),
        _shape("circle", cx=176, cy=352, r=28),
        _path("M176 196 V324 M176 280 C176 232 336 264 336 196", accent=True),
    ],
    "notion": [
        _path("M144 168 L176 136 H368 V352 L336 384 H144 Z"),
        _path("M144 168 H336 V384 M336 168 L368 136"),
        _path("M184 328 V224 L288 328 V224", accent=True),
    ],
    "microsoft-edge": [
        _path("M376 288 C376 352 328 384 264 384 C184 384 128 328 128 256 "
              "C128 184 184 128 256 128 C320 128 368 168 384 224"),
        _path("M128 256 C160 200 240 192 304 232 C352 256 352 312 304 328 "
              "C248 352 184 312 192 264", accent=True),
    ],
    "brave": [
        _path("M256 120 L368 168 V272 C368 328 320 368 256 392 "
              "C192 368 144 328 144 272 V168 Z"),
        _path("M200 232 L224 208 L256 224 L288 208 L312 232 "
              "L304 296 L272 328 H240 L208 296 Z", accent=True),
        _path("M232 272 L256 288 L280 272"),
    ],
    "microsoft-authenticator": [
        _shape("rect", x=168, y=120, width=176, height=272, rx=32),
        _path("M224 152 H288 M232 360 H280"),
        _path("M208 256 L248 296 L320 208", accent=True),
    ],
    "google-authenticator": [
        _shape("circle", cx=208, cy=208, r=64),
        _path("M256 256 L384 384 M312 312 L336 288 M352 352 L376 328"),
        _path("M208 176 V208 H232", accent=True),
    ],
    "samsung-smartthings": [
        _shape("circle", cx=160, cy=160, r=28),
        _shape("circle", cx=352, cy=160, r=28),
        _shape("circle", cx=160, cy=352, r=28),
        _shape("circle", cx=352, cy=352, r=28),
        _shape("circle", cx=256, cy=256, r=32, stroke="accent"),
        _path("M180 180 L233 233 M332 180 L279 233 "
              "M180 332 L233 279 M332 332 L279 279", accent=True),
    ],
}


# Original companion interpretations extend the same 16-unit stroke and inset.
FOURTH_APP_GLYPHS = {
    "good-lock": [
        _shape("rect", x=144, y=224, width=224, height=160, rx=36),
        _path("M192 224 V176 Q192 128 256 128 Q320 128 320 176 V192"),
        _shape("circle", cx=256, cy=288, r=20, stroke="accent"),
        _path("M256 308 V344", accent=True),
    ],
    "connect-iq-store": [
        _shape("rect", x=168, y=152, width=176, height=208, rx=40),
        _path("M216 152 V112 H296 V152 M216 360 V400 H296 V360"),
        _shape("rect", x=208, y=208, width=32, height=32, rx=8, stroke="accent"),
        _shape("rect", x=272, y=208, width=32, height=32, rx=8, stroke="accent"),
        _shape("rect", x=208, y=272, width=32, height=32, rx=8, stroke="accent"),
        _shape("rect", x=272, y=272, width=32, height=32, rx=8, stroke="accent"),
    ],
    "steam": [
        _path("M192 176 H320 C352 176 368 208 376 248 L392 328 "
              "C400 368 368 384 344 352 L304 304 H208 L168 352 "
              "C144 384 112 368 120 328 L136 248 C144 208 160 176 192 176 Z"),
        _path("M176 240 H224 M200 216 V264", accent=True),
        _shape("circle", cx=312, cy=232, r=12, stroke="accent"),
        _shape("circle", cx=344, cy=264, r=12, stroke="accent"),
    ],
    "reuters": [
        _path("M136 144 H344 V368 H160 Q136 368 136 344 Z "
              "M344 192 H376 V344 Q376 368 344 368"),
        _shape("rect", x=176, y=184, width=72, height=64, rx=8, stroke="accent"),
        _path("M280 192 H312 M280 232 H312 M176 288 H304 M176 328 H272"),
    ],
    "home-depot": [
        _path("M112 216 L256 128 L400 216 M144 216 V384 H368 V216"),
        _path("M216 240 L256 216 L312 240 L296 272 L256 256 "
              "L232 296 L200 280 Z M248 272 L216 344", accent=True),
    ],
    "patreon": [
        _path("M144 144 H368 V216 C336 216 336 296 368 296 V368 "
              "H144 V296 C176 296 176 216 144 216 Z"),
        _path("M256 304 L208 256 C176 224 216 192 240 216 L256 232 "
              "L272 216 C296 192 336 224 304 256 Z", accent=True),
    ],
}


def icon_catalog(version: str = VERSION) -> list[dict]:
    """Return labels and explicit assignment identities for an admitted revision."""
    if version not in VERSIONS:
        raise ValueError("Unsupported icon artwork version")
    catalog = [{"id": name, "label": name.replace("-", " ").title(), "kind": "function",
                "category": "general"} for name in FUNCTIONS]
    if version in ("0.1.0", "0.2.0"):
        return catalog
    seen, packages = set(FUNCTIONS), set()
    if version == "0.3.0":
        apps = APP_CATALOG
    elif version == "0.4.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG)
    elif version in ("0.5.0", "0.6.0"):
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG)
    else:
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG)
    for app in apps:
        if not isinstance(app, dict):
            raise ValueError("Malformed named-app catalog")
        identifier, package = app.get("id"), app.get("android_package")
        if (not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", identifier)
                or identifier in seen):
            raise ValueError("Duplicate or unsafe named-app icon ID")
        if (not isinstance(package, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", package)
                or package in packages):
            raise ValueError("Duplicate or malformed Android package ID")
        if any(not isinstance(app.get(key), str) or not app[key].strip()
               for key in ("label", "store_title", "category", "store_url", "selection_basis")):
            raise ValueError("Missing named-app label or source identity")
        url = urlparse(app["store_url"])
        if (url.scheme != "https" or url.netloc != "play.google.com" or url.path != "/store/apps/details"
                or parse_qs(url.query) != {"id": [package]} or url.fragment or app.get("kind") != "app"):
            raise ValueError("Named-app store URL must identify its exact official package")
        seen.add(identifier)
        packages.add(package)
        catalog.append(dict(app))
    drawings = set(APP_GLYPHS)
    if version in ("0.4.0", "0.5.0", "0.6.0", "0.7.0"):
        if drawings & set(NEW_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(NEW_APP_GLYPHS)
    if version in ("0.5.0", "0.6.0", "0.7.0"):
        if drawings & set(THIRD_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(THIRD_APP_GLYPHS)
    if version == "0.7.0":
        if drawings & set(FOURTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(FOURTH_APP_GLYPHS)
    if drawings != seen - set(FUNCTIONS):
        raise ValueError("Named-app catalog and drawings differ")
    return catalog


def _validated(document: dict) -> None:
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    try:
        validate(document)
    except (TypeError, AttributeError) as error:
        raise ValueError("Malformed token document") from error


def token_path(version: str = VERSION) -> Path:
    """Select the shared palette without changing a historical artwork revision."""
    if version not in VERSIONS:
        raise ValueError("Unsupported icon artwork version")
    return ROOT / ("tokens-monochrome.json" if version in ("0.6.0", "0.7.0") else "tokens.json")


def load_icon_tokens(version: str = VERSION, path: Path | None = None) -> dict:
    """Accept an explicit copy only when it matches the version's shared document."""
    canonical = load(token_path(version))
    if path is None:
        return canonical
    document = load(path)
    if document != canonical:
        raise ValueError("Icon tokens differ from the shared document for this artwork version")
    return document


def _monochrome(document: dict) -> None:
    for appearance, background, foreground in (("Clair", "#ffffff", "#000000"),
                                                ("Obscur", "#000000", "#ffffff")):
        palette = document["themes"][appearance]
        if any(len({color[index:index + 2].lower() for index in (1, 3, 5)}) != 1
               for color in palette.values()):
            raise ValueError("Monochrome icon tokens must contain only neutral colors")
        if (any(palette[role].lower() != background for role in ("canvas", "panel"))
                or any(palette[role].lower() != foreground for role in ("text", "accent"))):
            raise ValueError("Monochrome icons require opposite pure black and white backgrounds and glyphs")


def _render_icon(function: str, appearance: str, document: dict, grant: str, *, version: str,
                 label: str | None = None) -> bytes:
    palette = document["themes"][appearance]
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "width": str(SIZE), "height": str(SIZE),
        "viewBox": "0 0 512 512", "role": "img", "aria-label": label or function,
    })
    svg.append(ET.Comment("\n" + grant + "\n"))
    ET.SubElement(svg, "rect", {"x": "32", "y": "32", "width": "448", "height": "448",
                               "rx": "104", "fill": palette["panel"]})
    group = ET.SubElement(svg, "g", {"fill": "none", "stroke": palette["text"],
        "stroke-width": str(12 if version == "0.1.0" else STROKE),
        "stroke-linecap": "round", "stroke-linejoin": "round"})
    drawings = (GLYPHS if version == "0.1.0" else
                CURRENT_GLYPHS if function in CURRENT_GLYPHS else
                APP_GLYPHS if function in APP_GLYPHS else
                NEW_APP_GLYPHS if function in NEW_APP_GLYPHS else
                THIRD_APP_GLYPHS if function in THIRD_APP_GLYPHS else FOURTH_APP_GLYPHS)
    for tag, attributes in drawings[function]:
        ET.SubElement(group, tag, {
            key: palette[value] if value in ("accent", "text") else value
            for key, value in attributes.items()
        })
    ET.indent(svg, space="  ")
    return (ET.tostring(svg, encoding="unicode") + "\n").encode("utf-8")


def render_icons(document: dict, *, version: str = VERSION) -> dict[str, bytes]:
    """Return the selected SVG inventory and its deterministic identity manifest."""
    _validated(document)
    if version not in VERSIONS:
        raise ValueError("Unsupported icon artwork version")
    if version in ("0.6.0", "0.7.0"):
        _monochrome(document)
    catalog = icon_catalog(version)
    names = [entry["id"] for entry in catalog]
    grant = license_text()
    if "--" in grant:
        raise ValueError("The license cannot be embedded safely in an XML comment")
    files = {}
    records = []
    for appearance in ("Clair", "Obscur"):
        for entry in catalog:
            function = entry["id"]
            name = f"{appearance}/{function}.svg"
            payload = _render_icon(function, appearance, document, grant, version=version,
                                   label=entry["label"] if entry["kind"] == "app" else None)
            files[name] = payload
            records.append({"appearance": appearance, "function": function, "path": name,
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {
        "schema_version": 1, "generator": "themeforge.icons", "version": version,
        "token_schema": document["schema_version"], "token_version": document["version"],
        "size": [SIZE, SIZE], "stroke_width": 12 if version == "0.1.0" else STROKE,
        "tile": {"x": 32, "y": 32, "width": 448, "height": 448, "radius": 104},
        "glyph_centerline_bounds": [112, 112, 400, 400],
        "palette_roles": {"tile": "panel", "glyph": "text", "emphasis": "accent"},
        "functions": names, "files": records,
        "scope": "Original functional glyphs; no brand logos, font assets or phone installation",
    }
    if version in ("0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0"):
        if version == "0.3.0":
            date, scope = CATALOG_DATE, CATALOG_SCOPE
        elif version == "0.4.0":
            date, scope = NEW_CATALOG_DATE, NEW_CATALOG_SCOPE
        elif version in ("0.5.0", "0.6.0"):
            date, scope = THIRD_CATALOG_DATE, THIRD_CATALOG_SCOPE
        else:
            date, scope = FOURTH_CATALOG_DATE, FOURTH_CATALOG_SCOPE
        manifest.update(catalog=catalog, catalog_date=date, catalog_scope=scope,
                        scope="Original themed interpretations for named apps and general functions; "
                              "app names identify intended assignments, not publisher endorsement or installation")
    if version in ("0.6.0", "0.7.0"):
        manifest["palette_variant"] = "monochrome"
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return files


def _linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _safe_output(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    if path == path.parent:
        raise ValueError("The icon output must not be a filesystem root")
    if path == ROOT / "dist" or ROOT / "dist" in path.parents:
        raise ValueError("Icon output must stay outside managed desktop dist")
    for ancestor in (path, *path.parents):
        if ancestor.exists() or ancestor.is_symlink():
            if _linked(ancestor):
                raise ValueError("Icon output paths must not contain links or reparse points")
    return path


def _read_tree(root: Path) -> tuple[dict[str, bytes], set[str]]:
    files = {}
    directories = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            if _linked(path):
                raise ValueError("Icon output contains a link or reparse point")
            name = path.relative_to(root).as_posix()
            if path.is_dir():
                directories.add(name)
                pending.append(path)
            elif path.is_file():
                files[name] = path.read_bytes()
            else:
                raise ValueError("Icon output contains a non-regular entry")
    return files, directories


def build_icons(document: dict, output: Path, *, check: bool = False, version: str = VERSION) -> dict:
    """Create a new tree or compare an existing one, never replace user output."""
    files = render_icons(document, version=version)
    output = _safe_output(Path(output))
    if check:
        if not output.is_dir():
            raise ValueError("Icon check requires an existing generated output directory")
        actual, directories = _read_tree(output)
        if actual != files or directories != {"Clair", "Obscur"}:
            raise ValueError("Icon output differs: changed, missing or extra entries")
    else:
        if output.exists():
            raise ValueError("Icon generation requires a new output directory; existing files are preserved")
        output.parent.mkdir(parents=True, exist_ok=True)
        output = _safe_output(output)
        output.mkdir(exist_ok=False)
        # Exclusive writes preserve partial output as evidence if generation is interrupted.
        for name, payload in files.items():
            path = output / name
            path.parent.mkdir(exist_ok=True)
            with path.open("xb") as stream:
                stream.write(payload)
    return json.loads(files["manifest.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, help="An explicit copy of this artwork version's shared token document")
    parser.add_argument("--output", type=Path, required=True, help="A new folder outside managed dist")
    parser.add_argument("--check", action="store_true", help="Compare all generated bytes without writing")
    parser.add_argument("--version", choices=VERSIONS, default=VERSION, help="Artwork revision to generate or verify")
    options = parser.parse_args(argv)
    try:
        manifest = build_icons(load_icon_tokens(options.version, options.tokens), options.output,
                               check=options.check, version=options.version)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.exit(1, f"Icon generation: {error}\n")
    print(f'{"Verified" if options.check else "Generated"} {len(manifest["files"])} original SVG icons')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
