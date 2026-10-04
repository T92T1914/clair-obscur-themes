"""Native-format candidate boundaries and unchanged established downloads."""

import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID
import zipfile
import zlib

from themeforge.build import BROWSER_VERSION, PROJECT_ROOT, _review_payloads, build_release
from themeforge.opera_gx import hsl_hint, package_icon, theme_manifest
from themeforge.tokens import contrast, load
from themeforge.vivaldi import COLOR_TOKENS, theme_id, theme_settings


# Exact bytes previously served at the accepted 573cb043 deployment. Aliases
# add choices without replacing the actual Chrome or earlier client payloads.
ESTABLISHED = {
    "artifacts/Clair-Chrome-0.1.1.zip": "4bfa96dd8ffa50647d507c5b7aabb0d82f7c96b7cf07f4beaa73c43a5579aad5",
    "artifacts/Obscur-Chrome-0.1.1.zip": "b8bb73a48ddbc1e8f2f92258d30c3875b17d9d5ec98eab04c457eab2f2a5474a",
    "equicord/Clair.theme.css": "0f3337db8fc9ea35ff52e36e0d1028d242f1af30e2c1edd144af11939173f847",
    "equicord/Obscur.theme.css": "b2fc01e87f749c1138ca5635eb77f1463d2bcb2eac6d5de898bb8d840741d1dd",
    "artifacts/Clair-Firefox-0.2.0.xpi": "72fb8c7cdb5db8465382a897bce07701f3ffc9172af3d2808e390997c6190ae2",
    "artifacts/Obscur-Firefox-0.2.0.xpi": "3bf5bdfc6436eff3219fefd00a88d095567d51c60d2851a073cb0a8a04de7a0b",
    "vencord/Clair-Vencord.theme.css": "f46e5ad65bbcb6ed3d68988ec064c8ea5cd824075c630c81695cb3b1c52b92ea",
    "vencord/Obscur-Vencord.theme.css": "22608a0ea5600b44b12fc0299f1f5981162c702197cfad2907a06086e9f4664a",
    "betterdiscord/Clair-BetterDiscord.theme.css": "fd7f6dd7453f8e01afc53ceb97c095919bb37106f6ddcde327a347bc8b5bcb66",
    "betterdiscord/Obscur-BetterDiscord.theme.css": "2661e2341fef8f02ceed4b47779e85a980c546ca8fe10b1559f16e4d25961806",
}


class BrowserAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.themes = load(PROJECT_ROOT / "tokens.json")["themes"]

    def test_vivaldi_original_colors_and_stable_separate_identities(self):
        identities = []
        for name in ("Clair", "Obscur"):
            settings = theme_settings(name, self.themes[name])
            self.assertEqual(set(settings), {"engineVersion", "id", "name", "version", *COLOR_TOKENS})
            self.assertEqual(settings["version"], 1)
            self.assertEqual(settings["engineVersion"], 1)
            self.assertEqual(UUID(settings["id"]).version, 5)
            self.assertEqual(settings["id"], theme_id(name))
            identities.append(settings["id"])
            for field, role in COLOR_TOKENS.items():
                self.assertEqual(settings[field], self.themes[name][role])
            for field in ("colorBg", "colorAccentBg", "colorWindowBg"):
                self.assertGreaterEqual(contrast(settings["colorFg"], settings[field]), 4.5)
        self.assertEqual(len(set(identities)), 2)

    def test_hsl_reference_colors_grayscale_and_literal_input(self):
        for value, expected in (("#ff0000", {"h": 0, "s": 100, "l": 50}),
                                ("#00ff00", {"h": 120, "s": 100, "l": 50}),
                                ("#0000ff", {"h": 240, "s": 100, "l": 50}),
                                ("#808080", {"h": 0, "s": 0, "l": 50}),
                                ("#000000", {"h": 0, "s": 0, "l": 0}),
                                ("#ffffff", {"h": 0, "s": 0, "l": 100})):
            self.assertEqual(hsl_hint(value), expected)
        self.assertEqual(hsl_hint("#FF0000"), hsl_hint("#ff0000"))
        for value in ("#fff", "red", "#ffffff;script", None, 123):
            with self.assertRaises(ValueError):
                hsl_hint(value)

    def test_gx_is_one_paired_color_only_payload_with_canonical_hints(self):
        manifest = theme_manifest(self.themes, BROWSER_VERSION)
        self.assertEqual(set(manifest), {"manifest_version", "name", "version", "description", "developer", "icons", "mod"})
        self.assertEqual(set(manifest["mod"]["payload"]), {"theme"})
        modes = manifest["mod"]["payload"]["theme"]
        self.assertEqual(modes, {
            "light": {"gx_accent": {"h": 203, "s": 38, "l": 34},
                      "gx_secondary_base": {"h": 48, "s": 26, "l": 96}},
            "dark": {"gx_accent": {"h": 206, "s": 32, "l": 77},
                     "gx_secondary_base": {"h": 0, "s": 0, "l": 4}},
        })
        # The extreme base hints are retained, not quietly clamped to claim
        # compatibility. GX's documented host color limits need native evidence.
        self.assertEqual(manifest["mod"]["license"], "LICENSE.txt")

    def test_invalid_candidate_identity_version_or_palette_is_refused(self):
        for name in ("Other", "Clair\nscript", None):
            with self.assertRaises(ValueError):
                theme_settings(name, self.themes["Clair"])
        for value in ("#fff", "url(remote)", None):
            with self.assertRaises(ValueError):
                theme_settings("Clair", {**self.themes["Clair"], "canvas": value})
        for version in (None, "0.3", "0.3.0\n", "0.3.0-preview"):
            with self.assertRaises(ValueError):
                theme_manifest(self.themes, version)
        with self.assertRaises(ValueError):
            theme_manifest({"Obscur": self.themes["Obscur"]}, BROWSER_VERSION)

    def test_gx_icon_has_only_original_palette_pixels_and_no_extra_chunks(self):
        icon = package_icon(self.themes)
        self.assertEqual(icon, package_icon(self.themes))
        self.assertEqual(icon[:8], b"\x89PNG\r\n\x1a\n")
        position, chunks = 8, []
        while position < len(icon):
            size = struct.unpack(">I", icon[position:position + 4])[0]
            kind, data = icon[position + 4:position + 8], icon[position + 8:position + 8 + size]
            crc = struct.unpack(">I", icon[position + 8 + size:position + 12 + size])[0]
            self.assertEqual(crc, zlib.crc32(kind + data) & 0xffffffff)
            chunks.append((kind, data))
            position += size + 12
        self.assertEqual([kind for kind, _ in chunks], [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(struct.unpack(">IIBBBBB", chunks[0][1]), (512, 512, 8, 2, 0, 0, 0))
        raw = zlib.decompress(chunks[1][1])
        self.assertEqual(len(raw), 512 * (1 + 512 * 3))
        for y in (0, 239, 240, 271, 272, 511):
            row = raw[y * 1537:(y + 1) * 1537]
            self.assertEqual(row[0], 0)
            role = "accent" if 240 <= y < 272 else "canvas"
            for x, name in ((0, "Clair"), (255, "Clair"), (256, "Obscur"), (511, "Obscur")):
                self.assertEqual(row[1 + x * 3:4 + x * 3].hex(), self.themes[name][role][1:])

    def test_build_preserves_ten_downloads_and_reuses_brave_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            manifest = build_release(PROJECT_ROOT / "tokens.json", output)
            self.assertEqual(manifest["browser_adapter_version"], "0.3.0")
            self.assertEqual(len(manifest["downloads"]), 17)
            self.assertEqual(len({item["path"] for item in manifest["downloads"]}), 13)
            for path, digest in ESTABLISHED.items():
                self.assertEqual(hashlib.sha256((output / path).read_bytes()).hexdigest(), digest, path)
            for name in ("Clair", "Obscur"):
                chrome = next(d for d in manifest["downloads"] if d["name"] == name and d["platform"] == "chrome")
                for platform in ("brave", "edge"):
                    alias = next(d for d in manifest["downloads"] if d["name"] == name and d["platform"] == platform)
                    self.assertEqual(alias["path"], chrome["path"])
                    self.assertEqual(alias["version"], "0.1.1")
                    self.assertEqual(alias["native_acceptance"], "unverified")
                with zipfile.ZipFile(output / f"artifacts/{name}-Vivaldi-0.3.0.zip") as archive:
                    self.assertEqual(archive.namelist(), ["settings.json"])
                    self.assertEqual(json.loads(archive.read("settings.json")), theme_settings(name, self.themes[name]))
                    self.assertEqual(archive.infolist()[0].date_time, (1980, 1, 1, 0, 0, 0))
            with zipfile.ZipFile(output / "artifacts/Clair-Obscur-OperaGX-0.3.0.zip") as archive:
                self.assertEqual(archive.namelist(), ["LICENSE.txt", "icon512.png", "manifest.json"])
                self.assertEqual(json.loads(archive.read("manifest.json")), theme_manifest(self.themes, BROWSER_VERSION))
                self.assertEqual(archive.read("LICENSE.txt"), (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8").encode())
                self.assertTrue(all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist()))

    def test_payload_review_rejects_host_changes_or_non_theme_gx_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            manifest = build_release(PROJECT_ROOT / "tokens.json", output)
            original = {record["path"]: (output / record["path"]).read_bytes()
                        for record in manifest["files"] if not record["path"].startswith("artifacts/")}
            for field, value in (("backgroundImage", "remote.png"), ("radius", 4), ("alpha", 0.9),
                                 ("accentFromPage", True), ("url", "https://example.com"), ("version", True)):
                changed = dict(original)
                settings = json.loads(changed["vivaldi/clair/settings.json"])
                settings[field] = value
                changed["vivaldi/clair/settings.json"] = json.dumps(settings).encode()
                with self.subTest(field=field), self.assertRaises(ValueError):
                    _review_payloads(changed)
            gx = json.loads(original["opera-gx/manifest.json"])
            mutations = []
            for payload in ("shaders", "page_styles", "wallpaper", "background_music"):
                mutated = copy.deepcopy(gx)
                mutated["mod"]["payload"][payload] = []
                mutations.append(mutated)
            mutated = copy.deepcopy(gx)
            del mutated["mod"]["payload"]["theme"]["light"]
            mutations.append(mutated)
            for value in (-1, 360, True, 12.5):
                mutated = copy.deepcopy(gx)
                mutated["mod"]["payload"]["theme"]["dark"]["gx_accent"]["h"] = value
                mutations.append(mutated)
            mutated = copy.deepcopy(gx)
            mutated["permissions"] = ["tabs"]
            mutations.append(mutated)
            mutated = copy.deepcopy(gx)
            mutated["icons"] = {"512": "https://example.com/icon.png"}
            mutations.append(mutated)
            for mutated in mutations:
                changed = {**original, "opera-gx/manifest.json": json.dumps(mutated).encode()}
                with self.assertRaises(ValueError):
                    _review_payloads(changed)

    def test_non_theme_injection_cannot_replace_an_existing_build(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            build_release(PROJECT_ROOT / "tokens.json", output)
            before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            def injected(*args):
                result = theme_manifest(*args)
                result["mod"]["payload"]["page_styles"] = []
                return result
            with patch("themeforge.build.gx_manifest", side_effect=injected), self.assertRaises(ValueError):
                build_release(PROJECT_ROOT / "tokens.json", output)
            self.assertEqual(before, {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()})
