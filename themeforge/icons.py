"""Generate original functional SVG icons into a separate, new output folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

from .legal import license_text
from .tokens import load, validate


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
SIZE = 512
STROKE = 12
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


def _validated(document: dict) -> None:
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    try:
        validate(document)
    except (TypeError, AttributeError) as error:
        raise ValueError("Malformed token document") from error


def _render_icon(function: str, appearance: str, document: dict, grant: str) -> bytes:
    palette = document["themes"][appearance]
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "width": str(SIZE), "height": str(SIZE),
        "viewBox": "0 0 512 512", "role": "img", "aria-label": function,
    })
    svg.append(ET.Comment("\n" + grant + "\n"))
    ET.SubElement(svg, "rect", {"x": "32", "y": "32", "width": "448", "height": "448",
                               "rx": "104", "fill": palette["panel"]})
    group = ET.SubElement(svg, "g", {"fill": "none", "stroke": palette["text"],
        "stroke-width": str(STROKE), "stroke-linecap": "round", "stroke-linejoin": "round"})
    for tag, attributes in GLYPHS[function]:
        ET.SubElement(group, tag, {
            key: palette[value] if value in ("accent", "text") else value
            for key, value in attributes.items()
        })
    ET.indent(svg, space="  ")
    return (ET.tostring(svg, encoding="unicode") + "\n").encode("utf-8")


def render_icons(document: dict) -> dict[str, bytes]:
    """Return 48 SVG masters and their deterministic identity manifest."""
    _validated(document)
    grant = license_text()
    if "--" in grant:
        raise ValueError("The license cannot be embedded safely in an XML comment")
    files = {}
    records = []
    for appearance in ("Clair", "Obscur"):
        for function in FUNCTIONS:
            name = f"{appearance}/{function}.svg"
            payload = _render_icon(function, appearance, document, grant)
            files[name] = payload
            records.append({"appearance": appearance, "function": function, "path": name,
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {
        "schema_version": 1, "generator": "themeforge.icons", "version": VERSION,
        "token_schema": document["schema_version"], "token_version": document["version"],
        "size": [SIZE, SIZE], "stroke_width": STROKE,
        "tile": {"x": 32, "y": 32, "width": 448, "height": 448, "radius": 104},
        "glyph_centerline_bounds": [112, 112, 400, 400],
        "palette_roles": {"tile": "panel", "glyph": "text", "emphasis": "accent"},
        "functions": list(FUNCTIONS), "files": records,
        "scope": "Original functional glyphs; no brand logos, font assets or phone installation",
    }
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


def build_icons(document: dict, output: Path, *, check: bool = False) -> dict:
    """Create a new tree or compare an existing one, never replace user output."""
    files = render_icons(document)
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
    parser.add_argument("--tokens", type=Path, default=ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, required=True, help="A new folder outside managed dist")
    parser.add_argument("--check", action="store_true", help="Compare all generated bytes without writing")
    options = parser.parse_args(argv)
    try:
        manifest = build_icons(load(options.tokens), options.output, check=options.check)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.exit(1, f"Icon generation: {error}\n")
    print(f'{"Verified" if options.check else "Generated"} {len(manifest["files"])} original SVG icons')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
