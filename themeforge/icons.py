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
    FIFTH_APP_CATALOG, FIFTH_CATALOG_DATE, FIFTH_CATALOG_SCOPE,
    SIXTH_APP_CATALOG, SIXTH_CATALOG_DATE, SIXTH_CATALOG_SCOPE,
    SEVENTH_APP_CATALOG, SEVENTH_CATALOG_DATE, SEVENTH_CATALOG_SCOPE,
    EIGHTH_APP_CATALOG, EIGHTH_CATALOG_DATE, EIGHTH_CATALOG_SCOPE,
    NINTH_APP_CATALOG, NINTH_CATALOG_DATE, NINTH_CATALOG_SCOPE,
    TENTH_APP_CATALOG, TENTH_CATALOG_DATE, TENTH_CATALOG_SCOPE,
    ELEVENTH_APP_CATALOG, ELEVENTH_CATALOG_DATE, ELEVENTH_CATALOG_SCOPE,
    TWELFTH_APP_CATALOG, TWELFTH_CATALOG_DATE, TWELFTH_CATALOG_SCOPE,
    THIRTEENTH_APP_CATALOG, THIRTEENTH_CATALOG_DATE, THIRTEENTH_CATALOG_SCOPE,
    FOURTEENTH_APP_CATALOG, FOURTEENTH_CATALOG_DATE, FOURTEENTH_CATALOG_SCOPE,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.17.0"
VERSIONS = ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", VERSION)
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


# Broader media, shopping, travel, utility and game interpretations retain the
# same safe inset and stroke. These drawings belong only to the 0.8.0 catalog.
FIFTH_APP_GLYPHS = {
    "youtube-music": [
        _shape("circle", cx=256, cy=256, r=128),
        _shape("circle", cx=256, cy=256, r=80),
        _path("M240 216 L296 256 L240 296 Z", accent=True, filled=True),
    ],
    "audible": [
        _path("M136 248 Q192 224 256 256 Q320 224 376 248 V368 "
              "Q320 344 256 376 Q192 344 136 368 Z M256 256 V376"),
        _path("M192 192 Q256 128 320 192 M224 216 Q256 184 288 216", accent=True),
    ],
    "amazon-kindle": [
        _path("M128 152 Q192 128 256 168 Q320 128 384 152 V352 "
              "Q320 328 256 368 Q192 328 128 352 Z M256 168 V368"),
        _path("M296 160 V264 L320 240 L344 264 V152", accent=True),
    ],
    "pocket-casts": [
        _shape("circle", cx=256, cy=256, r=128),
        _path("M184 328 V248 Q184 184 248 184 H328 "
              "M224 328 V264 Q224 224 264 224 H328", accent=True),
        _shape("circle", cx=288, cy=288, r=24, fill="accent", stroke="accent"),
    ],
    "vlc": [
        _path("M256 128 L144 368 H368 Z M128 392 H384"),
        _path("M208 240 H304 M176 304 H336", accent=True),
    ],
    "shazam": [
        _path("M184 344 C128 296 136 200 192 160 C248 120 328 152 344 208 "
              "C360 256 320 280 288 304 C264 320 280 368 240 384"),
        _path("M208 248 C208 192 296 192 296 240 C296 272 256 264 256 304", accent=True),
    ],
    "soundcloud": [
        _path("M248 328 H344 C400 328 400 240 344 240 "
              "C328 176 248 176 232 240"),
        _path("M128 264 V304 M168 232 V328 M208 208 V328 M248 240 V328", accent=True),
    ],
    "hulu": [
        _shape("rect", x=128, y=152, width=256, height=208, rx=32),
        _path("M216 392 H296 M256 360 V392"),
        _path("M208 208 V304 M304 208 V304 M208 256 H304", accent=True),
    ],
    "target": [
        _shape("circle", cx=232, cy=280, r=104),
        _shape("circle", cx=232, cy=280, r=48),
        _path("M232 280 L376 136 M312 136 H376 V200", accent=True),
    ],
    "costco": [
        _path("M128 184 L256 128 L384 184 V376 H128 Z"),
        _shape("rect", x=208, y=248, width=96, height=128, rx=8),
        _path("M176 208 H336 M160 280 H176 M336 280 H352 M160 328 H176 M336 328 H352", accent=True),
    ],
    "best-buy": [
        _path("M128 208 L192 144 H384 V352 H192 L128 288 Z"),
        _shape("circle", cx=184, cy=248, r=16),
        _shape("rect", x=240, y=208, width=96, height=80, rx=8, stroke="accent"),
        _path("M264 184 V208 M312 184 V208 M264 288 V312 M312 288 V312", accent=True),
    ],
    "etsy": [
        _shape("circle", cx=168, cy=328, r=40),
        _shape("circle", cx=272, cy=328, r=40),
        _path("M192 296 L352 144 M248 296 L128 144", accent=True),
        _shape("circle", cx=224, cy=264, r=12),
    ],
    "aliexpress": [
        _shape("rect", x=160, y=176, width=224, height=192, rx=24),
        _path("M160 232 H384 M272 176 V232"),
        _path("M128 288 H224 M128 336 H192 M304 288 L328 312 L360 264", accent=True),
    ],
    "shein": [
        _path("M256 192 C256 136 320 136 320 184 C320 208 280 224 256 240 "
              "L384 320 H128 L256 240", accent=True),
        _path("M152 352 H360"),
    ],
    "instacart": [
        _path("M144 368 L208 240 Q232 216 256 240 L288 272 Q312 296 288 320 Z"),
        _path("M256 240 C248 192 280 160 312 144 Q336 192 288 248 "
              "M288 272 Q336 208 384 232 Q368 280 304 288", accent=True),
        _path("M200 280 L224 304 M176 328 L200 344"),
    ],
    "airbnb": [
        _path("M128 240 L256 128 L384 240 M160 224 V376 H352 V224"),
        _path("M256 328 L216 288 C184 256 216 224 240 248 L256 264 "
              "L272 248 C296 224 328 256 296 288 Z", accent=True),
    ],
    "booking": [
        _shape("rect", x=168, y=128, width=176, height=256, rx=16),
        _path("M208 184 H224 M288 184 H304 M208 240 H224 M288 240 H304", accent=True),
        _path("M232 384 V328 Q232 304 256 304 Q280 304 280 328 V384 M144 384 H368"),
    ],
    "expedia": [
        _path("M160 160 C256 112 368 176 384 272 C400 352 288 400 200 360"),
        _path("M128 264 H224 V176 L256 136 L288 176 V264 H384 "
              "L352 296 H288 V344 L256 376 L224 344 V296 H160 Z", accent=True),
    ],
    "lyft": [
        _path("M128 320 V248 H176 L224 184 H304 L352 248 H384 V320 H352 M288 320 H224 M160 320 H128"),
        _shape("circle", cx=192, cy=320, r=32),
        _shape("circle", cx=320, cy=320, r=32),
        _path("M224 248 H320 M216 144 Q256 120 296 144", accent=True),
    ],
    "uber-eats": [
        _path("M160 192 H352 L376 376 H136 Z M208 192 V168 Q208 128 256 128 Q304 128 304 168 V192"),
        _path("M208 248 V272 Q208 288 224 288 Q240 288 240 272 V248 "
              "M224 248 V328 M288 248 V328", accent=True),
    ],
    "google-earth": [
        _shape("circle", cx=256, cy=256, r=128),
        _path("M160 184 L208 160 L248 184 L232 232 L192 240 L176 288 L144 264 "
              "M288 240 L344 224 L368 256 L336 288 L320 352 L280 320 Z", accent=True),
    ],
    "google-news": [
        _path("M128 184 V144 H336 V184"),
        _shape("rect", x=152, y=184, width=232, height=192, rx=16),
        _shape("rect", x=184, y=216, width=64, height=64, rx=8, stroke="accent"),
        _path("M280 224 H344 M280 264 H344 M184 328 H344", accent=True),
    ],
    "galaxy-wearable": [
        _path("M176 256 V352 Q176 376 200 376 Q224 376 224 352 V208 "
              "C224 144 128 144 128 208 C128 248 152 256 176 256 Z"),
        _path("M336 256 V352 Q336 376 312 376 Q288 376 288 352 V208 "
              "C288 144 384 144 384 208 C384 248 360 256 336 256 Z", accent=True),
    ],
    "files-by-google": [
        _path("M128 208 V144 H224 L256 176 H384 V368 H128 Z"),
        _path("M256 224 V320 M208 272 L256 320 L304 272", accent=True),
    ],
    "adobe-acrobat": [
        _path("M144 128 H304 L368 192 V384 H144 Z M304 128 V192 H368"),
        _path("M192 320 L288 224 L320 256 L224 352 H192 Z M264 248 L296 280", accent=True),
    ],
    "microsoft-word": [
        _shape("rect", x=144, y=128, width=224, height=256, rx=24),
        _path("M192 208 H320 M192 256 H272 M192 304 H264"),
        _path("M312 288 V352 M296 288 H328 M296 352 H328", accent=True),
    ],
    "microsoft-excel": [
        _shape("rect", x=128, y=144, width=256, height=224, rx=16),
        _path("M128 216 H384 M216 144 V368 M160 176 H184 M160 264 H184 M160 312 H184"),
        _path("M256 256 L336 328 M336 256 L256 328", accent=True),
    ],
    "microsoft-powerpoint": [
        _shape("rect", x=128, y=144, width=256, height=192, rx=16),
        _path("M256 336 V384 M208 384 L256 352 L304 384"),
        _path("M256 184 V248 H320 Q320 184 256 184 Z", accent=True, filled=True),
        _path("M216 200 C160 240 200 312 264 288", accent=True),
    ],
    "google-slides": [
        _path("M160 120 H296 L368 192 V392 H160 Z M296 120 V192 H368"),
        _shape("rect", x=200, y=232, width=128, height=96, rx=8, stroke="accent"),
        _path("M240 296 H288", accent=True),
    ],
    "google-lens": [
        _path("M128 216 V144 H200 M312 144 H384 V216 M384 312 V384 H312 M200 384 H128 V312"),
        _shape("circle", cx=256, cy=256, r=72, stroke="accent"),
    ],
    "roblox": [
        _path("M256 128 L384 200 V328 L256 400 L128 328 V200 Z "
              "M128 200 L256 272 L384 200 M256 272 V400"),
        _path("M192 164 L320 236 M192 308 L224 328 M288 328 L320 308", accent=True),
    ],
    "minecraft": [
        _path("M144 152 H280 L368 240 L328 280 L256 208 H176 L144 240 H112 V184 Z"),
        _path("M240 224 L272 256 L176 384 L144 352 Z", accent=True, filled=True),
    ],
}


# Original0.9 drawings retain the existing inset and shared stroke.
SIXTH_APP_GLYPHS = {
"slack": [
        _path("M208 136 L176 376 M304 136 L272 376 "
              "M136 216 H376 M128 304 H368", accent=True),
    ],
    "trello": [
        _shape("rect", x=128, y=136, width=256, height=240, rx=24),
        _shape("rect", x=168, y=184, width=64, height=144, rx=12, stroke="accent"),
        _shape("rect", x=280, y=184, width=64, height=96, rx=12, stroke="accent"),
    ],
    "todoist": [
        _path("M136 176 L160 200 L208 152 M136 264 L160 288 L208 240 "
              "M136 352 L160 376 L208 328", accent=True),
        _path("M248 176 H376 M248 264 H344 M248 352 H312"),
    ],
    "ticktick": [
        _shape("circle", cx=256, cy=272, r=112),
        _path("M224 128 H288 M256 128 V160"),
        _path("M192 272 L240 320 L320 224", accent=True),
    ],
    "evernote": [
        _path("M152 352 V216 Q152 144 224 144 H304 Q368 144 368 208 "
              "V312 Q368 368 320 368 Q280 368 280 328 V280 H232 V352"),
        _shape("ellipse", cx=224, cy=216, rx=40, ry=56, stroke="accent"),
        _shape("circle", cx=320, cy=208, r=8, fill="accent", stroke="accent"),
    ],
    "obsidian": [
        _path("M224 128 L336 168 L368 312 L280 384 L144 320 L168 200 Z"),
        _path("M224 128 L248 240 L168 200 M248 240 L336 168 "
              "M248 240 L280 384 M248 240 L144 320", accent=True),
    ],
    "dropbox": [
        _path("M128 200 L192 144 L256 184 L320 144 L384 200 "
              "L320 248 L256 216 L192 248 Z"),
        _path("M160 232 V320 L256 376 L352 320 V232 M256 272 V376", accent=True),
    ],
    "proton-mail": [
        _path("M256 128 L384 184 V280 Q384 344 256 392 Q128 344 128 280 V184 Z"),
        _shape("rect", x=176, y=208, width=160, height=112, rx=16),
        _path("M176 224 L256 280 L336 224", accent=True),
    ],
    "yahoo-mail": [
        _path("M128 224 L256 128 L384 224 V368 H128 Z M128 224 L184 264 M384 224 L328 264"),
        _path("M216 264 L256 304 L296 264 M256 304 V344", accent=True),
    ],
    "google-tasks": [
        _path("M376 232 C384 312 320 384 248 384 C176 384 128 328 128 256 "
              "C128 184 184 128 256 128 H312"),
        _path("M200 248 L248 296 L368 152", accent=True),
    ],
    "google-one": [
        _shape("circle", cx=256, cy=256, r=128),
        _path("M224 216 L264 184 V328 M224 328 H304", accent=True),
    ],
    "microsoft-copilot": [
        _path("M160 184 Q128 184 128 216 V296 Q128 328 160 328 H232 L280 184 Z"),
        _path("M280 184 H352 Q384 184 384 216 V296 Q384 328 352 328 H232 Z", accent=True),
    ],
    "google-gemini": [
        _path("M232 152 Q248 232 320 248 Q248 264 232 344 "
              "Q216 264 144 248 Q216 232 232 152 Z"),
        _path("M352 128 Q360 160 392 168 Q360 176 352 208 "
              "Q344 176 312 168 Q344 160 352 128 Z", accent=True),
    ],
    "claude": [
        _path("M160 312 C160 192 352 192 352 312 M128 344 H384"),
        _path("M256 128 V168 M152 168 L176 200 M360 168 L336 200 "
              "M128 248 H168 M344 248 H384", accent=True),
    ],
    "perplexity": [
        _path("M256 128 L384 256 L256 384 L128 256 Z"),
        _path("M200 312 L240 224 L312 192 L280 272 Z", accent=True),
    ],
    "bitwarden": [
        _path("M256 128 L368 176 V264 C368 328 304 376 256 400 "
              "C208 376 144 328 144 264 V176 Z"),
        _shape("circle", cx=256, cy=232, r=32, stroke="accent"),
        _path("M256 264 V328 M256 296 H280", accent=True),
    ],
    "apple-music": [
        _shape("rect", x=144, y=128, width=224, height=256, rx=48),
        _path("M240 320 V184 L328 160 V216 L240 240", accent=True),
        _shape("ellipse", cx=208, cy=320, rx=32, ry=24, stroke="accent"),
    ],
    "apple-tv": [
        _shape("rect", x=128, y=192, width=256, height=160, rx=24),
        _path("M208 136 L256 192 L304 136"),
        _path("M184 232 H248 M216 232 V312 M272 232 L304 312 L336 232", accent=True),
    ],
    "hbo-max": [
        _shape("circle", cx=208, cy=256, r=88),
        _path("M296 216 L384 168 V344 L296 296"),
        _shape("circle", cx=184, cy=216, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=248, cy=256, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=184, cy=296, r=12, fill="accent", stroke="accent"),
    ],
    "peacock": [
        _path("M256 376 L144 272 Q112 176 176 152 Q224 144 256 224 "
              "Q288 144 336 152 Q400 176 368 272 Z"),
        _path("M256 192 C200 248 200 304 256 336 C312 304 312 248 256 192 Z", accent=True),
    ],
    "paramount-plus": [
        _path("M128 360 L224 176 L288 288 L320 232 L384 360 Z"),
        _path("M192 240 L224 264 L248 224 M320 144 H384 M352 112 V176", accent=True),
    ],
    "plex": [
        _path("M128 160 V352 M384 160 V352"),
        _path("M176 160 L288 256 L176 352 M248 160 L360 256 L248 352", accent=True),
    ],
    "tubi": [
        _path("M128 176 H384 V224 C344 224 344 288 384 288 V336 "
              "H128 V288 C168 288 168 224 128 224 Z"),
        _path("M232 216 L296 256 L232 296 Z", accent=True),
    ],
    "pluto-tv": [
        _path("M144 184 L328 368 C232 400 112 280 144 184 Z"),
        _path("M192 232 L328 136 M328 136 H376 V184 M248 352 L224 392 H328", accent=True),
    ],
"crunchyroll": [
        _path("M128 256 Q192 152 280 176 Q344 192 384 256 "
              "Q320 344 232 336 Q168 320 128 256 Z"),
        _shape("circle", cx=256, cy=256, r=56, stroke="accent"),
        _path("M280 128 V160 M328 144 L312 176", accent=True),
    ],
    "pandora": [
        _shape("rect", x=128, y=200, width=256, height=168, rx=24),
        _path("M176 200 L320 128 M152 248 H256", accent=True),
        _shape("circle", cx=200, cy=304, r=32),
        _path("M288 272 H344 M288 312 H344", accent=True),
    ],
    "iheartradio": [
        _path("M256 368 L160 280 C112 232 160 176 208 208 L256 248 "
              "L304 208 C352 176 400 232 352 280 Z"),
        _path("M192 152 Q256 112 320 152 M216 184 Q256 160 296 184", accent=True),
    ],
    "siriusxm": [
        _path("M232 208 L280 160 L328 208 L280 256 Z"),
        _path("M128 256 L184 200 L224 240 L168 296 Z "
              "M304 184 L360 128 L400 168 L344 224 Z", accent=True),
        _path("M280 256 L312 288 M264 304 Q288 328 320 320 "
              "M240 328 Q280 376 344 360", accent=True),
    ],
    "adobe-lightroom": [
        _shape("rect", x=128, y=144, width=256, height=176, rx=16),
        _path("M152 288 L216 216 L264 264 L304 224 L360 288", accent=True),
        _shape("circle", cx=312, cy=192, r=16),
        _path("M176 352 V384 M256 344 V384 M336 360 V384", accent=True),
    ],
    "photoshop-express": [
        _path("M176 128 V336 H384 M128 176 H336 V384"),
        _path("M224 288 L312 200 M312 144 V176 M360 192 H384 "
              "M344 160 L360 144", accent=True),
    ],
    "snapseed": [
        _path("M152 360 C128 240 224 136 368 136 "
              "C392 256 296 368 176 368 Z"),
        _path("M176 344 L328 176 M224 296 L216 248 M272 248 L320 256", accent=True),
    ],
    "picsart": [
        _path("M256 128 C184 128 128 184 128 256 C128 336 192 384 264 384 "
              "Q304 384 304 344 Q304 312 336 304 Q384 296 384 248 "
              "C384 176 328 128 256 128 Z"),
        _shape("circle", cx=184, cy=232, r=16, stroke="accent"),
        _shape("circle", cx=240, cy=184, r=16, stroke="accent"),
        _shape("circle", cx=312, cy=200, r=16, stroke="accent"),
    ],
    "strava": [
        _path("M128 376 L248 168 L368 376"),
        _path("M248 168 V120 H312 L288 144 H248", accent=True),
        _path("M184 280 H216 L248 224 L280 280 H312", accent=True),
    ],
    "fitbit": [
        _path("M216 144 L200 112 H312 L296 144 "
              "M216 368 L200 400 H312 L296 368"),
        _shape("rect", x=168, y=144, width=176, height=224, rx=56),
        _shape("circle", cx=232, cy=232, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=280, cy=232, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=232, cy=280, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=280, cy=280, r=12, fill="accent", stroke="accent"),
    ],
    "google-fit": [
        _path("M256 384 L152 280 C112 232 136 168 184 160 "
              "Q224 152 256 192 Q288 152 328 160 C376 168 400 232 360 280 Z"),
        _path("M200 256 L240 296 L320 216", accent=True),
    ],
    "myfitnesspal": [
        _shape("circle", cx=256, cy=256, r=88),
        _path("M120 160 V216 Q120 240 144 240 V368 "
              "M144 160 V240 M168 160 V216 Q168 240 144 240", accent=True),
        _path("M384 160 C352 208 352 248 384 272 V368 M384 160 V272", accent=True),
    ],
    "alltrails": [
        _path("M128 304 L224 144 L280 240 L320 184 L384 304"),
        _path("M224 144 L208 208 L240 192 M320 184 L304 240 L336 232", accent=True),
        _path("M256 288 C192 320 304 328 264 352 Q248 368 208 384", accent=True),
    ],
    "komoot": [
        _shape("circle", cx=256, cy=256, r=128),
        _path("M288 176 L224 224 L192 336 L288 288 Z", accent=True),
        _path("M224 224 L288 288 M256 128 V144 M384 256 H368 "
              "M256 384 V368 M128 256 H144"),
    ],
    "amazon-alexa": [
        _shape("ellipse", cx=256, cy=176, rx=104, ry=40),
        _path("M152 176 V336 C152 392 360 392 360 336 V176"),
        _path("M208 256 V304 M256 232 V328 M304 256 V304", accent=True),
    ],
    "ring": [
        _shape("rect", x=192, y=128, width=128, height=256, rx=48),
        _shape("circle", cx=256, cy=208, r=32, stroke="accent"),
        _shape("circle", cx=256, cy=312, r=24),
        _path("M144 200 V248 M368 200 V248", accent=True),
    ],
    "blink": [
        _path("M168 152 H304 L368 216 V296 H168 Z"),
        _shape("circle", cx=256, cy=224, r=40, stroke="accent"),
        _path("M232 296 V352 H328 M200 384 H360"),
        _path("M128 160 V192 M344 128 L360 144", accent=True),
    ],
    "google-home": [
        _path("M128 240 L256 128 L384 240 M160 224 V376 H352 V224"),
        _path("M208 264 Q256 216 304 264 M232 288 Q256 264 280 288", accent=True),
        _shape("circle", cx=256, cy=320, r=12, fill="accent", stroke="accent"),
    ],
    "zillow": [
        _path("M128 232 L256 128 L384 232 M160 208 V376 H352 V208"),
        _shape("circle", cx=248, cy=264, r=48, stroke="accent"),
        _path("M280 304 L320 344", accent=True),
    ],
    "chase": [
        _path("M176 128 H336 L384 176 V336 L336 384 H176 L128 336 V176 Z"),
        _shape("circle", cx=256, cy=256, r=64, stroke="accent"),
        _path("M256 192 V232 M320 256 H280 M256 320 V280 M192 256 H232", accent=True),
        _shape("circle", cx=256, cy=256, r=16),
    ],
    "capital-one": [
        _shape("rect", x=128, y=192, width=256, height=176, rx=24),
        _path("M152 240 H224 M160 320 H224"),
        _path("M216 168 Q288 120 360 144 M320 128 L360 144 L336 176", accent=True),
        _shape("rect", x=280, y=272, width=48, height=40, rx=8, stroke="accent"),
    ],
    "chime": [
        _path("M152 328 H360 L328 280 V224 C328 136 184 136 184 224 V280 Z"),
        _path("M240 136 V120 H272 V136 M224 360 Q256 392 288 360", accent=True),
        _path("M224 232 H288 M224 272 H288", accent=True),
    ],
    "ups": [
        _path("M256 120 L376 168 V272 C376 328 320 368 256 400 "
              "C192 368 136 328 136 272 V168 Z"),
        _path("M192 232 L256 200 L320 232 V304 L256 336 L192 304 Z "
              "M192 232 L256 264 L320 232 M256 264 V336", accent=True),
    ],
    "fedex": [
        _path("M136 176 H344 V208 M136 176 V368 H344 V320 M208 176 V232 H272 V176"),
        _path("M208 272 H392 L352 232 M392 272 L352 312", accent=True),
        _path("M168 336 H216"),
    ],
}


# Original 0.10 drawings share the accepted inset and stroke.
SEVENTH_APP_GLYPHS = {
    "chipotle": [
        _path("M208 192 C168 208 168 264 208 312 "
              "C248 360 312 384 368 360 C320 352 296 312 304 264 "
              "C312 216 280 184 240 192 Z"),
        _path("M240 192 C240 152 272 128 304 136 "
              "M208 232 Q200 288 264 328", accent=True),
    ],
    "taco-bell": [
        _path("M152 312 H360 L336 272 V224 "
              "C336 128 176 128 176 224 V272 Z"),
        _path("M256 128 V144 M224 352 Q256 384 288 352", accent=True),
    ],
    "wendys": [
        _path("M192 216 C144 192 120 224 136 256 "
              "C112 288 144 320 184 296 L192 264 Z "
              "M320 216 C368 192 392 224 376 256 "
              "C400 288 368 320 328 296 L320 264 Z"),
        _path("M192 216 C192 160 224 144 256 144 "
              "C288 144 320 160 320 216 V248 "
              "C320 288 288 320 256 320 C224 320 192 288 192 248 Z"),
        _path("M192 208 Q224 208 240 168 Q264 208 320 208 "
              "M232 264 Q256 280 280 264", accent=True),
        _path("M160 384 Q184 336 224 336 L256 360 L288 336 "
              "Q328 336 352 384"),
    ],
    "burger-king": [
        _path("M184 192 L168 128 L232 160 L256 120 "
              "L280 160 L344 128 L328 192 Z", accent=True),
        _path("M152 248 C168 200 344 200 360 248 Z"),
        _path("M160 288 H352", accent=True),
        _path("M152 320 H360 Q352 368 320 368 H192 "
              "Q160 368 152 320 Z"),
    ],
    "dunkin": [
        _shape("circle", cx=248, cy=256, r=120),
        _shape("circle", cx=248, cy=256, r=44, stroke="accent"),
        _path("M176 184 L192 200 M288 160 L280 184 "
              "M328 256 H304 M192 320 L208 304 "
              "M280 336 L288 352", accent=True),
    ],
    "chick-fil-a": [
        _path("M184 376 V312 C152 288 144 256 152 224 "
              "C160 192 192 176 224 176 H264 "
              "C312 176 336 208 336 248 L384 272 L336 296 "
              "V336 Q336 376 296 376 Z"),
        _path("M192 184 C160 160 184 128 208 152 "
              "C208 112 256 112 256 152 C280 128 312 160 288 184"),
        _shape("circle", cx=280, cy=232, r=12, fill="accent", stroke="accent"),
        _path("M200 312 Q232 280 272 304 Q288 328 272 344", accent=True),
    ],
    "dominos": [
        _path("M128 248 L264 112 L392 240 L256 376 Z"),
        _path("M196 180 L324 308", accent=True),
        _shape("circle", cx=292, cy=220, r=16, fill="accent", stroke="accent"),
        _shape("circle", cx=200, cy=260, r=16, fill="accent", stroke="accent"),
        _shape("circle", cx=248, cy=308, r=16, fill="accent", stroke="accent"),
    ],
    "pizza-hut": [
        _path("M128 216 L256 144 L384 216 M160 216 H352"),
        _path("M176 264 H336 L256 392 Z"),
        _path("M176 264 Q256 232 336 264", accent=True),
        _shape("circle", cx=256, cy=304, r=14, stroke="accent"),
    ],
    "subway": [
        _path("M144 304 L296 152 C328 120 360 120 376 144 "
              "C400 168 392 200 368 224 L216 376 "
              "C184 400 152 392 136 368 C120 344 120 328 144 304 Z"),
        _path("M160 352 L352 160", accent=True),
        _path("M168 280 L184 296 M224 224 L240 240 "
              "M280 168 L296 184"),
    ],
    "panera-bread": [
        _path("M128 320 V280 C128 224 184 200 256 200 "
              "C328 200 384 224 384 280 V320 "
              "Q384 368 336 368 H176 Q128 368 128 320 Z"),
        _path("M184 280 L216 248 M240 288 L272 248 "
              "M296 280 L328 248", accent=True),
        _path("M256 200 V120 M256 152 L232 136 M256 176 L280 152"),
    ],
    "kfc-us": [
        _path("M144 232 H368 L344 384 H168 Z"),
        _shape("rect", x=136, y=200, width=240, height=32, rx=8),
        _path("M208 264 C176 264 176 312 208 328 "
              "C232 344 256 328 256 304 L288 336 L312 312 "
              "L280 280 C256 248 232 248 208 264 Z", accent=True),
    ],
    "grubhub": [
        _path("M144 312 C144 192 336 192 336 312 Z M128 344 H352"),
        _shape("circle", cx=240, cy=184, r=16, stroke="accent"),
        _path("M240 200 V216", accent=True),
        _path("M376 192 V376 M352 192 V240 "
              "Q352 264 376 264 Q400 264 400 240 V192", accent=True),
    ],
}


# Original 0.11 travel drawings use different large silhouettes at the same inset.
EIGHTH_APP_GLYPHS = {
    "fly-delta": [
        _path("M128 288 L224 256 L208 160 L240 144 L280 240 "
              "L360 208 Q384 200 392 216 Q400 232 376 248 "
              "L296 280 L280 376 L248 384 V296 L176 320 Z"),
        _path("M128 376 H200", accent=True),
    ],
    "united-airlines": [
        _path("M152 328 C128 248 176 168 256 168 "
              "C336 168 384 248 360 328 M152 328 H360"),
        _path("M256 168 C208 216 208 280 224 328 "
              "M256 168 C304 216 304 280 288 328 M144 256 H368", accent=True),
        _path("M128 176 Q256 112 384 176", accent=True),
        _shape("circle", cx=128, cy=176, r=16, fill="accent", stroke="accent"),
        _shape("circle", cx=384, cy=176, r=16, fill="accent", stroke="accent"),
    ],
    "american-airlines": [
        _path("M136 160 H376 V224 Q344 240 376 256 V352 H136 "
              "V256 Q168 240 136 224 Z"),
        _path("M192 296 L304 208 M248 208 H304 V264", accent=True),
        _path("M336 176 V208 M336 288 V336"),
    ],
    "southwest-airlines": [
        _path("M184 224 C184 136 328 136 328 224 "
              "M256 112 V136 M144 168 L168 184 M368 168 L344 184", accent=True),
        _path("M128 288 H208 L184 248 H216 L256 288 H352 "
              "Q384 288 384 308 Q384 328 352 328 H256 "
              "L216 368 H184 L208 328 H160 Z"),
    ],
    "amtrak": [
        _path("M176 352 V184 Q176 128 232 128 H280 "
              "Q336 128 336 184 V352 L256 376 Z"),
        _shape("rect", x=200, y=176, width=112, height=88, rx=16, stroke="accent"),
        _shape("circle", cx=216, cy=312, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=296, cy=312, r=12, fill="accent", stroke="accent"),
        _path("M208 368 L184 400 M304 368 L328 400", accent=True),
    ],
    "transit": [
        _path("M144 144 V288 Q144 336 192 336 H368"),
        _path("M368 176 H256 Q208 176 208 224 V384", accent=True),
        _shape("circle", cx=208, cy=336, r=24, fill="text"),
        _shape("circle", cx=144, cy=144, r=16, fill="accent", stroke="accent"),
        _shape("circle", cx=368, cy=176, r=16, fill="accent", stroke="accent"),
    ],
    "moovit": [
        _shape("rect", x=128, y=160, width=256, height=208, rx=40),
        _shape("rect", x=160, y=192, width=192, height=80, rx=16, stroke="accent"),
        _path("M208 128 H304 M160 368 V392 M352 368 V392", accent=True),
        _shape("circle", cx=184, cy=320, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=328, cy=320, r=12, fill="accent", stroke="accent"),
    ],
    "citymapper": [
        _path("M144 128 V368 H384 M144 208 H304 V128 "
              "M224 208 V288 H384"),
        _path("M288 344 L344 288 L288 232", accent=True),
        _shape("circle", cx=144, cy=128, r=16, fill="accent", stroke="accent"),
    ],
    "tripit": [
        _path("M152 120 H296 L360 184 V392 H152 Z M296 120 V184 H360"),
        _path("M208 232 H296 V296 H208 V360 H296", accent=True),
        _shape("circle", cx=208, cy=232, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=296, cy=296, r=12, fill="accent", stroke="accent"),
        _shape("circle", cx=208, cy=360, r=12, fill="accent", stroke="accent"),
    ],
    "hopper": [
        _shape("rect", x=128, y=176, width=176, height=208, rx=32),
        _path("M176 176 V128 H256 V176 M176 216 V344 M256 216 V344"),
        _path("M352 192 V368 M320 336 L352 368 L384 336", accent=True),
    ],
}


# Original 0.12 finance drawings use varied large forms within the shared inset.
NINTH_APP_GLYPHS = {
    "bank-of-america": [
        _path("M128 312 L272 240 L384 288 L240 360 Z"),
        _path("M128 248 L272 176 L384 224 L352 240 "
              "M128 184 L272 112 L384 160 L352 176", accent=True),
        _path("M176 352 V384 H336 V336"),
    ],
    "wells-fargo": [
        _path("M136 208 L176 144 H328 L376 208 Z "
              "M152 208 V304 H360 V208"),
        _path("M216 208 V272 H296 V208 M128 304 H384", accent=True),
        _shape("circle", cx=192, cy=344, r=40),
        _shape("circle", cx=320, cy=344, r=40),
        _path("M192 328 V360 M176 344 H208 "
              "M320 328 V360 M304 344 H336", accent=True),
    ],
    "us-bank": [
        _path("M136 384 V248 C136 112 376 112 376 248 V384 Z"),
        _path("M176 344 V248 C176 144 336 144 336 248 V344 Z", accent=True),
        _shape("circle", cx=256, cy=264, r=40),
        _path("M256 224 V248 M296 264 H272 M256 304 V280 M216 264 H240"),
    ],
    "pnc": [
        _path("M144 376 V304 H208 V376 M224 376 V248 H288 V376 "
              "M304 376 V192 H368 V376 M128 376 H384"),
        _path("M144 240 L240 168 L336 136 M288 120 L336 136 L312 176", accent=True),
    ],
    "discover": [
        _path("M136 224 C136 112 376 112 376 224 M128 224 H384", accent=True),
        _path("M256 112 V128 M160 136 L176 152 M352 136 L336 152"),
        _shape("rect", x=136, y=264, width=240, height=120, rx=24),
        _path("M160 304 H352 M176 344 H232", accent=True),
    ],
    "amex": [
        _path("M192 128 H320 L368 176 V336 L320 384 H192 L144 336 V176 Z"),
        _path("M208 344 V312 L232 296 V272 "
              "C208 256 200 232 208 208 C216 176 264 160 296 184 "
              "C312 200 312 224 304 240 L328 264 H304 V288 H264 "
              "V320 L288 344 Z", accent=True),
    ],
    "fidelity-investments": [
        _path("M184 384 L216 216 H296 L328 384 Z "
              "M208 216 V168 H304 V216 M200 168 L256 120 L312 168 Z"),
        _path("M256 176 V208 M160 192 L128 176 "
              "M352 192 L384 176 M176 248 L128 248 "
              "M336 248 H384", accent=True),
        _path("M240 384 V328 H272 V384"),
    ],
    "schwab": [
        _path("M128 176 L256 120 L384 176 Z M144 208 H368 "
              "M144 352 H368 M128 384 H384"),
        _path("M176 208 V352 M256 208 V352 M336 208 V352", accent=True),
        _path("M160 256 H192 M240 296 H272 M320 256 H352"),
    ],
    "sofi": [
        _path("M184 184 L232 232 M328 184 L280 232 "
              "M184 328 L232 280 M328 328 L280 280"),
        _shape("circle", cx=256, cy=256, r=40, stroke="accent"),
        _shape("circle", cx=160, cy=160, r=32),
        _shape("circle", cx=352, cy=160, r=32, stroke="accent"),
        _shape("circle", cx=160, cy=352, r=32, stroke="accent"),
        _shape("circle", cx=352, cy=352, r=32),
    ],
    "robinhood": [
        _path("M152 360 C128 280 192 152 344 128 "
              "C384 240 328 328 216 344 Z"),
        _path("M128 392 L328 152 M216 344 L232 272 L160 280 "
              "M280 312 L288 208 L224 200", accent=True),
    ],
}


# Original weather objects keep broad silhouettes and the shared optical weight.
TENTH_APP_GLYPHS = {
    "accuweather": [
        _path("M168 280 C168 160 344 160 344 280 M120 312 H392"),
        _path("M256 128 V152 M144 184 L160 200 M368 184 L352 200", accent=True),
    ],
    "weather-channel": [
        _shape("rect", x=128, y=144, width=256, height=192, rx=24),
        _path("M256 168 V312 M256 336 V384 M208 384 H304"),
        _shape("circle", cx=192, cy=240, r=28, stroke="accent"),
        _path("M336 200 C280 200 280 280 336 280 C304 264 304 216 336 200 Z", filled=True),
    ],
    "weather-underground": [
        _path("M224 128 H288 Q288 176 256 176 Q224 176 224 128 Z"),
        _path("M368 208 V272 Q320 272 320 240 Q320 208 368 208 Z"),
        _path("M144 240 V304 Q192 304 192 272 Q192 240 144 240 Z"),
        _path("M256 176 V336 M256 224 L320 240 M256 224 L192 272 "
              "M256 336 L200 392 M256 336 L312 392", accent=True),
    ],
    "windy-com": [
        _path("M120 208 H320 C392 208 392 128 336 128 C304 128 288 152 304 176"),
        _path("M392 304 H192 C120 304 120 384 176 384 C208 384 224 360 208 336", accent=True),
    ],
    "myradar": [
        _path("M144 384 V144 C280 144 368 232 368 384 Z"),
        _path("M144 216 C240 216 296 288 296 384 "
              "M144 288 C192 288 224 328 224 384", accent=True),
        _shape("circle", cx=280, cy=224, r=16, fill="accent", stroke="accent"),
    ],
    "weatherbug": [
        _shape("ellipse", cx=256, cy=256, rx=64, ry=104),
        _path("M256 160 V352 M224 160 L200 120 M288 160 L312 120", accent=True),
        _path("M192 224 H144 L128 208 M320 224 H368 L384 208 "
              "M192 304 H144 L128 320 M320 304 H368 L384 320"),
    ],
    "one-weather": [
        _path("M224 312 V160 C224 120 288 120 288 160 V312 "
              "C344 360 304 400 256 400 C208 400 168 360 224 312 Z"),
        _path("M256 176 V344", accent=True),
        _shape("circle", cx=256, cy=352, r=20, fill="accent", stroke="accent"),
    ],
    "clime": [
        _path("M128 256 C144 128 368 128 384 256 "
              "Q320 224 256 256 Q192 224 128 256 Z"),
        _path("M256 160 V344 Q256 392 304 392 Q336 392 336 360", accent=True),
    ],
    "windfinder": [
        _path("M152 128 V392 M120 392 H216"),
        _path("M152 144 L384 184 V280 L152 256 Z", accent=True),
        _path("M232 160 V264 M312 176 V272"),
    ],
    "rainviewer": [
        _path("M256 128 C224 176 176 232 176 280 "
              "C176 384 336 384 336 280 C336 232 288 176 256 128 Z"),
        _path("M128 392 Q256 400 384 392", accent=True),
    ],
}


# Original exercise objects retain the broad forms and shared monochrome weight.
ELEVENTH_APP_GLYPHS = {
    "nike-run-club": [
        _path("M128 184 H184 L224 248 L296 280 H344 Q384 280 384 320 V352 H128 Z"),
        _path("M128 328 H384", accent=True),
        _path("M208 272 L232 248 M240 288 L264 264"),
    ],
    "adidas-running": [
        _shape("circle", cx=256, cy=280, r=112),
        _path("M224 120 H288 M256 120 V168"),
        _path("M256 280 L312 224 M256 280 V328", accent=True),
    ],
    "asics-runkeeper": [
        _path("M176 128 C128 128 128 200 152 248 L160 280 "
              "C144 320 152 368 184 368 C216 368 224 328 208 296 "
              "L200 264 C232 216 240 128 176 128 Z"),
        _path("M336 160 C272 160 280 248 312 296 L304 328 "
              "C288 360 296 400 328 400 C360 400 368 352 352 312 "
              "L360 280 C384 232 384 160 336 160 Z", accent=True),
    ],
    "map-my-run": [
        _shape("circle", cx=144, cy=352, r=24, fill="accent", stroke="accent"),
        _path("M168 352 H280 V176 H328"),
        _shape("rect", x=328, y=144, width=64, height=64, rx=8, stroke="accent"),
    ],
    "runna": [
        _path("M152 376 V176 H360 V376"),
        _path("M120 376 H192 M320 376 H392", accent=True),
    ],
    "trainingpeaks": [
        _path("M168 128 V384 M344 128 V384"),
        _path("M168 176 H344 M168 256 H344 M168 336 H344", accent=True),
    ],
    "zwift-companion": [
        _path("M184 288 H160 C112 288 112 176 160 176 H352 "
              "C400 176 400 288 352 288 H328"),
        _path("M256 176 V320", accent=True),
    ],
    "relive": [
        _shape("rect", x=136, y=240, width=240, height=144, rx=16),
        _path("M136 240 L120 184 L360 128 L376 184 Z"),
        _path("M192 168 L208 224 M280 148 L296 204", accent=True),
    ],
}


# Broad study objects keep their silhouette without publisher marks or small text.
TWELFTH_APP_GLYPHS = {
    "google-classroom": [
        _shape("rect", x=120, y=136, width=272, height=208, rx=16),
        _path("M184 200 H328 M152 344 H360 M184 344 V384 M328 344 V384", accent=True),
    ],
    "khan-academy": [
        _path("M136 128 V384 H376 V128 M136 192 H376 M136 256 H376 M136 320 H376"),
        _shape("rect", x=176, y=168, width=48, height=48, rx=16, fill="accent", stroke="accent"),
        _shape("rect", x=288, y=232, width=48, height=48, rx=16, fill="accent", stroke="accent"),
        _shape("rect", x=208, y=296, width=48, height=48, rx=16, fill="accent", stroke="accent"),
    ],
    "coursera": [
        _path("M120 208 L256 136 L392 208 L256 280 Z"),
        _path("M176 240 V304 Q256 368 336 304 V240 M392 208 V312", accent=True),
    ],
    "udemy": [
        _path("M144 160 L368 208 L344 272 L120 224 Z"),
        _path("M248 256 V376 M184 376 H312", accent=True),
    ],
    "edx": [
        _shape("circle", cx=256, cy=160, r=32),
        _path("M240 192 L152 384 M272 192 L360 384 M200 280 H312", accent=True),
    ],
    "quizlet": [
        _path("M136 288 H120 V144 H344 V168"),
        _shape("rect", x=168, y=208, width=224, height=160, rx=16),
        _path("M224 288 H336", accent=True),
    ],
    "photomath": [
        _path("M128 192 V128 H192 M320 128 H384 V192 M384 320 V384 H320 M192 384 H128 V320"),
        _path("M192 256 H320", accent=True),
        _shape("circle", cx=256, cy=192, r=16, fill="accent", stroke="accent"),
        _shape("circle", cx=256, cy=320, r=16, fill="accent", stroke="accent"),
    ],
    "brainly": [
        _path("M144 248 H136 Q120 248 120 232 V144 Q120 128 136 128 H312 Q328 128 328 144 V176"),
        _path("M200 208 H368 Q392 208 392 232 V328 Q392 352 368 352 H280 L216 392 V352 H200 Q176 352 176 328 V232 Q176 208 200 208 Z"),
        _path("M232 280 H336", accent=True),
    ],
}


# Broad reading objects retain visible gaps at the gallery's small icon sizes.
THIRTEENTH_APP_GLYPHS = {
    "google-play-books": [
        _shape("rect", x=128, y=144, width=56, height=216, rx=8),
        _shape("rect", x=216, y=128, width=56, height=232, rx=8),
        _path("M304 176 L352 160 L400 344 L352 360 Z"),
        _path("M112 392 H400", accent=True),
    ],
    "libby": [
        _shape("rect", x=120, y=144, width=272, height=208, rx=24),
        _shape("circle", cx=184, cy=216, r=24, stroke="accent"),
        _path("M248 200 H344 M248 248 H312 M160 304 H352", accent=True),
        _path("M168 352 V384 H344 V352"),
    ],
    "kobo-books": [
        _shape("rect", x=160, y=120, width=192, height=272, rx=24),
        _path("M208 184 H304 M208 232 H304 M208 280 H272", accent=True),
        _shape("circle", cx=256, cy=352, r=8, fill="accent", stroke="accent"),
    ],
    "goodreads": [
        _path("M176 128 H368 V328 H176 Q144 328 144 360 V160 Q144 128 176 128 Z"),
        _path("M176 328 Q144 328 144 360 Q144 384 176 384 H368 V328 M192 360 H336", accent=True),
        _path("M256 168 L280 216 L328 224 L292 260 L304 312 L256 288 L208 312 L220 260 L184 224 L232 216 Z"),
    ],
    "wattpad": [
        _path("M216 128 H376 V384 H136 V272 M184 328 H312 M232 280 H312", accent=True),
        _path("M136 264 L152 152 L216 128 L248 192 Z"),
        _path("M136 264 L200 200"),
    ],
    "webtoon": [
        _shape("rect", x=168, y=120, width=176, height=272, rx=16),
        _path("M168 208 H344 M168 296 H344", accent=True),
        _path("M216 152 H296 V176 H248 L216 192 Z"),
        _path("M200 360 L240 320 L280 360 L312 336", accent=True),
    ],
    "readera": [
        _path("M120 152 Q184 128 256 176 Q328 128 392 152 V344 Q328 320 256 368 Q184 320 120 344 Z"),
        _path("M256 176 V256 M256 304 V368"),
        _shape("rect", x=136, y=256, width=240, height=48, rx=8, stroke="accent"),
    ],
    "moon-reader": [
        _path("M280 120 C208 120 176 168 192 224 C208 280 280 296 328 248 C248 264 216 176 280 120 Z"),
        _path("M152 328 H360 V392 H152 Q120 392 120 360 Q120 328 152 328 Z"),
        _path("M168 360 H328", accent=True),
    ],
}




# Phone-service drawings keep simple silhouettes distinct at small gallery sizes.
FOURTEENTH_APP_GLYPHS = {
    "ace-hardware": [
        _path("M128 144 L176 128 L208 160 L192 208 L160 224 L128 192 Z"),
        _path("M192 208 L360 376 L392 344 L224 176"),
        _shape("circle", cx=352, cy=344, r=12),
    ],
    "ai-dungeon": [
        _path("M128 168 Q192 144 256 184 Q320 144 384 168 V360 Q320 336 256 376 Q192 336 128 360 Z"),
        _path("M224 344 V264 Q256 216 288 264 V344 M256 184 V216"),
        _path("M352 120 V152 M336 136 H368", accent=True),
    ],
    "gaming-hub": [
        _path("M160 160 Q256 112 352 160 M160 352 Q256 400 352 352", accent=True),
        _path("M184 208 H328 Q352 208 368 256 L384 304 Q384 336 352 328 L304 296 H208 L160 328 Q128 336 128 304 L144 256 Q160 208 184 208 Z"),
        _path("M184 240 V280 M164 260 H204"),
        _shape("circle", cx=304, cy=252, r=8, fill="text"),
        _shape("circle", cx=336, cy=276, r=8, fill="text"),
    ],
    "kroger": [
        _path("M128 224 H384 L352 376 H160 Z M192 224 L224 136 M320 224 L288 136"),
        _shape("circle", cx=224, cy=288, r=20),
        _shape("circle", cx=288, cy=312, r=20, stroke="accent"),
    ],
    "affirm": [
        _shape("rect", x=136, y=168, width=240, height=208, rx=24),
        _path("M136 224 H376 M192 136 V192 M320 136 V192"),
        _path("M184 312 L224 344 L328 256", accent=True),
    ],
    "usaa": [
        _path("M256 128 L376 168 V256 Q376 336 256 392 Q136 336 136 256 V168 Z"),
        _path("M184 224 L256 184 L328 224 M192 224 V304 M256 224 V320 M320 224 V304 M184 336 H328", accent=True),
    ],
    "proton-authenticator": [
        _path("M256 120 L368 168 V256 Q368 336 256 392 Q144 336 144 256 V168 Z"),
        _shape("circle", cx=256, cy=248, r=64),
        _path("M256 208 V248 L288 264", accent=True),
    ],
    "wikipedia": [
        _shape("circle", cx=256, cy=232, r=104),
        _shape("ellipse", cx=256, cy=232, rx=40, ry=104),
        _path("M152 232 H360 M168 184 H344 M168 280 H344", accent=True),
        _path("M160 376 H352 M208 336 V376 M304 336 V376"),
    ],
    "xbox": [
        _path("M192 152 H320 Q352 152 368 216 L392 328 Q392 368 352 352 L304 304 H208 L160 352 Q120 368 120 328 L144 216 Q160 152 192 152 Z"),
        _path("M184 208 V272 M152 240 H216"),
        _shape("circle", cx=312, cy=208, r=8, fill="text"),
        _shape("circle", cx=344, cy=240, r=8, fill="text"),
        _shape("circle", cx=312, cy=272, r=8, fill="text"),
        _shape("circle", cx=280, cy=240, r=8, fill="text"),
    ],
    "shop": [
        _path("M152 208 H360 L376 376 H136 Z M208 208 V176 Q208 128 256 128 Q304 128 304 176 V208"),
        _shape("rect", x=224, y=256, width=64, height=64, rx=12, stroke="accent"),
    ],
    "fandom": [
        _path("M128 184 Q184 160 240 200 Q296 160 352 184 V376 Q296 352 240 392 Q184 352 128 376 Z M240 200 V392"),
        _path("M264 128 H384 V224 H344 L312 256 V224 H264 Z", accent=True),
    ],
    "shonen-jump": [
        _shape("rect", x=144, y=120, width=224, height=272, rx=16),
        _path("M144 224 H368 M144 304 H368 M272 120 V224 M224 304 V392"),
        _path("M184 272 L328 248 M184 192 L232 152 M272 352 L328 328", accent=True),
    ],
    "smart-switch": [
        _shape("rect", x=120, y=136, width=104, height=240, rx=20),
        _shape("rect", x=288, y=136, width=104, height=240, rx=20),
        _path("M192 216 H320 L296 192 M320 296 H192 L216 320", accent=True),
    ],
    "steam-chat": [
        _path("M160 144 H352 Q392 144 392 184 V304 Q392 344 352 344 H248 L176 392 V344 H160 Q120 344 120 304 V184 Q120 144 160 144 Z"),
        _shape("circle", cx=208, cy=248, r=24),
        _shape("circle", cx=304, cy=248, r=24),
        _path("M232 248 H280", accent=True),
    ],
    "sonic": [
        _path("M128 192 L160 136 H352 L384 192 Z M152 192 V224 M360 192 V224"),
        _path("M208 248 H312 L296 384 H224 Z M272 248 V208 L304 184", accent=True),
    ],
    "samsung-global-goals": [
        _path("M240 128 Q144 144 128 240 H208 Q216 216 240 208 Z"),
        _path("M272 128 Q368 144 384 240 H304 Q296 216 272 208 Z"),
        _path("M128 272 Q144 368 240 384 V304 Q216 296 208 272 Z"),
        _path("M272 384 Q368 368 384 272 H304 Q296 296 272 304 Z"),
    ],
    "theme-park": [
        _shape("rect", x=128, y=128, width=256, height=256, rx=40),
        _shape("circle", cx=208, cy=208, r=24),
        _shape("circle", cx=304, cy=208, r=24),
        _shape("circle", cx=208, cy=304, r=24, stroke="accent"),
        _shape("circle", cx=304, cy=304, r=24, fill="text"),
    ],
    "zillow-rentals": [
        _path("M128 232 L256 128 L384 232 M160 208 V360 H240"),
        _shape("circle", cx=304, cy=264, r=32),
        _path("M304 296 V392 M304 352 H344 M304 384 H328", accent=True),
    ],
    "samsung-find": [
        _path("M136 216 V136 H216 M296 136 H376 V216 M376 296 V376 H296 M216 376 H136 V296"),
        _shape("circle", cx=256, cy=256, r=56, stroke="accent"),
        _shape("circle", cx=256, cy=256, r=8, fill="text"),
    ],
    "dollar-general": [
        _path("M128 224 L152 144 H336 L360 224 M152 224 V376 H336 V296 M184 376 V272 H248 V376"),
        _path("M288 232 H352 L392 272 L352 312 L288 248 Z", accent=True),
        _shape("circle", cx=320, cy=248, r=8, fill="text"),
    ],
    "sound-connect": [
        _path("M144 288 V240 Q144 128 256 128 Q368 128 368 240 V288"),
        _shape("rect", x=128, y=248, width=48, height=104, rx=16),
        _shape("rect", x=336, y=248, width=48, height=104, rx=16),
        _shape("circle", cx=256, cy=304, r=24, stroke="accent"),
        _path("M208 304 H232 M280 304 H304 M256 328 V376", accent=True),
    ],
    "samsung-pass": [
        _shape("rect", x=136, y=144, width=240, height=224, rx=32),
        _shape("circle", cx=232, cy=224, r=32),
        _path("M216 256 L200 312 H264 L248 256 M296 304 L320 328 L360 280", accent=True),
    ],
    "va": [
        _path("M128 184 V152 H232 L264 184 H384 V376 H128 Z"),
        _path("M256 216 L280 264 L336 272 L296 312 L304 360 L256 336 L208 360 L216 312 L176 272 L232 264 Z", accent=True),
    ],
    "battle-net": [
        _shape("circle", cx=256, cy=152, r=24),
        _shape("circle", cx=160, cy=336, r=24),
        _shape("circle", cx=352, cy=336, r=24),
        _path("M280 152 Q384 176 376 288 M328 360 Q256 400 192 368 M136 288 Q128 208 208 168", accent=True),
    ],
    "coinbase": [
        _shape("circle", cx=216, cy=224, r=88),
        _shape("circle", cx=312, cy=312, r=72),
        _path("M184 224 H248 M216 192 V256 M280 312 H344", accent=True),
    ],
    "credit-one": [
        _shape("rect", x=128, y=160, width=256, height=192, rx=24),
        _path("M128 216 H384 M176 296 H216 M288 264 L312 248 V312", accent=True),
    ],
    "samsung-members": [
        _shape("circle", cx=216, cy=216, r=40),
        _shape("circle", cx=328, cy=232, r=32),
        _path("M136 360 V336 Q136 288 216 288 Q296 288 296 336 V360 M320 304 Q376 304 376 352 V360"),
        _path("M128 144 Q256 112 384 144", accent=True),
    ],
    "proton-vpn": [
        _path("M128 376 L232 144 L280 248 M232 376 L320 208 L392 376 Z"),
        _shape("circle", cx=184, cy=328, r=16, stroke="accent"),
        _path("M184 344 V376 M144 376 H224", accent=True),
    ],
    "t-life": [
        _shape("rect", x=168, y=120, width=176, height=272, rx=32),
        _path("M216 168 H296 M232 256 H280 M256 232 V280", accent=True),
        _path("M224 344 H288"),
    ],
    "my-spectrum": [
        _path("M144 224 Q256 128 368 224 M184 264 Q256 200 328 264 M224 304 Q256 280 288 304", accent=True),
        _shape("rect", x=136, y=344, width=240, height=48, rx=16),
        _path("M184 368 H208"),
    ],
    "g2a": [
        _path("M128 184 H288 V328 H128 V280 Q160 256 128 232 Z"),
        _path("M224 152 H384 V352 H288", accent=True),
        _path("M192 216 V280 M160 248 H224"),
    ],
    "samsung-tv-plus": [
        _shape("rect", x=128, y=144, width=256, height=192, rx=24),
        _path("M224 336 V384 M288 336 V384 M192 384 H320"),
        _path("M224 240 H288 M256 208 V272", accent=True),
    ],
    "ap-news": [
        _path("M128 144 H336 V352 Q336 384 304 384 H160 Q128 384 128 352 Z M336 208 H384 V352 Q384 384 352 384 H304"),
        _shape("rect", x=168, y=184, width=64, height=64, rx=8),
        _path("M264 184 H296 M264 224 H296 M168 296 H296 M168 336 H264", accent=True),
    ],
    "link-to-windows": [
        _shape("rect", x=120, y=152, width=192, height=144, rx=16),
        _path("M184 296 V344 M152 344 H216"),
        _shape("rect", x=280, y=224, width=112, height=168, rx=16),
        _path("M208 224 H256 L240 208 M256 224 L240 240", accent=True),
    ],
    "tips": [
        _path("M200 296 Q160 264 160 216 Q160 128 256 128 Q352 128 352 216 Q352 264 312 296 L296 336 H216 Z"),
        _path("M224 368 H288 M240 392 H272 M256 192 V240 M256 272 V280", accent=True),
    ],
    "proton-pass": [
        _path("M256 120 L392 256 L256 392 L120 256 Z"),
        _shape("circle", cx=232, cy=232, r=40),
        _path("M264 264 L328 328 M296 296 L320 272 M320 320 L344 296", accent=True),
    ],
    "shop-samsung": [
        _path("M144 208 H368 L384 384 H128 Z M208 208 V176 Q208 128 256 128 Q304 128 304 176 V208"),
        _shape("rect", x=224, y=248, width=64, height=96, rx=12, stroke="accent"),
        _path("M248 320 H264", accent=True),
    ],
    "wallpaper-engine": [
        _shape("rect", x=128, y=144, width=240, height=208, rx=24),
        _shape("circle", cx=200, cy=208, r=24),
        _path("M128 312 L200 256 L256 296 L304 248 L336 272"),
        _shape("circle", cx=336, cy=336, r=40, stroke="accent"),
        _path("M336 280 V296 M336 376 V392 M280 336 H296 M376 336 H392", accent=True),
    ],
    "asus-router": [
        _shape("rect", x=136, y=272, width=240, height=96, rx=24),
        _path("M168 272 V136 M344 272 V136 M184 368 V392 M328 368 V392"),
        _shape("circle", cx=256, cy=320, r=16, stroke="accent"),
        _path("M216 176 Q256 144 296 176", accent=True),
    ],
    "mochi-health": [
        _path("M128 264 Q128 184 208 184 Q264 184 288 240 Q312 296 368 296 Q368 376 288 376 Q232 376 208 320 Q184 264 128 264 Z"),
        _path("M256 176 Q288 120 360 136 Q344 192 288 192 M256 208 L312 160", accent=True),
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
    elif version == "0.7.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG)
    elif version == "0.8.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG)
    elif version == "0.9.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG)
    elif version == "0.10.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG)
    elif version == "0.11.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG)
    elif version == "0.12.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG)
    elif version == "0.13.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG, *TENTH_APP_CATALOG)
    elif version == "0.14.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG, *TENTH_APP_CATALOG, *ELEVENTH_APP_CATALOG)
    elif version == "0.15.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG, *TENTH_APP_CATALOG, *ELEVENTH_APP_CATALOG, *TWELFTH_APP_CATALOG)
    elif version == "0.16.0":
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG, *TENTH_APP_CATALOG, *ELEVENTH_APP_CATALOG, *TWELFTH_APP_CATALOG, *THIRTEENTH_APP_CATALOG)
    else:
        apps = (*APP_CATALOG, *NEW_APP_CATALOG, *THIRD_APP_CATALOG, *FOURTH_APP_CATALOG, *FIFTH_APP_CATALOG, *SIXTH_APP_CATALOG, *SEVENTH_APP_CATALOG, *EIGHTH_APP_CATALOG, *NINTH_APP_CATALOG, *TENTH_APP_CATALOG, *ELEVENTH_APP_CATALOG, *TWELFTH_APP_CATALOG, *THIRTEENTH_APP_CATALOG, *FOURTEENTH_APP_CATALOG)
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
        play_identity = (url.scheme == "https" and url.netloc == "play.google.com"
                         and url.path == "/store/apps/details"
                         and parse_qs(url.query) == {"id": [package]} and not url.fragment)
        # Only these inspected Samsung records extend the current catalog's store contract.
        galaxy_identity = (version == "0.17.0" and package in {
            "com.samsung.android.game.gamehome", "com.samsung.android.themedesigner",
            "com.samsung.android.samsungpass", "com.samsung.android.app.tips",
        } and app["store_url"] == f"https://galaxystore.samsung.com/detail/{package}")
        if app.get("kind") != "app" or not (play_identity or galaxy_identity):
            raise ValueError("Named-app store URL must identify its exact official package")
        seen.add(identifier)
        packages.add(package)
        catalog.append(dict(app))
    drawings = set(APP_GLYPHS)
    if version in ("0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(NEW_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(NEW_APP_GLYPHS)
    if version in ("0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(THIRD_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(THIRD_APP_GLYPHS)
    if version in ("0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(FOURTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(FOURTH_APP_GLYPHS)
    if version in ("0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(FIFTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(FIFTH_APP_GLYPHS)
    if version in ("0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(SIXTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(SIXTH_APP_GLYPHS)
    if version in ("0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(SEVENTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(SEVENTH_APP_GLYPHS)
    if version in ("0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(EIGHTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(EIGHTH_APP_GLYPHS)
    if version in ("0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(NINTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(NINTH_APP_GLYPHS)
    if version in ("0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(TENTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(TENTH_APP_GLYPHS)
    if version in ("0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(ELEVENTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(ELEVENTH_APP_GLYPHS)
    if version in ("0.15.0", "0.16.0", "0.17.0"):
        if drawings & set(TWELFTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(TWELFTH_APP_GLYPHS)
    if version in ("0.16.0", "0.17.0"):
        if drawings & set(THIRTEENTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(THIRTEENTH_APP_GLYPHS)
    if version == "0.17.0":
        if drawings & set(FOURTEENTH_APP_GLYPHS):
            raise ValueError("New named-app drawings replace an accepted ID")
        drawings |= set(FOURTEENTH_APP_GLYPHS)
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
    return ROOT / ("tokens-monochrome.json" if version in ("0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0") else "tokens.json")


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
                THIRD_APP_GLYPHS if function in THIRD_APP_GLYPHS else
                FOURTH_APP_GLYPHS if function in FOURTH_APP_GLYPHS else
                FIFTH_APP_GLYPHS if function in FIFTH_APP_GLYPHS else
                SIXTH_APP_GLYPHS if function in SIXTH_APP_GLYPHS else
                SEVENTH_APP_GLYPHS if function in SEVENTH_APP_GLYPHS else
                EIGHTH_APP_GLYPHS if function in EIGHTH_APP_GLYPHS else
                NINTH_APP_GLYPHS if function in NINTH_APP_GLYPHS else
                TENTH_APP_GLYPHS if function in TENTH_APP_GLYPHS else
                ELEVENTH_APP_GLYPHS if function in ELEVENTH_APP_GLYPHS else
                TWELFTH_APP_GLYPHS if function in TWELFTH_APP_GLYPHS else
                THIRTEENTH_APP_GLYPHS if function in THIRTEENTH_APP_GLYPHS else FOURTEENTH_APP_GLYPHS)
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
    if version in ("0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
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
    if version in ("0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
        if version == "0.3.0":
            date, scope = CATALOG_DATE, CATALOG_SCOPE
        elif version == "0.4.0":
            date, scope = NEW_CATALOG_DATE, NEW_CATALOG_SCOPE
        elif version in ("0.5.0", "0.6.0"):
            date, scope = THIRD_CATALOG_DATE, THIRD_CATALOG_SCOPE
        elif version == "0.7.0":
            date, scope = FOURTH_CATALOG_DATE, FOURTH_CATALOG_SCOPE
        elif version == "0.8.0":
            date, scope = FIFTH_CATALOG_DATE, FIFTH_CATALOG_SCOPE
        elif version == "0.9.0":
            date, scope = SIXTH_CATALOG_DATE, SIXTH_CATALOG_SCOPE
        elif version == "0.10.0":
            date, scope = SEVENTH_CATALOG_DATE, SEVENTH_CATALOG_SCOPE
        elif version == "0.11.0":
            date, scope = EIGHTH_CATALOG_DATE, EIGHTH_CATALOG_SCOPE
        elif version == "0.12.0":
            date, scope = NINTH_CATALOG_DATE, NINTH_CATALOG_SCOPE
        elif version == "0.13.0":
            date, scope = TENTH_CATALOG_DATE, TENTH_CATALOG_SCOPE
        elif version == "0.14.0":
            date, scope = ELEVENTH_CATALOG_DATE, ELEVENTH_CATALOG_SCOPE
        elif version == "0.15.0":
            date, scope = TWELFTH_CATALOG_DATE, TWELFTH_CATALOG_SCOPE
        elif version == "0.16.0":
            date, scope = THIRTEENTH_CATALOG_DATE, THIRTEENTH_CATALOG_SCOPE
        else:
            date, scope = FOURTEENTH_CATALOG_DATE, FOURTEENTH_CATALOG_SCOPE
        manifest.update(catalog=catalog, catalog_date=date, catalog_scope=scope,
                        scope="Original themed interpretations for named apps and general functions; "
                              "app names identify intended assignments, not publisher endorsement or installation")
    if version in ("0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
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
