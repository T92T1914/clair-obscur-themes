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


def theme_manifest(themes: Mapping[str, Mapping[str, str]], version: str) -> dict:
    if set(themes) != {"Clair", "Obscur"}:
        raise ValueError("GX requires both Clair light and Obscur dark appearances")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("GX version must contain three integers")
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
                       "gx_secondary_base": hsl_hint(themes[name]["canvas"])}
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
