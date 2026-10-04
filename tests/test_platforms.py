"""Platform packages, paired states and preservation of the original release."""

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from themeforge.build import PROJECT_ROOT, PORTABILITY_VERSION, build_release
from themeforge.discord_clients import render_client_theme
from themeforge.firefox import COLOR_TOKENS, theme_manifest
from themeforge.tokens import contrast, load


class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = load(PROJECT_ROOT / "tokens.json")["themes"]

    def test_original_four_downloads_keep_the_accepted_release_bytes(self):
        expected = {
            "artifacts/Clair-Chrome-0.1.1.zip": "4bfa96dd8ffa50647d507c5b7aabb0d82f7c96b7cf07f4beaa73c43a5579aad5",
            "artifacts/Obscur-Chrome-0.1.1.zip": "b8bb73a48ddbc1e8f2f92258d30c3875b17d9d5ec98eab04c457eab2f2a5474a",
            "equicord/Clair.theme.css": "0f3337db8fc9ea35ff52e36e0d1028d242f1af30e2c1edd144af11939173f847",
            "equicord/Obscur.theme.css": "b2fc01e87f749c1138ca5635eb77f1463d2bcb2eac6d5de898bb8d840741d1dd",
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            manifest = build_release(PROJECT_ROOT / "tokens.json", output)
            self.assertEqual(manifest["version"], "0.1.1")
            self.assertEqual(manifest["adapter_version"], "0.2.0")
            for path, digest in expected.items():
                self.assertEqual(hashlib.sha256((output / path).read_bytes()).hexdigest(), digest)
            for name in ("Clair", "Obscur"):
                chrome = next(d for d in manifest["downloads"] if d["platform"] == "chrome" and d["name"] == name)
                edge = next(d for d in manifest["downloads"] if d["platform"] == "edge" and d["name"] == name)
                self.assertEqual(edge["path"], chrome["path"])
                self.assertEqual(edge["native_acceptance"], "unverified")
            paths = {download["path"] for download in manifest["downloads"]}
            self.assertEqual(len(paths), 13)
            self.assertEqual(len({Path(path).name for path in paths}), 13)

    def test_firefox_xpi_is_only_the_static_manifest_and_license(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            manifest = build_release(PROJECT_ROOT / "tokens.json", output)
            for download in (d for d in manifest["downloads"] if d["platform"] == "firefox"):
                self.assertEqual(download["kind"], "unsigned-static-theme-xpi")
                with zipfile.ZipFile(output / download["path"]) as package:
                    self.assertEqual(package.namelist(), ["LICENSE.txt", "manifest.json"])
                    parsed = json.loads(package.read("manifest.json"))
                    self.assertEqual(parsed, theme_manifest(download["name"], self.tokens[download["name"]], PORTABILITY_VERSION))
                    for entry in package.infolist():
                        self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertFalse(any(key in parsed for key in ("permissions", "background", "content_scripts", "host_permissions", "dark_theme")))

    def test_firefox_manual_browser_mode_preserves_system_content_preference(self):
        for name, mode in (("Clair", "light"), ("Obscur", "dark")):
            manifest = theme_manifest(name, self.tokens[name], "0.2.0")
            self.assertEqual(manifest["theme"]["properties"], {"color_scheme": mode, "content_color_scheme": "system"})
            self.assertEqual(set(manifest["theme"]["colors"]), set(COLOR_TOKENS))
            self.assertNotIn("tab_background_separator", manifest["theme"]["colors"])
            self.assertNotIn("toolbar_field_separator", manifest["theme"]["colors"])

    def test_firefox_declared_text_selection_and_focus_pairings_have_contrast(self):
        pairs = (("tab_text", "tab_selected"), ("tab_background_text", "frame"),
                 ("tab_background_text", "frame_inactive"), ("toolbar_field_text", "toolbar_field"),
                 ("toolbar_field_text_focus", "toolbar_field_focus"), ("popup_text", "popup"),
                 ("popup_highlight_text", "popup_highlight"), ("sidebar_text", "sidebar"),
                 ("sidebar_highlight_text", "sidebar_highlight"),
                 ("toolbar_field_highlight_text", "toolbar_field_highlight"),
                 ("ntp_text", "ntp_background"), ("ntp_text", "ntp_card_background"))
        for name in self.tokens:
            colors = theme_manifest(name, self.tokens[name], "0.2.0")["theme"]["colors"]
            for fg, bg in pairs:
                self.assertGreaterEqual(contrast(colors[fg], colors[bg]), 4.5, (name, fg, bg))
            self.assertGreaterEqual(contrast(colors["toolbar_field_border_focus"], colors["toolbar_field_focus"]), 3)

    def test_firefox_invalid_input_does_not_inject_manifest_capabilities(self):
        for name in ("unknown", "Clair\nscript"):
            with self.assertRaises(ValueError):
                theme_manifest(name, self.tokens["Clair"], "0.2.0")
        for version in ("0.2.0\n", "1.2", "0.2.0-preview", None):
            with self.assertRaises(ValueError):
                theme_manifest("Clair", self.tokens["Clair"], version)
        for value in ("red", "#fff", "#ffffff;script", None):
            with self.assertRaises(ValueError):
                theme_manifest("Clair", {**self.tokens["Clair"], "canvas": value}, "0.2.0")

    def test_build_rejects_firefox_permissions_before_installing_output(self):
        real = theme_manifest
        def injected(*args):
            result = real(*args)
            result["permissions"] = ["tabs"]
            return result
        with tempfile.TemporaryDirectory() as directory, patch("themeforge.build.firefox_manifest", side_effect=injected):
            output = Path(directory) / "build"
            with self.assertRaisesRegex(ValueError, "unexpected manifest capabilities"):
                build_release(PROJECT_ROOT / "tokens.json", output)
            self.assertFalse(output.exists())

    def test_client_metadata_and_local_typography_are_self_contained(self):
        for client, label in (("vencord", "Vencord"), ("betterdiscord", "BetterDiscord")):
            for name in self.tokens:
                css = render_client_theme(client, name, self.tokens[name], "0.2.0")
                fields = dict(re.findall(r"^ \* @(\w+) (.+)$", css, re.MULTILINE))
                self.assertEqual(fields["name"], name)
                self.assertEqual(fields["version"], "0.2.0")
                self.assertIn(label + ".", fields["description"])
                self.assertEqual(css.count("@font-face"), 6)
                self.assertNotRegex(css, r"@import\b|url\s*\(|https?://|!important|filter:")
                self.assertNotRegex(css, r"(?:^|\n)\s*(?:width|height|position|display|transform|font-size):")
                self.assertNotIn("--font-code:", css)
                self.assertNotIn(":root", css)

    def test_client_specific_switches_do_not_inherit_a_pale_fill_white_handle(self):
        vc = render_client_theme("vencord", "Obscur", self.tokens["Obscur"], "0.2.0")
        bd = render_client_theme("betterdiscord", "Obscur", self.tokens["Obscur"], "0.2.0")
        self.assertIn(".vc-switch-container.vc-switch-checked", vc)
        self.assertIn(".vc-switch-checked .vc-switch-slider > rect { fill: var(--co-on-accent); }", vc)
        self.assertIn(".bd-switch input:checked + .bd-switch-body .bd-switch-handle { fill: var(--co-on-accent); }", bd)
        self.assertIn(".bd-button-filled:is(.bd-button-color-brand, .bd-button-color-blurple, .bd-button-color-link)", bd)
        self.assertIn(".bd-switch input:focus-visible + .bd-switch-body", bd)
        self.assertIn(".vc-switch-container.vc-switch-focusVisible", vc)
        for css in (vc, bd):
            self.assertIn("@media (forced-colors: active)", css)
            self.assertIn("@media (prefers-reduced-motion: reduce)", css)
            self.assertNotIn(".bd-switch-disabled {", css)
            self.assertNotIn("--control-critical-primary-background-default:", css)

    def test_unknown_client_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Client must"):
            render_client_theme("other", "Clair", self.tokens["Clair"], "0.2.0")


if __name__ == "__main__":
    unittest.main()
