"""Derive the bounded clock bitmap resource from an explicit licensed Inter file."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = "-0123456789:"
SIZE = 108
FACE = "Clair Obscur Clock"
FONT_FILE = "clair-obscur-clock-108.fnt"
ATLAS_FILE = "clair-obscur-clock-108.png"
SOURCE_SHA256 = "288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f"
LICENSE_SHA256 = "262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a"
RENDERER = {"pillow": "12.3.0", "freetype": "2.14.3", "fonttools": "4.63.0", "png_zlib": "1.3.1.zlib-ng"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def safe_path(path: Path) -> Path:
    """Inspect existing path components before resolving or reading through them."""
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if os.path.lexists(item) and linked(item):
            raise ValueError("Font paths must not contain links or reparse points")
    return path


def read_input(path: Path, limit: int) -> bytes:
    path = safe_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("Expected a bounded regular font or license input")
    return path.read_bytes()


def render(font_path: Path, license_path: Path) -> dict[str, bytes]:
    font_bytes = read_input(font_path, 2 * 1024 * 1024)
    license_bytes = read_input(license_path, 64 * 1024)
    if digest(font_bytes) != SOURCE_SHA256 or digest(license_bytes) != LICENSE_SHA256:
        raise ValueError("Expected the identified Inter Bold source and its complete OFL license")
    # These tools are required only for explicit regeneration, not ordinary builds.
    import PIL
    from PIL import Image, ImageDraw, ImageFont, features
    import fontTools
    from fontTools.ttLib import TTFont

    renderer = {"pillow": PIL.__version__, "freetype": features.version_module("freetype2"),
                "fonttools": fontTools.__version__, "png_zlib": features.version_codec("zlib")}
    if renderer != RENDERER:
        raise ValueError("Canonical regeneration requires the recorded renderer versions")
    with TTFont(io.BytesIO(font_bytes)) as original:
        family = original["name"].getDebugName(1)
        style = original["name"].getDebugName(2)
        version = original["name"].getDebugName(5)
        copyright_text = original["name"].getDebugName(0)
    if (family, style, version) != ("Inter", "Bold", "Version 4.001;git-9221beed3"):
        raise ValueError("Unexpected embedded source-font identity")
    font = ImageFont.truetype(io.BytesIO(font_bytes), SIZE, layout_engine=ImageFont.Layout.BASIC)
    ascent, descent = font.getmetrics()
    glyphs = []
    for character in CHARACTERS:
        left, top, right, bottom = font.getbbox(character, anchor="ls")
        mask = Image.new("L", (right - left, bottom - top))
        ImageDraw.Draw(mask).text((-left, -top), character, font=font, fill=255, anchor="ls")
        bounds = mask.getbbox()
        if bounds is None:
            raise ValueError("A clock glyph has no ink")
        advance = font.getlength(character)
        if advance != int(advance):
            raise ValueError("Expected integer unshaped glyph advances")
        glyphs.append({"id": ord(character), "mask": mask.crop(bounds),
                       "xoffset": left + bounds[0], "yoffset": ascent + top + bounds[1],
                       "xadvance": int(advance)})
    # A single compact row needs no packing heuristic or glyph-order dependency.
    width = sum(glyph["mask"].width + 2 for glyph in glyphs)
    height = max(glyph["mask"].height for glyph in glyphs) + 2
    atlas = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    rows = []
    x = 1
    for glyph in glyphs:
        mask = glyph["mask"]
        rgba = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        rgba.putalpha(mask)
        atlas.paste(rgba, (x, 1))
        rows.append(f'char id={glyph["id"]} x={x} y=1 width={mask.width} height={mask.height} '
                    f'xoffset={glyph["xoffset"]} yoffset={glyph["yoffset"]} '
                    f'xadvance={glyph["xadvance"]} page=0 chnl=8')
        x += mask.width + 2
    image = io.BytesIO()
    atlas.save(image, format="PNG", optimize=False, compress_level=9)
    descriptor = (f'info face="{FACE}" size={SIZE} bold=1 italic=0 charset="" unicode=1 '
                  'stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=0,0 outline=0\n'
                  f'common lineHeight={ascent + descent} base={ascent} scaleW={width} scaleH={height} '
                  'pages=1 packed=0 alphaChnl=0 redChnl=4 greenChnl=4 blueChnl=4\n'
                  f'page id=0 file="{ATLAS_FILE}"\nchars count={len(glyphs)}\n' +
                  "\n".join(rows) + "\nkernings count=0\n").encode()
    resources = (f'<fonts>\n  <font id="InterClock" filename="{FONT_FILE}" '
                 f'antialias="true" filter="{CHARACTERS}" />\n</fonts>\n').encode()
    files = {FONT_FILE: descriptor, ATLAS_FILE: image.getvalue(), "fonts.xml": resources,
             "LICENSE.txt": license_bytes}
    provenance = {
        "schema_version": 1, "derivative_name": FACE,
        "source": {"release": "Inter v4.1", "file": "Inter-Bold.ttf", "sha256": SOURCE_SHA256,
                   "family": family, "style": style, "embedded_version": version,
                   "copyright": copyright_text,
                   "release_url": "https://github.com/rsms/inter/releases/tag/v4.1"},
        "license": {"id": "OFL-1.1", "file": "LICENSE.txt", "sha256": LICENSE_SHA256,
                    "url": "https://github.com/rsms/inter/blob/v4.1/LICENSE.txt"},
        "generation": {"producer": "garmin/generate_clock_font.py",
                       "producer_sha256": digest(Path(__file__).read_bytes()), "renderer": renderer,
                       "pixels_per_em": SIZE, "characters": CHARACTERS,
                       "layout": "Per-glyph proportional advances, no kerning or OpenType feature shaping",
                       "source_outline_scaling": "Uniform scale only; no condensed outlines or stretched digits",
                       "line_height": ascent + descent, "baseline": ascent,
                       "atlas": {"width": width, "height": height, "mode": "RGBA",
                                 "rgb": "white", "glyph_channel": "alpha"}},
        "files": {name: {"bytes": len(data), "sha256": digest(data)} for name, data in sorted(files.items())},
        "references": ["https://developer.garmin.com/connect-iq/articles/core-topics/Resources.html#fonts",
                       "https://www.angelcode.com/products/bmfont/doc/file_format.html"],
        "scope": "Derived bitmap subset for the active digital clock. No original TTF is distributed. "
                 "Host metrics and raster identity do not establish Garmin rendering, runtime RAM, "
                 "font-scale behavior, persistence, always-on performance or physical-watch acceptance.",
    }
    files["provenance.json"] = (json.dumps(provenance, indent=2, ensure_ascii=False) + "\n").encode()
    return files


def output_path(path: Path) -> Path:
    path = safe_path(path)
    if path == Path(path.anchor) or path == ROOT or path.is_relative_to(ROOT / "dist"):
        raise ValueError("Refusing filesystem root, repository root or managed desktop output")
    return path


def publish_new(path: Path, files: dict[str, bytes]) -> None:
    path = output_path(path)
    if os.path.lexists(path):
        raise ValueError("A new output directory is required; existing output is preserved")
    # Reserve exclusively. A later failure retains this attempt for inspection.
    path.mkdir()
    for name, data in sorted(files.items()):
        with (path / name).open("xb") as stream:
            stream.write(data)


def verify_existing(path: Path, files: dict[str, bytes]) -> None:
    path = output_path(path)
    if not path.is_dir():
        raise ValueError("Expected an existing resource directory")
    children = list(path.iterdir())
    if {child.name for child in children} != set(files):
        raise ValueError("Font output differs; missing and extra files are preserved")
    actual = {}
    for child in children:
        if linked(child) or not child.is_file():
            raise ValueError("Font output differs: linked, nested or nonregular entry")
        if child.stat().st_size != len(files[child.name]):
            raise ValueError("Font output differs; changed files are preserved")
        actual[child.name] = child.read_bytes()
    if actual != files:
        raise ValueError("Font output differs; changed, missing and extra files are preserved")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="Explicit Inter v4.1 static Inter-Bold.ttf")
    parser.add_argument("--license", type=Path, required=True, help="Explicit complete Inter v4.1 LICENSE.txt")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output-new", type=Path)
    mode.add_argument("--check", type=Path)
    args = parser.parse_args()
    try:
        files = render(args.font, args.license)
        if args.output_new is not None:
            publish_new(args.output_new, files)
        else:
            verify_existing(args.check, files)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(1, f"Clock font generation failed: {error}\n")
    print("Clock bitmap subset generated or checked; Garmin runtime acceptance remains separate")


if __name__ == "__main__":
    main()
