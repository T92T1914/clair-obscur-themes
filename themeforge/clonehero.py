"""Generate paired Clone Hero color profiles and highways outside desktop dist.

The profiles start from a recorded base of the game's color keys and change only
what the skin is about, so every profile carries the same 183 keys in the same
order as a complete professional profile. The two video highways are pinned
source assets. Everything else is built here with the standard library only.
"""

from __future__ import annotations

import argparse
import colorsys
import io
import json
import math
from pathlib import Path
import re
import struct
import zipfile
import zlib

from .build import _checksum_bytes, _digest, _inventory, _json_bytes, _safe_destination
from .legal import license_text
from .terminal import ANSI_EXTRAS
from .tokens import load, validate

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
ARCHIVE = f"Clair-Obscur-Clone-Hero-{VERSION}.zip"
BASE_PATH = Path(__file__).with_name("clonehero_base.json")
ASSET_DIR = Path(__file__).with_name("clonehero_assets")
APPEARANCES = ("Clair", "Obscur")
KEY_COUNT = 183
WIDTH, HEIGHT = 512, 1024
FPS, FRAMES = 30, 60  # the video highways are two second loops
STAR_POWER_RED = "#FF0000"
# The two highways are encoded VP8 loops that came from the installed skin. They
# stay byte for byte as built, so the hash is checked every time they are read.
HIGHWAY_SHA256 = {
    "Clair": "f3fdafce55e4d18bc707fac71f2f188b2102645dcd6d22749fe1a6995ba05ede",
    "Obscur": "f86caa353032f1456d3cdbb249dec4d9151bb9dc4a195d557667d1428a0cf439",
}
# The background videos are too large for the repository. Their identities are
# recorded in the manifest and in docs/clone-hero.md only.
BACKGROUND_SHA256 = {
    "Clair Obscur 4K.webm": "6574b87ec9dc70bf173c1f231ba0dd5807746a7d487ff7a86667cf233756a986",
    "Clair Obscur 1080p.webm": "91aa67bce6561a7e9455b2735e5eb3d77ebc318cbe10b6a6845ca6bac868fcd1",
}
HIGHWAY_CONFIG = (
    "[highway]\r\ncolor = #FFFFFF\r\ntransparency = 1\r\nplayback_speed = 1\r\n"
    "scale_full_highway_length = 1\r\nmirrored_repeat = 0\r\n"
    "scale_playback_with_note_speed = 0\r\nscrolling_enabled = 0\r\n"
).encode("ascii")
PROFILES = {
    name: (name, f"{name} Color") for name in APPEARANCES
}
LANES = ("green", "red", "yellow", "blue", "orange")
PADS = ("green", "blue", "yellow", "red")


def _validated(document: dict) -> None:
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    try:
        validate(document)
    except (TypeError, AttributeError) as error:
        raise ValueError("Malformed token document") from error


def base_profile() -> dict[str, dict[str, str]]:
    """The recorded base: section, key and value, in the order the game writes them."""
    base = json.loads(BASE_PATH.read_text(encoding="utf-8"))
    if sum(len(keys) for keys in base.values()) != KEY_COUNT:
        raise ValueError("The recorded base must hold exactly 183 keys")
    return base


def key_order(base: dict[str, dict[str, str]] | None = None) -> list[str]:
    base = base or base_profile()
    return [f"{section}.{key}" for section, keys in base.items() for key in keys]


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def hsv(hue_degrees: float, saturation: float = 1.0, value: float = 1.0) -> str:
    return rgb_hex([c * 255 for c in colorsys.hsv_to_rgb((hue_degrees % 360) / 360, saturation, value)])


def hue(color: str) -> float:
    r, g, b = (c / 255 for c in hex_rgb(color))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def scale(color: str, factor: float) -> str:
    return rgb_hex([v * factor for v in hex_rgb(color)])


def blend(a: str, b: str, amount: float) -> str:
    """Plain sRGB blend, the arithmetic the reference profile uses."""
    return rgb_hex([x + (y - x) * amount for x, y in zip(hex_rgb(a), hex_rgb(b))])


def _star_power(values, sp, light_sp, hud, dark_kick=None):
    other, guitar, drums, six = values["other"], values["guitar"], values["drums"], values["sixfret"]
    other["combo_sp_active"] = hud
    other["striker_hit_flame_sp_active"] = "#FFFFFF"
    other["striker_hit_flame"] = hud
    other["sp_bar_arrow"] = blend(hud, "#FFFFFF", 0.5)
    other["sp_bar_elec"] = "#FFFFFF"
    other["sp_bar_color"] = hud
    other["sp_act_animation"] = scale(hud, 0.92)
    other["sp_act_flash"] = scale(hud, 0.78)
    other["general_sp"] = sp
    for key in ("sustain_sp_active", "sustain_sp_phrase_active", "sustain_sp_phrase",
                "note_sp_active", "note_sp_phrase_active", "note_sp_phrase",
                "note_anim_sp_active", "note_anim_sp_phrase"):
        guitar[key] = sp
    for key in ("tom_sp_active", "tom_sp_phrase_active", "tom_sp_phrase",
                "cym_sp_active", "cym_sp_phrase_active", "cym_sp_phrase"):
        drums[key] = sp
    for key in ("tom_anim_sp_active", "tom_anim_sp_phrase_active", "tom_anim_sp_phrase",
                "cym_anim_sp_active", "cym_anim_sp_phrase_active", "cym_anim_sp_phrase"):
        drums[key] = light_sp
    for key in ("note_kick_sp_active", "note_kick_sp_phrase_active", "note_kick_sp_phrase"):
        drums[key] = sp if dark_kick is not None and sp.upper() == dark_kick.upper() else scale(sp, 0.7)
    for key in ("note_overlay_kick_sp_active", "note_overlay_kick_sp_phrase"):
        drums[key] = scale(sp, 0.85)
    for key in ("note_anim_kick_sp_active", "note_anim_kick_sp_phrase_active", "note_anim_kick_sp_phrase"):
        drums[key] = sp
    for key in ("sf_sustain_sp_active", "sf_sustain_sp_phrase_active", "sf_sustain_sp_phrase",
                "sf_note_sp_active", "sf_note_sp_phrase_active", "sf_note_sp_phrase"):
        six[key] = sp


def _steel_combo(values, theme):
    """The reference turned the fourth multiplier steel blue. The accent is steel blue."""
    h = hue(theme["accent"])
    values["other"]["combo_four"] = hsv(h, 0.50, 0.62)
    values["other"]["combo_four_glow"] = hsv(h, 0.30, 1.0)


def _guitar_lanes(values, lane, light, cover, sustain, anim, open_note, open_anim, open_light, base):
    guitar = values["guitar"]
    for name, color in lane.items():
        guitar[f"note_{name}"] = color
        guitar[f"striker_head_light_{name}"] = light[name]
        guitar[f"striker_head_cover_{name}"] = cover[name]
        guitar[f"striker_cover_{name}"] = cover[name]
        guitar[f"sustain_{name}"] = sustain[name]
        guitar[f"note_anim_{name}"] = anim[name]
        guitar[f"striker_base_{name}"] = base
    guitar["note_open"] = open_note
    guitar["sustain_open"] = open_note
    guitar["note_anim_open"] = open_anim
    guitar["striker_head_light_open"] = open_light


def _drum_pads(values, pad, cym, anim, light, cover, base, kick, kick_anim, kick_light):
    drums = values["drums"]
    for name in PADS:
        drums[f"tom_{name}"] = pad[name]
        drums[f"cym_{name}"] = cym[name]
        drums[f"tom_anim_{name}"] = anim[name]
        drums[f"cym_anim_{name}"] = anim[name]
        for prefix in ("", "drums_"):
            drums[f"{prefix}striker_base_{name}"] = base
            drums[f"{prefix}striker_head_light_{name}"] = light[name]
            drums[f"{prefix}striker_head_cover_{name}"] = cover[name]
            drums[f"{prefix}striker_cover_{name}"] = cover[name]
    for prefix in ("", "drums_"):
        drums[f"{prefix}striker_head_light_kick"] = kick_light
    drums["note_kick"] = kick
    drums["note_anim_kick"] = kick_anim


def mono_profile(name: str, theme: dict) -> tuple[dict, dict]:
    """Black and white notes. Star power is vivid red."""
    dark = name == "Obscur"
    values = base_profile()
    ink = "#FFFFFF" if dark else theme["text"]
    gray = theme["muted"]
    cover = scale(ink, 0.706) if dark else theme["muted"]
    anim = "#FFFFFF" if dark else theme["muted"]
    _guitar_lanes(values, {k: ink for k in LANES}, {k: ink for k in LANES}, {k: cover for k in LANES},
                  {k: ink for k in LANES}, {k: anim for k in LANES}, gray,
                  "#FFFFFF" if dark else theme["muted"], blend(gray, "#FFFFFF", 0.5), ink)
    _drum_pads(values, {k: ink for k in PADS}, {k: ink for k in PADS}, {k: anim for k in PADS},
               {k: ink for k in PADS}, {k: cover for k in PADS}, ink, gray,
               blend(gray, "#FFFFFF", 0.4), blend(gray, "#FFFFFF", 0.5))
    _star_power(values, STAR_POWER_RED, blend(STAR_POWER_RED, "#FFFFFF", 0.32), STAR_POWER_RED)
    _steel_combo(values, theme)
    six = values["sixfret"]
    if not dark:  # white six fret notes would vanish on the light highway
        for key in list(six):
            if "_sp" in key:
                continue
            if "black" in key:
                six[key] = theme["text"]
            elif "white" in key or "open" in key or key.startswith(("sf_sustain_", "sf_striker_background")):
                six[key] = theme["border"]
    # HOPO and tap markers stay neutral so red keeps meaning star power.
    marker = theme["border"] if dark else theme["muted"]
    six["sf_note_hopo"] = marker
    for key in list(six):
        if key.startswith("sf_note_tap"):
            six[key] = marker
    return values, {"notes": ink, "open": gray, "star_power": STAR_POWER_RED}


def lane_colors(theme: dict) -> dict[str, str]:
    """Full strength lane colors at the hues of the theme roles, with yellow added."""
    return {"green": hsv(hue(theme["success"])), "red": hsv(hue(theme["error"])), "yellow": hsv(60.0),
            "blue": hsv(hue(theme["accent"])), "orange": hsv(hue(theme["warning"]))}


def color_profile(name: str, theme: dict) -> tuple[dict, dict]:
    """Full strength lanes. Star power stays the theme ink, because red would match the red lane."""
    dark = name == "Obscur"
    values = base_profile()
    lane = lane_colors(theme)
    purple = hsv(hue(ANSI_EXTRAS[name]["purple"]))
    ink = "#FFFFFF" if dark else theme["text"]
    _guitar_lanes(values, lane, dict(lane), {k: scale(c, 0.706) for k, c in lane.items()}, dict(lane),
                  {k: blend(c, "#FFFFFF", 0.45) for k, c in lane.items()}, purple, "#FFFFFF",
                  blend(purple, "#FFFFFF", 0.5), ink)
    pads = {k: lane[k] for k in PADS}
    _drum_pads(values, pads, {k: blend(c, "#FFFFFF", 0.1) for k, c in pads.items()},
               {k: blend(c, "#FFFFFF", 0.45) for k, c in pads.items()}, dict(pads), dict(pads),
               ink, lane["orange"], blend(lane["orange"], "#FFFFFF", 0.4), blend(lane["orange"], "#FFFFFF", 0.5))
    _star_power(values, ink, theme["muted"] if not dark else "#FFFFFF", "#FFFFFF", theme["text"])
    _steel_combo(values, theme)
    return values, {"notes": lane, "open": purple, "star_power": ink}


def profile_bytes(values: dict) -> bytes:
    """The game's INI layout: sections, `key = VALUE` lines, CRLF line ends."""
    lines = []
    for section, keys in values.items():
        lines.append(f"[{section}]")
        lines += [f"{key} = {value.upper()}" for key, value in keys.items()]
        lines.append("")
    return ("\n".join(lines) + "\n").replace("\n", "\r\n").encode("utf-8")


def frame_rows(name: str, theme: dict, frame: int = 0) -> list[bytes]:
    """One frame of the highway loop, row by row. Frame 0 is the still highway.

    Rails are 20 solid pixels on each side with a glow that falls to nothing about
    40 pixels in. Along a rail, star power red and the theme ink trade places and
    travel one full period over FRAMES frames, so frame FRAMES repeats frame 0.
    """
    dark = name == "Obscur"
    canvas = hex_rgb(theme["canvas"])
    accent = hex_rgb(STAR_POWER_RED)
    ink = hex_rgb("#FFFFFF" if dark else theme["text"])
    half = WIDTH // 2
    alpha = []
    for x in range(half):
        edge = float(x)
        alpha.append(1.0 if edge < 20 else 0.35 * math.exp(-(edge - 20.0) / 17.0))
    rows = []
    for y in range(HEIGHT):
        k = 0.5 - 0.5 * math.cos(2 * math.pi * (y / HEIGHT - frame / FRAMES))
        rail = [a + (b - a) * k for a, b in zip(accent, ink)]
        left = bytearray()
        for a in alpha:
            for channel in range(3):
                v = canvas[channel] * (1 - a) + rail[channel] * a
                left.append(int(min(max(v + 0.5, 0.0), 255.0)))
        pixels = bytes(left)
        mirrored = b"".join(pixels[i:i + 3] for i in range(len(pixels) - 3, -1, -3))
        rows.append(pixels + mirrored)
    return rows


def png_bytes(rows: list[bytes], width: int, height: int) -> bytes:
    """A deterministic 8 bit RGB PNG with no metadata chunks."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _archive_bytes(files: dict[str, bytes]) -> bytes:
    """A deterministic stored ZIP. The game's own folder names hold spaces, which the shared writer refuses."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*(?:/[A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*)*", name):
                raise ValueError("Artifact path is invalid")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, files[name])
    return buffer.getvalue()


def highway_video(name: str) -> bytes:
    data = (ASSET_DIR / name / "highway.webm").read_bytes()
    if _digest(data) != HIGHWAY_SHA256[name]:
        raise ValueError(f"{name}: pinned highway video differs from its recorded hash")
    return data


def render_clonehero(document: dict) -> dict[str, bytes]:
    """Return the skin tree, its local archive and exact independent identities."""
    _validated(document)
    payload: dict[str, bytes] = {"LICENSE.txt": license_text().encode("utf-8")}
    appearances = {}
    for name in APPEARANCES:
        theme = document["themes"][name]
        appearances[name] = {}
        for profile, build in zip(PROFILES[name], (mono_profile, color_profile)):
            values, summary = build(name, theme)
            payload[f"Colors/{profile}.ini"] = profile_bytes(values)
            appearances[name][profile] = summary
        payload[f"Video Highways/{name}/highway.webm"] = highway_video(name)
        payload[f"Video Highways/{name}/config.ini"] = HIGHWAY_CONFIG
        payload[f"Highways/{name} Still.png"] = png_bytes(frame_rows(name, theme), WIDTH, HEIGHT)
    files = {**payload, ARCHIVE: _archive_bytes(payload)}
    manifest = {
        "schema_version": 1, "generator": "themeforge.clonehero", "version": VERSION,
        "token_schema": document["schema_version"], "token_version": document["version"],
        "tokens_sha256": _digest(_json_bytes(document)), "archive": ARCHIVE,
        "base_sha256": _digest(BASE_PATH.read_bytes()), "key_count": KEY_COUNT,
        "method": "A recorded base of the game's color keys, recolored the way a complete professional profile is",
        "appearances": appearances,
        "pinned_highway_videos": {name: HIGHWAY_SHA256[name] for name in APPEARANCES},
        "background_videos": {"in_package": False, "sha256": BACKGROUND_SHA256},
        "native_acceptance": "unverified",
        "scope": "Color profiles, video highways and still highways; the background videos are separate and not included",
        "files": [{"path": name, "bytes": len(data), "sha256": _digest(data)}
                  for name, data in sorted(files.items())],
    }
    files["manifest.json"] = _json_bytes(manifest)
    files["SHA256SUMS"] = _checksum_bytes(files)
    return files


def _safe_output(path: Path) -> Path:
    path = _safe_destination(path)
    if path == ROOT / "dist" or ROOT / "dist" in path.parents:
        raise ValueError("Clone Hero output must stay outside managed desktop dist")
    return path


def build_clonehero(document: dict, output: Path, *, check: bool = False) -> dict:
    """Create a new output tree or compare existing bytes without repair."""
    files = render_clonehero(document)
    output = _safe_output(Path(output))
    if check:
        if not output.is_dir():
            raise ValueError("Clone Hero check requires an existing generated output directory")
        actual, directories = _inventory(output)
        expected = {output / parent for name in files for parent in map(Path, [name]) for parent in list(parent.parents)[:-1]}
        if actual != files or {Path(d) for d in directories} != expected:
            raise ValueError("Clone Hero output differs: changed, missing or extra entries")
    else:
        if output.exists():
            raise ValueError("Clone Hero generation requires a new output directory; existing entries are preserved")
        output.parent.mkdir(parents=True, exist_ok=True)
        output = _safe_output(output)
        output.mkdir(exist_ok=False)
        for name, data in files.items():
            target = _safe_destination(output / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
    return json.loads(files["manifest.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, required=True, help="A new directory outside managed desktop dist")
    parser.add_argument("--check", action="store_true", help="Compare exact generated output without writing")
    args = parser.parse_args(argv)
    try:
        manifest = build_clonehero(load(args.tokens), args.output, check=args.check)
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        parser.exit(1, f"Clone Hero generation: {error}\n")
    print(f'{"Verified" if args.check else "Generated"} Clone Hero {manifest["version"]} candidate; native play unverified')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
