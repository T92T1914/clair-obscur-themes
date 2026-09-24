"""Generator invariants. Real Equibop acceptance is a separate manual gate."""

import re
from pathlib import Path
import unittest

from themeforge.equicord import FACES, HOST_TOKENS, TOKEN_NAMES, render_theme


def palette():
    # Deliberately distinct values expose accidental semantic aliasing.
    return {key: f"#{index + 1:06x}" for index, key in enumerate(TOKEN_NAMES)}


class EquicordThemeTests(unittest.TestCase):
    def test_complete_license_follows_the_loader_metadata_in_its_own_comment(self):
        canonical = (Path(__file__).resolve().parents[1] / "LICENSE").read_text(encoding="utf-8")
        for name in ("Clair", "Obscur"):
            with self.subTest(name=name):
                css = render_theme(name, palette(), "0.1.0")
                metadata, remaining = css.split("*/", 1)
                self.assertTrue(metadata.startswith("/**\n * @name " + name))
                self.assertNotIn("MIT License", metadata)
                self.assertTrue(remaining.lstrip().startswith("/*\n" + canonical + "*/"))
                self.assertEqual(css.count(canonical), 1)

    def test_both_outputs_are_deterministic_with_loader_metadata(self):
        for name in ("Clair", "Obscur"):
            css = render_theme(name, palette(), "0.1.0")
            self.assertEqual(css, render_theme(name, dict(reversed(list(palette().items()))), "0.1.0"))
            header = dict(re.findall(r"^ \* @(\w+) (.+)$", css, re.MULTILINE))
            self.assertEqual(header["name"], name)
            self.assertEqual(header["version"], "0.1.0")
            self.assertEqual(header["author"], "T92T1914")
            self.assertIn("Equibop with Equicord", header["description"])
            self.assertNotIn("@import", css)
            self.assertNotIn("url(", css)
            self.assertNotIn("https://", css)

    def test_six_local_faces_preserve_real_styles_and_weights(self):
        css = render_theme("Obscur", palette(), "0.1.0")
        rules = re.findall(r"@font-face\s*\{([^}]+)\}", css)
        self.assertEqual(len(rules), 6)
        for weight, style, full, postscript in FACES:
            matches = [rule for rule in rules if f'local("{full}")' in rule]
            self.assertEqual(len(matches), 1)
            rule = matches[0]
            self.assertIn(f'local("{postscript}")', rule)
            self.assertIn(f"font-weight: {weight};", rule)
            self.assertIn(f"font-style: {style};", rule)
        self.assertNotIn("--font-code:", css)
        self.assertNotIn("font-size:", css)
        self.assertNotIn("font-variation-settings:", css)
        self.assertNotIn("transform:", css)
        self.assertNotIn("!important", css)

    def test_native_base_modes_are_explicitly_gated(self):
        light = render_theme("Clair", palette(), "1.0.0")
        dark = render_theme("Obscur", palette(), "1.0.0")
        self.assertIn(".theme-light {", light)
        self.assertNotIn(".theme-dark", light)
        self.assertIn(":is(.theme-dark, .theme-darker, .theme-midnight) {", dark)
        self.assertNotIn(".theme-light", dark)
        self.assertNotIn(":root", light + dark)
        self.assertIn("color-scheme: light;", light)
        self.assertIn("color-scheme: dark;", dark)

    def test_every_host_alias_resolves_to_a_declared_semantic_token(self):
        css = render_theme("Clair", palette(), "1.2.3")
        declarations = set(re.findall(r"(--co-[\w-]+):", css))
        refs = set(re.findall(r"var\((--co-[\w-]+)\)", css))
        self.assertLessEqual(refs, declarations)
        for host, token in HOST_TOKENS.items():
            self.assertIn(f"--{host}: var(--co-{token.replace('_', '-')});", css)

    def test_toggle_checked_unchecked_focus_and_disabled_are_distinct(self):
        css = render_theme("Obscur", palette(), "1.0.0")
        self.assertIn("--switch-background-default: var(--co-control)", css)
        self.assertIn("--switch-background-selected-default: var(--co-accent)", css)
        self.assertIn("--switch-thumb-background-selected-default: var(--co-on-accent)", css)
        self.assertIn(".vc-switch-focusVisible .vc-switch-indicator", css)
        self.assertIn("input:not(.vc-switch-input)", css)
        self.assertNotIn(".vc-switch-disabled {", css)
        self.assertIn("@media (forced-colors: active)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("--switch-thumb-background-selected-default: HighlightText", css)

    def test_semantic_feedback_and_user_content_are_not_flattened(self):
        css = render_theme("Clair", palette(), "1.0.0")
        self.assertIn("--text-danger: var(--co-error)", css)
        self.assertIn("--text-positive: var(--co-success)", css)
        self.assertIn("--text-warning: var(--co-warning)", css)
        for prohibited in ("filter:", "opacity:", "pointer-events:", "display: none", "[class*="):
            self.assertNotIn(prohibited, css)

    def test_current_equicord_button_contract_has_paired_colors(self):
        css = render_theme("Obscur", palette(), "1.0.0")
        for state in ("default", "hover"):
            self.assertIn(f"--control-primary-background-{state}: var(--co-accent)", css)
            self.assertIn(f"--control-primary-text-{state}: var(--co-on-accent)", css)
            self.assertIn(f"--control-secondary-text-{state}: var(--co-text)", css)
        self.assertIn(":is(.vc-btn-small, .vc-btn-medium)", css)
        # Filled critical actions retain the native paired foreground/background.
        self.assertNotIn("--control-critical-primary-background-default:", css)

    def test_invalid_source_cannot_inject_metadata_or_styles(self):
        for name in ("Unknown", "Clair\n */ body {color:red}"):
            with self.assertRaises(ValueError):
                render_theme(name, palette(), "1.0.0")
        for version in ("1.0\n * @author Other", "1.0.0 */", None):
            with self.assertRaises(ValueError):
                render_theme("Clair", palette(), version)
        broken = palette()
        del broken["canvas"]
        with self.assertRaisesRegex(ValueError, "Missing theme tokens: canvas"):
            render_theme("Clair", broken, "1.0.0")
        for bad in ("red", "#fff", "#ffffff; background:red", None, 123):
            broken = {**palette(), "canvas": bad}
            with self.assertRaisesRegex(ValueError, "Token canvas"):
                render_theme("Clair", broken, "1.0.0")


if __name__ == "__main__":
    unittest.main()
