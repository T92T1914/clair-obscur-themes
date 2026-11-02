"""Regenerate the two original static Hybrid dial resources with Pillow 12.3.0.

The normal Monkey C build consumes committed PNGs and does not import Pillow.
This backplate contains no hands, live values, branding, font or photograph.
Run with --check to compare bytes, or --write to replace verified owned output.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

import PIL
from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "watchface/source/FaceModel.mc"
TOKENS = ROOT.parent / "tokens-monochrome.json"
PALETTE = ROOT / "watchface/source/GeneratedPalette.mc"
DESTINATION = ROOT / "watchface/resources/dial"
SCALE = 4
EXPECTED = {
    "DISPLAY_SIZE": 454, "DIAL_CENTER": 227,
    "HYBRID_MARKER_CENTER": 155, "HYBRID_CIRCLE_RADIUS": 14,
    "HYBRID_CIRCLE_INNER": 11, "HYBRID_BATON_INNER": 137,
    "HYBRID_BATON_OUTER": 166, "HYBRID_BATON_HALF": 8,
    "HYBRID_TRIANGLE_INNER": 119, "HYBRID_TRIANGLE_OUTER": 164,
    "HYBRID_TRIANGLE_HALF": 17, "HYBRID_TICK_OUTER": 174,
    "HYBRID_TICK_INNER": 169, "HYBRID_BEZEL_OUTER": 226,
    "HYBRID_BEZEL_INNER": 177, "HYBRID_BEZEL_RADIUS": 203,
}

# Original closed contours in a 16 by 28 grid. The counters in 0 and 4
# are explicit negative shapes. These are solid forms, not stroked paths.
NUMERALS = {
    0: {
        "outer": [(4, 0), (12, 0), (16, 4), (16, 24), (12, 28), (4, 28), (0, 24), (0, 4)],
        "holes": [[(5, 4), (11, 4), (12, 5), (12, 23), (11, 24), (5, 24), (4, 23), (4, 5)]],
    },
    1: {
        "outer": [(3, 4), (8, 0), (12, 0), (12, 24), (16, 24), (16, 28), (4, 28), (4, 24), (8, 24), (8, 6), (3, 9)],
        "holes": [],
    },
    2: {
        "outer": [(0, 4), (4, 0), (12, 0), (16, 4), (16, 10), (12, 16), (4, 24), (16, 24), (16, 28), (0, 28), (0, 23), (9, 14), (12, 9), (12, 5), (11, 4), (5, 4), (4, 5), (4, 8), (0, 8)],
        "holes": [],
    },
    3: {
        "outer": [(0, 0), (12, 0), (16, 4), (16, 10), (13, 14), (16, 18), (16, 24), (12, 28), (0, 28), (0, 24), (11, 24), (12, 23), (12, 19), (10, 16), (5, 16), (5, 12), (10, 12), (12, 9), (12, 5), (11, 4), (0, 4)],
        "holes": [],
    },
    4: {
        "outer": [(8, 0), (13, 0), (13, 17), (16, 17), (16, 21), (13, 21), (13, 28), (9, 28), (9, 21), (0, 21), (0, 16)],
        "holes": [[(4, 17), (9, 17), (9, 7)]],
    },
    5: {
        "outer": [(0, 0), (16, 0), (16, 4), (4, 4), (4, 11), (12, 11), (16, 15), (16, 24), (12, 28), (0, 28), (0, 24), (11, 24), (12, 23), (12, 16), (11, 15), (0, 15)],
        "holes": [],
    },
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def geometry() -> tuple[dict[str, int], bytes]:
    raw = MODEL.read_bytes()
    source = raw.decode("utf-8")
    values = {}
    for name, expected in EXPECTED.items():
        found = re.findall(r"\bconst\s+" + re.escape(name) + r"\s*=\s*(\d+)\s*;", source)
        if len(found) != 1 or int(found[0]) != expected:
            raise ValueError(f"Review changed native geometry before regeneration: {name}")
        values[name] = int(found[0])
    return values, raw


def scaled(value: float) -> int:
    return round(value * SCALE)


def radial(g: dict[str, int], turn: float, radius: float, tangent: float = 0) -> tuple[float, float]:
    angle = turn * math.tau
    center = g["DIAL_CENTER"]
    return (center + math.sin(angle) * radius + math.cos(angle) * tangent,
            center - math.cos(angle) * radius + math.sin(angle) * tangent)


def polygon_mask(size: int, points: list[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon([(scaled(x), scaled(y)) for x, y in points], fill=255)
    return mask


def shifted(mask: Image.Image, dx: float, dy: float) -> Image.Image:
    # Paste with clipping, not ImageChops.offset's wraparound.
    result = Image.new("L", mask.size, 0)
    result.paste(mask, (scaled(dx), scaled(dy)))
    return result


def metal_shape(image: Image.Image, outer: Image.Image, inner: Image.Image,
                lume: int) -> None:
    # A narrow darker bottom/right relief and bright top/left chamfer.
    image.paste(30, mask=shifted(outer, .75, .75))
    image.paste(142, mask=outer)
    highlight = ImageChops.subtract(outer, shifted(outer, 1, 1))
    shadow = ImageChops.subtract(outer, shifted(outer, -1, -1))
    image.paste(235, mask=highlight)
    image.paste(75, mask=shadow)
    image.paste(lume, mask=inner)


def render(appearance: str, g: dict[str, int], canvas: int) -> bytes:
    dimension = g["DISPLAY_SIZE"]
    size = dimension * SCALE
    image = Image.new("L", (size, size), 0)
    drawing = ImageDraw.Draw(image)
    center = g["DIAL_CENTER"]
    clair = appearance == "clair"
    dial = canvas
    ceramic = 13
    lume = 250 if clair else 246

    def ellipse(radius: float, color: int) -> None:
        drawing.ellipse((scaled(center - radius), scaled(center - radius),
                         scaled(center + radius), scaled(center + radius)), fill=color)

    def arc(radius: float, start: float, end: float, color: int, width: float = 1) -> None:
        drawing.arc((scaled(center - radius), scaled(center - radius),
                     scaled(center + radius), scaled(center + radius)),
                    start, end, fill=color, width=max(1, scaled(width)))

    # The resource stops at the circular display. No simulated case or bracelet.
    ellipse(g["HYBRID_BEZEL_OUTER"], 69)
    ellipse(g["HYBRID_BEZEL_OUTER"] - 1, 154)
    arc(g["HYBRID_BEZEL_OUTER"] - .5, 155, 290, 238, .75)
    arc(g["HYBRID_BEZEL_OUTER"] - .5, -15, 110, 70, .75)
    ellipse(223, ceramic)
    arc(222, 155, 290, 47, .75)
    arc(222, -15, 110, 5, .75)
    ellipse(184, 97)
    arc(183.5, 155, 290, 207, 1)
    arc(183.5, -15, 110, 53, 1)
    ellipse(181.5, 41)
    ellipse(179.5, 122)
    arc(179, 155, 290, 214, .75)
    arc(179, -15, 110, 57, .75)
    ellipse(g["HYBRID_BEZEL_INNER"], dial)

    def block(turn: float, inner: float, outer: float, half: float) -> list[tuple[float, float]]:
        return [radial(g, turn, inner, -half), radial(g, turn, outer, -half),
                radial(g, turn, outer, half), radial(g, turn, inner, half)]

    # Bezel scale, separate from the smaller native minute track.
    for index in range(1, 15):
        if index % 5:
            image.paste(233, mask=polygon_mask(size, block(index / 60, 211, 220, 1)))
    for index in range(5, 60, 10):
        image.paste(239, mask=polygon_mask(size, block(index / 60, 198, 218, 2.5)))
    for value in range(10, 60, 10):
        turn = value / 60
        glyphs = Image.new("L", (size, size), 0)
        gd = ImageDraw.Draw(glyphs)
        for digit, offset in ((value // 10, -17.5), (0, 1.5)):
            glyph = NUMERALS[digit]
            for contour, color in [(glyph["outer"], 255), *[(hole, 0) for hole in glyph["holes"]]]:
                points = [radial(g, turn, g["HYBRID_BEZEL_RADIUS"] + 14 - y, x + offset) for x, y in contour]
                gd.polygon([(scaled(x), scaled(y)) for x, y in points], fill=color)
        image.paste(64, mask=shifted(glyphs, .5, .5))
        image.paste(239, mask=glyphs)

    pip_outer = polygon_mask(size, [(210, 8), (244, 8), (227, 39)])
    pip_inner = polygon_mask(size, [(214, 10), (240, 10), (227, 34)])
    metal_shape(image, pip_outer, pip_inner, ceramic)
    drawing = ImageDraw.Draw(image)
    drawing.ellipse((scaled(221), scaled(12), scaled(233), scaled(24)), fill=150)
    drawing.ellipse((scaled(222), scaled(13), scaled(232), scaled(23)), fill=248)

    # All marker positions and sizes come from the actual native model.
    track = 91 if clair else 164
    for index in range(60):
        turn = index / 60
        ends = [radial(g, turn, g["HYBRID_TICK_INNER"]), radial(g, turn, g["HYBRID_TICK_OUTER"])]
        drawing.line([(scaled(x), scaled(y)) for x, y in ends], fill=track, width=SCALE)
    for index in (1, 2, 4, 5, 7, 8, 10, 11):
        x, y = radial(g, index / 12, g["HYBRID_MARKER_CENTER"])
        outer, inner = Image.new("L", (size, size), 0), Image.new("L", (size, size), 0)
        for mask, radius in ((outer, g["HYBRID_CIRCLE_RADIUS"]), (inner, g["HYBRID_CIRCLE_INNER"])):
            ImageDraw.Draw(mask).ellipse((scaled(x - radius), scaled(y - radius), scaled(x + radius), scaled(y + radius)), fill=255)
        metal_shape(image, outer, inner, lume)
    for index in (6, 9):
        turn = index / 12
        outer = polygon_mask(size, block(turn, g["HYBRID_BATON_INNER"], g["HYBRID_BATON_OUTER"], g["HYBRID_BATON_HALF"]))
        inner = polygon_mask(size, block(turn, g["HYBRID_BATON_INNER"] + 2.5, g["HYBRID_BATON_OUTER"] - 2.5, g["HYBRID_BATON_HALF"] - 2.5))
        metal_shape(image, outer, inner, lume)
    outer = polygon_mask(size, [radial(g, 0, g["HYBRID_TRIANGLE_OUTER"], -g["HYBRID_TRIANGLE_HALF"]),
                                radial(g, 0, g["HYBRID_TRIANGLE_OUTER"], g["HYBRID_TRIANGLE_HALF"]),
                                radial(g, 0, g["HYBRID_TRIANGLE_INNER"])])
    inner = polygon_mask(size, [radial(g, 0, g["HYBRID_TRIANGLE_OUTER"] - 2.5, -g["HYBRID_TRIANGLE_HALF"] + 3),
                                radial(g, 0, g["HYBRID_TRIANGLE_OUTER"] - 2.5, g["HYBRID_TRIANGLE_HALF"] - 3),
                                radial(g, 0, g["HYBRID_TRIANGLE_INNER"] + 5)])
    metal_shape(image, outer, inner, lume)

    # RGB preserves neutral channel values directly, without a color profile.
    final = image.resize((dimension, dimension), Image.Resampling.LANCZOS).convert("RGB")
    out = io.BytesIO()
    final.save(out, "PNG", optimize=False, compress_level=9)
    return out.getvalue()


def outputs() -> dict[str, bytes]:
    if PIL.__version__ != "12.3.0":
        raise RuntimeError("Dial regeneration requires the qualified Pillow 12.3.0")
    g, model_raw = geometry()
    tokens_raw = TOKENS.read_bytes()
    tokens = json.loads(tokens_raw)
    palette = PALETTE.read_text(encoding="utf-8")
    canvases = {}
    for appearance in ("Obscur", "Clair"):
        color = tokens["themes"][appearance]["canvas"]
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color) or not color[1:3] == color[3:5] == color[5:7]:
            raise ValueError("Static neutral dial requires a reviewed neutral canvas")
        found = re.findall(r"\bconst\s+" + appearance.upper() + r"_CANVAS\s*=\s*0x([0-9a-fA-F]{6})\s*;", palette)
        if len(found) != 1 or int(found[0], 16) != int(color[1:], 16):
            raise ValueError("Native clearing canvas does not match the semantic tokens")
        canvases[appearance.lower()] = int(color[1:3], 16)
    result = {f"{appearance}.png": render(appearance, g, canvases[appearance]) for appearance in ("obscur", "clair")}
    provenance = {
        "schema_version": 1,
        "kind": "clair-obscur-original-static-dial",
        "scope": "Production Monkey C bitmap backplate only. No hands, live data, branding, font or photograph. Not native rendering or physical appearance acceptance.",
        "generator": "garmin/generate_dial_art.py",
        "generator_sha256": sha(Path(__file__).read_bytes()),
        "model": "garmin/watchface/source/FaceModel.mc",
        "model_sha256": sha(model_raw),
        "geometry": g,
        "canvas_source": "tokens-monochrome.json",
        "canvas_source_sha256": sha(tokens_raw),
        "canvas_values": canvases,
        "native_canvas_check": "GeneratedPalette.mc CLAIR_CANVAS and OBSCUR_CANVAS agree with token values",
        "source_art": "Original closed polygons and native-model marker geometry; no external artwork or fonts.",
        "numeral_contours_sha256": sha(json.dumps(NUMERALS, sort_keys=True, separators=(",", ":")).encode()),
        "renderer": {"library": "Pillow", "version": PIL.__version__, "supersampling": SCALE,
                     "downsample": "LANCZOS", "output": "454x454 RGB PNG, neutral channels", "png_compress_level": 9},
        "lighting": "Narrow upper-left metal highlights and lower-right shadows; uniform black ceramic with no noise or broad glare.",
        "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in result.items()},
    }
    result["provenance.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode()
    return result


def check_owned_destination() -> None:
    for path in (DESTINATION, *DESTINATION.parents):
        if path.exists() and (path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 1024):
            raise ValueError(f"Refusing redirected output path: {path}")
    if not DESTINATION.exists():
        return
    present = {p.name for p in DESTINATION.iterdir()}
    if not present:
        return
    if present != {"obscur.png", "clair.png", "provenance.json"}:
        raise ValueError("Preserving incomplete or foreign dial output")
    for path in DESTINATION.iterdir():
        if not path.is_file() or path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 1024:
            raise ValueError(f"Preserving nonregular dial output: {path.name}")
    old = json.loads((DESTINATION / "provenance.json").read_bytes())
    if old.get("kind") != "clair-obscur-original-static-dial" or set(old.get("files", {})) != {"obscur.png", "clair.png"}:
        raise ValueError("Preserving unrecognized dial provenance")
    for name, record in old["files"].items():
        data = (DESTINATION / name).read_bytes()
        if len(data) != record["bytes"] or sha(data) != record["sha256"]:
            raise ValueError(f"Preserving edited dial resource: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args()
    check_owned_destination()
    generated = outputs()
    if args.check:
        changed = [name for name, data in generated.items() if not (DESTINATION / name).is_file() or (DESTINATION / name).read_bytes() != data]
        if changed:
            print("Dial resource comparison differs: " + ", ".join(changed), file=sys.stderr)
            return 1
        print("Static dial resources and provenance match deterministic regeneration.")
        return 0
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, data in generated.items():
        (DESTINATION / name).write_bytes(data)
    print("Wrote two original static dial PNGs and exact provenance. Native appearance remains unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
