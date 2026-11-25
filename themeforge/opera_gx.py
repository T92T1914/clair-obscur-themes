"""Paired color hints for Opera GX, with an original local package icon."""

from __future__ import annotations

from collections.abc import Mapping
import colorsys
import re
import struct
import zlib


def _rgb(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError("GX color must be a six-digit hex value")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def hsl_hint(value: str) -> dict[str, int]:
    """Quantize sRGB to integer HSL hints; the host derives its own palette."""
    hue, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in _rgb(value)))
    return {"h": round(hue * 360) % 360, "s": round(saturation * 100), "l": round(lightness * 100)}


# A measured candidate for a later GX version. Version 0.3.0 does not use it.
# GX derives its light surfaces from the light base hint and sets their
# lightness itself. Clair's own hint, 48 26 96, makes those surfaces read beige.
# In Opera GX 139.0.6053.63 for Linux this hint brought the chroma of the info
# bar, the suggestions and the selected suggestion within 1.0 of Clair's
# control, hover and selected tokens, and left the base within two channels of
# Clair's canvas. Their lightness stayed GX's own, 4.8 to 10.6 L* darker
# than those tokens.
LIGHT_BASE_CANDIDATE = {"h": 48, "s": 10, "l": 98}


def _checked_hint(hint: object) -> dict[str, int]:
    if not isinstance(hint, Mapping) or set(hint) != {"h", "s", "l"}:
        raise ValueError("A GX hint has exactly h, s and l")
    for key, top in (("h", 359), ("s", 100), ("l", 100)):
        value = hint[key]
        if type(value) is not int or not 0 <= value <= top:
            raise ValueError("GX hint values are integers in range")
    return {"h": hint["h"], "s": hint["s"], "l": hint["l"]}


def theme_manifest(themes: Mapping[str, Mapping[str, str]], version: str, *,
                   light_base: Mapping[str, int] | None = None) -> dict:
    """Paired payload. light_base replaces only Clair's derived base hint."""
    if set(themes) != {"Clair", "Obscur"}:
        raise ValueError("GX requires both Clair light and Obscur dark appearances")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("GX version must contain three integers")
    bases = {"light": hsl_hint(themes["Clair"]["canvas"]) if light_base is None else _checked_hint(light_base),
             "dark": hsl_hint(themes["Obscur"]["canvas"])}
    return {
        "manifest_version": 3,
        "name": "Clair and Obscur",
        "version": version,
        "description": "Color-only candidate. Clair light and Obscur dark hints; Opera GX derives the interface palette.",
        "developer": {"name": "T92T1914"},
        "icons": {"512": "icon512.png"},
        "mod": {
            "schema_version": 1,
            "license": "LICENSE.txt",
            "payload": {"theme": {
                mode: {"gx_accent": hsl_hint(themes[name]["accent"]),
                       "gx_secondary_base": bases[mode]}
                for mode, name in (("light", "Clair"), ("dark", "Obscur"))
            }},
        },
    }


def package_icon(themes: Mapping[str, Mapping[str, str]]) -> bytes:
    """An original geometric palette mark, without fonts or upstream artwork."""
    if set(themes) != {"Clair", "Obscur"}:
        raise ValueError("GX icon requires both appearances")
    colors = {name: {key: bytes(_rgb(themes[name][key])) for key in ("canvas", "accent")}
              for name in ("Clair", "Obscur")}
    rows = []
    for y in range(512):
        key = "accent" if 240 <= y < 272 else "canvas"
        rows.append(b"\x00" + colors["Clair"][key] * 256 + colors["Obscur"][key] * 256)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))
