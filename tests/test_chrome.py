import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from themeforge.chrome import build_theme
from themeforge.tokens import contrast, load


TOKENS = {
    "canvas": "#090909", "panel": "#151515", "text": "#f4f4f4",
    "muted": "#bcbcbc", "divider": "#494949", "control": "#252525",
    "hover": "#373737", "selected": "#333333", "border": "#858585",
    "accent": "#b1bcec", "on_accent": "#090909", "focus": "#b1bcec",
    "success": "#88cba2", "warning": "#e3c179", "error": "#f09c98",
    "code": "#151515", "disabled": "#858585",
}

# Independent reviewed upstream allowlist, not the generator's mapping table.
NATIVE_COLORS = {
    "background_tab", "background_tab_inactive", "background_tab_incognito",
    "background_tab_incognito_inactive", "bookmark_text", "button_background",
    "frame", "frame_inactive", "frame_incognito", "frame_incognito_inactive",
    "ntp_background", "ntp_header", "ntp_link", "ntp_text",
    "omnibox_background", "omnibox_text", "tab_background_text",
    "tab_background_text_inactive", "tab_background_text_incognito",
    "tab_background_text_incognito_inactive", "tab_text", "toolbar",
    "toolbar_button_icon", "toolbar_text",
}


class ChromeThemeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_both_variants_are_native_packages_with_only_reviewed_colors(self):
        for name in ("Clair", "Obscur"):
            with self.subTest(name=name):
                target = build_theme(name, TOKENS, self.root, "1.2.3")
                self.assertEqual(target, self.root / name.lower())
                self.assertEqual({p.name for p in target.iterdir()}, {"manifest.json", "icon128.png", "LICENSE.txt"})
                canonical = (Path(__file__).resolve().parents[1] / "LICENSE").read_text(encoding="utf-8")
                self.assertEqual((target / "LICENSE.txt").read_text(encoding="utf-8"), canonical)
                manifest = json.loads((target / "manifest.json").read_text())
                self.assertEqual(set(manifest), {"manifest_version", "name", "version", "description", "icons", "theme"})
                self.assertEqual(manifest["manifest_version"], 3)
                self.assertEqual(manifest["name"], name)
                self.assertEqual(set(manifest["theme"]), {"colors"})
                colors = manifest["theme"]["colors"]
                self.assertTrue(set(colors) <= NATIVE_COLORS)
                self.assertFalse(any("incognito" in key for key in colors))
                for value in colors.values():
                    self.assertEqual(len(value), 3)
                    self.assertTrue(all(type(channel) is int and 0 <= channel <= 255 for channel in value))

    def test_active_and_inactive_surfaces_and_text_use_different_roles(self):
        target = build_theme("Obscur", TOKENS, self.root, "1")
        colors = json.loads((target / "manifest.json").read_text())["theme"]["colors"]
        self.assertEqual(colors["toolbar"], [21, 21, 21])
        self.assertEqual(colors["frame"], [9, 9, 9])
        self.assertEqual(colors["background_tab"], [37, 37, 37])
        self.assertEqual(colors["tab_text"], [244, 244, 244])
        self.assertEqual(colors["tab_background_text"], [188, 188, 188])
        self.assertEqual(colors["omnibox_text"], colors["tab_text"])
        self.assertEqual(colors["bookmark_text"], colors["tab_text"])

    def test_actual_palettes_keep_explicit_native_text_and_icon_pairs_readable(self):
        document = load(Path(__file__).resolve().parents[1] / "tokens.json")
        pairs = (
            ("tab_text", "toolbar", 4.5),
            ("tab_background_text", "background_tab", 4.5),
            ("tab_background_text_inactive", "background_tab_inactive", 4.5),
            ("toolbar_text", "toolbar", 4.5),
            ("bookmark_text", "toolbar", 4.5),
            ("omnibox_text", "omnibox_background", 4.5),
            ("ntp_text", "ntp_background", 4.5),
            ("ntp_link", "ntp_background", 4.5),
            ("toolbar_button_icon", "toolbar", 3),
        )
        for name, tokens in document["themes"].items():
            target = build_theme(name, tokens, self.root, document["version"])
            manifest = json.loads((target / "manifest.json").read_text())
            colors = {key: "#" + "".join(f"{channel:02x}" for channel in value)
                      for key, value in manifest["theme"]["colors"].items()}
            for foreground, background, minimum in pairs:
                with self.subTest(theme=name, foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(colors[foreground], colors[background]), minimum)
            # Different RGB values are a mapping invariant, not native visual acceptance.
            self.assertNotEqual(colors["toolbar"], colors["background_tab"])
            self.assertNotEqual(colors["frame"], colors["frame_inactive"])

    def test_repeat_build_is_byte_identical_and_version_updates_are_scoped(self):
        target = build_theme("Obscur", TOKENS, self.root, "1.2.3")
        first = {p.name: p.read_bytes() for p in target.iterdir()}
        build_theme("Obscur", dict(reversed(list(TOKENS.items()))), self.root, "1.2.3")
        self.assertEqual(first, {p.name: p.read_bytes() for p in target.iterdir()})
        build_theme("Obscur", TOKENS, self.root, "1.2.4")
        updated = json.loads((target / "manifest.json").read_bytes())
        prior = json.loads(first["manifest.json"])
        self.assertEqual(updated.pop("version"), "1.2.4")
        prior.pop("version")
        self.assertEqual(updated, prior)
        self.assertEqual((target / "icon128.png").read_bytes(), first["icon128.png"])

    def test_icon_decodes_as_srgb_rgba_with_transparent_padding_and_valid_crcs(self):
        target = build_theme("Obscur", TOKENS, self.root, "1")
        raw = (target / "icon128.png").read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        chunks = {}
        position = 8
        while position < len(raw):
            size = struct.unpack(">I", raw[position:position + 4])[0]
            kind = raw[position + 4:position + 8]
            content = raw[position + 8:position + 8 + size]
            checksum = struct.unpack(">I", raw[position + 8 + size:position + 12 + size])[0]
            self.assertEqual(checksum, zlib.crc32(kind + content))
            chunks[kind] = content
            position += size + 12
        self.assertEqual(position, len(raw))
        self.assertEqual(set(chunks), {b"IHDR", b"sRGB", b"IDAT", b"IEND"})
        self.assertEqual(struct.unpack(">2I5B", chunks[b"IHDR"]), (128, 128, 8, 6, 0, 0, 0))
        self.assertEqual(chunks[b"sRGB"], b"\x00")
        pixels = zlib.decompress(chunks[b"IDAT"])
        self.assertEqual(len(pixels), 128 * (1 + 128 * 4))
        for y in range(128):
            self.assertEqual(pixels[y * 513], 0)
            for x in range(128):
                alpha = pixels[y * 513 + 1 + x * 4 + 3]
                self.assertEqual(alpha, 255 if 16 <= x < 112 and 16 <= y < 112 else 0)

    def test_invalid_color_and_missing_token_do_not_create_outputs(self):
        for value in ("#fff", "#000000ff", "red", "url(https://example.com/)", [0, 0, 0], None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "six-digit RGB"):
                    build_theme("Clair", {**TOKENS, "panel": value}, self.root, "1")
                self.assertFalse((self.root / "clair").exists())
        missing = dict(TOKENS)
        del missing["text"]
        with self.assertRaisesRegex(ValueError, "Missing native Chrome tokens: text"):
            build_theme("Clair", missing, self.root, "1")

    def test_unsupported_token_names_cannot_add_permissions_or_font_overrides(self):
        target = build_theme("Clair", {**TOKENS, "permissions": ["tabs"], "font_family": "Inter"}, self.root, "1")
        text = (target / "manifest.json").read_text()
        self.assertNotIn("permissions", text)
        self.assertNotIn("font_family", text)
        self.assertNotIn("Inter", text)

    def test_version_rules_include_chrome_boundaries(self):
        for version in ("0", "0.0.0.0", "01", "1.02", "1.2.3.4.5", "65536", "-1", "1.0-beta", "1\n", 1):
            with self.subTest(version=version), self.assertRaises(ValueError):
                build_theme("Clair", TOKENS, self.root, version)
        for version in ("1", "0.1", "65535.65535.65535.65535"):
            with self.subTest(version=version):
                build_theme("Clair", TOKENS, self.root, version)

    def test_invalid_name_cannot_escape_destination(self):
        for name in ("../other", "clair/other", "..", "", "Obscur ", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_theme(name, TOKENS, self.root, "1")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unrelated_existing_file_is_preserved(self):
        target = self.root / "clair"
        target.mkdir()
        unrelated = target / "notes.txt"
        unrelated.write_text("keep")
        with self.assertRaisesRegex(ValueError, "unrelated files"):
            build_theme("Clair", TOKENS, self.root, "1")
        self.assertEqual(unrelated.read_text(), "keep")
        self.assertEqual(list(target.iterdir()), [unrelated])

    def test_unrelated_existing_manifest_is_preserved(self):
        target = self.root / "clair"
        target.mkdir()
        manifest = target / "manifest.json"
        for raw in ('{"name":"Unrelated","theme":{}}', '[]', '{invalid'):
            manifest.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                build_theme("Clair", TOKENS, self.root, "1")
            self.assertEqual(manifest.read_text(), raw)
            self.assertFalse((target / "icon128.png").exists())

    def test_failed_atomic_write_keeps_old_manifest_and_removes_temporary_file(self):
        target = build_theme("Obscur", TOKENS, self.root, "1")
        original = (target / "manifest.json").read_bytes()
        with patch("themeforge.chrome.os.replace", side_effect=OSError("disk write refused")):
            with self.assertRaisesRegex(OSError, "disk write refused"):
                build_theme("Obscur", TOKENS, self.root, "2")
        self.assertEqual((target / "manifest.json").read_bytes(), original)
        self.assertEqual({p.name for p in target.iterdir()}, {"manifest.json", "icon128.png", "LICENSE.txt"})


if __name__ == "__main__":
    unittest.main()
