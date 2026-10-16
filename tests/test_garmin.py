"""Palette and source-derived geometry checks, not Monkey C runtime acceptance."""

import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

from themeforge.garmin import main, render_palette


ROOT = Path(__file__).resolve().parents[1]

# Independent literal expectations retain the accepted desktop semantic identity.
EXPECTED_COLORS = {
    "CLAIR_CANVAS": 0xF8F7F3, "CLAIR_PANEL": 0xFDFCF8,
    "CLAIR_TEXT": 0x242424, "CLAIR_MUTED": 0x595854,
    "CLAIR_DIVIDER": 0xB8B6AE, "CLAIR_CONTROL": 0xECEBE6,
    "CLAIR_HOVER": 0xE0DED7, "CLAIR_SELECTED": 0xE7E4DA,
    "CLAIR_BORDER": 0x7F7D76, "CLAIR_ACCENT": 0x365F78,
    "CLAIR_ON_ACCENT": 0xFFFFFF, "CLAIR_FOCUS": 0x315977,
    "CLAIR_SUCCESS": 0x276548, "CLAIR_WARNING": 0x805100,
    "CLAIR_ERROR": 0xA32E32, "CLAIR_CODE": 0xEEECE5,
    "CLAIR_DISABLED": 0x686760,
    "OBSCUR_CANVAS": 0x090909, "OBSCUR_PANEL": 0x151515,
    "OBSCUR_TEXT": 0xF4F4F4, "OBSCUR_MUTED": 0xBCBCBC,
    "OBSCUR_DIVIDER": 0x494949, "OBSCUR_CONTROL": 0x252525,
    "OBSCUR_HOVER": 0x373737, "OBSCUR_SELECTED": 0x333333,
    "OBSCUR_BORDER": 0x858585, "OBSCUR_ACCENT": 0xB3C8D8,
    "OBSCUR_ON_ACCENT": 0x15212C, "OBSCUR_FOCUS": 0xC2D7E6,
    "OBSCUR_SUCCESS": 0x8ECB9B, "OBSCUR_WARNING": 0xE3BF79,
    "OBSCUR_ERROR": 0xF2A3A3, "OBSCUR_CODE": 0x111111,
    "OBSCUR_DISABLED": 0xA4A4A4,
}


def colors(source):
    declarations = re.findall(r"^    const ([A-Z_]+) = 0x([0-9A-F]{6});$", source, re.MULTILINE)
    if len(declarations) != len(dict(declarations)):
        raise AssertionError("Duplicate generated color declaration")
    return {name: int(value, 16) for name, value in declarations}


class GarminPaletteTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))

    def test_every_accepted_role_has_its_own_exact_numeric_color(self):
        source = render_palette(self.document)
        self.assertEqual(colors(source), EXPECTED_COLORS)
        self.assertIn('const TOKEN_SCHEMA = 1;', source)
        self.assertIn('const TOKEN_VERSION = "0.1.1";', source)
        self.assertIn((ROOT / "LICENSE").read_text(encoding="utf-8"), source)
        # Dark desktop gray remains gray. The renderer owns a separate black AOD.
        self.assertNotEqual(colors(source)["OBSCUR_CANVAS"], 0)

    def test_key_order_does_not_change_source_and_input_is_not_mutated(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {
            name: dict(reversed(list(values.items())))
            for name, values in reversed(list(self.document["themes"].items()))
        }
        self.assertEqual(render_palette(reordered), render_palette(self.document))
        self.assertEqual(self.document, before)

    def test_mapping_consumes_valid_changes_instead_of_a_frozen_palette_copy(self):
        changed = copy.deepcopy(self.document)
        changed["themes"]["Clair"]["canvas"] = "#f7f6f2"
        changed["version"] = "2.3.4"
        source = render_palette(changed)
        expected = {**EXPECTED_COLORS, "CLAIR_CANVAS": 0xF7F6F2}
        self.assertEqual(colors(source), expected)
        self.assertIn('const TOKEN_VERSION = "2.3.4";', source)

    def test_invalid_role_color_schema_and_contrast_are_refused(self):
        invalid = []
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        extra = copy.deepcopy(self.document)
        extra["themes"]["Clair"]["unexpected"] = "#123456"
        invalid.append(extra)
        injection = copy.deepcopy(self.document)
        injection["themes"]["Clair"]["focus"] = '#315977; System.println("injected")'
        invalid.append(injection)
        contrast = copy.deepcopy(self.document)
        contrast["themes"]["Clair"]["text"] = "#f8f7f3"
        invalid.append(contrast)
        invalid.extend([None, [], {**self.document, "schema_version": True}])
        for document in invalid:
            with self.subTest(document=document), self.assertRaises(ValueError):
                render_palette(document)

    def test_generation_and_check_use_only_the_selected_source_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tokens = directory / "tokens.json"
            tokens.write_text(json.dumps(self.document), encoding="utf-8")
            output = directory / "source" / "GeneratedPalette.mc"
            arguments = ["--tokens", str(tokens), "--output", str(output)]
            self.assertEqual(main(arguments), 0)
            self.assertEqual(output.read_bytes(), render_palette(self.document).encode("utf-8"))
            before = {path.relative_to(directory): path.read_bytes()
                      for path in directory.rglob("*") if path.is_file()}
            self.assertEqual(main([*arguments, "--check"]), 0)
            after = {path.relative_to(directory): path.read_bytes()
                     for path in directory.rglob("*") if path.is_file()}
            self.assertEqual(after, before)
            output.write_bytes(output.read_bytes() + b"// edited\n")
            changed = output.read_bytes()
            with self.assertRaisesRegex(ValueError, "differs"):
                main([*arguments, "--check"])
            self.assertEqual(output.read_bytes(), changed)

    def test_check_does_not_create_a_missing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "missing" / "GeneratedPalette.mc"
            with self.assertRaisesRegex(ValueError, "differs"):
                main(["--tokens", str(ROOT / "tokens.json"), "--output", str(output), "--check"])
            self.assertFalse(output.parent.exists())

    def test_committed_palette_is_the_current_generated_source(self):
        self.assertEqual((ROOT / "garmin/watchface/source/GeneratedPalette.mc").read_bytes(),
                         render_palette(self.document).encode("utf-8"))


class GarminAodGeometryTests(unittest.TestCase):
    """Conservative declared-box bounds, without executing the Garmin renderer."""

    @classmethod
    def setUpClass(cls):
        model = (ROOT / "garmin/watchface/source/FaceModel.mc").read_text(encoding="utf-8")
        cls.constants = {name: int(value) for name, value in re.findall(
            r"^    const (DISPLAY_SIZE|AOD_MAX_WIDTH|AOD_MAX_HEIGHT|AOD_SHIFT) = (\d+);$",
            model, re.MULTILINE)}
        if set(cls.constants) != {"DISPLAY_SIZE", "AOD_MAX_WIDTH", "AOD_MAX_HEIGHT", "AOD_SHIFT"}:
            raise AssertionError("The actual model must expose all four literal geometry bounds")
        size = cls.constants["DISPLAY_SIZE"]
        # Count pixel centers inside the round screen, not its square bounding image.
        cls.round_pixels = sum(
            (2 * x + 1 - size) ** 2 + (2 * y + 1 - size) ** 2 <= size ** 2
            for y in range(size) for x in range(size))

    def test_maximum_clipped_box_bounds_lit_area_and_white_luminance(self):
        self.assertEqual(self.constants["DISPLAY_SIZE"], 454)
        maximum_lit_pixels = self.constants["AOD_MAX_WIDTH"] * self.constants["AOD_MAX_HEIGHT"]
        self.assertGreater(maximum_lit_pixels, 0)
        self.assertLess(maximum_lit_pixels * 10, self.round_pixels)
        # Even if every admitted pixel were full white, normalized luminance is
        # bounded by this same fraction. Actual font output and clipping remain
        # simulator/hardware acceptance questions, not Python rendering results.
        self.assertLess(maximum_lit_pixels / self.round_pixels, 0.10)

    def test_declared_box_and_shift_extremes_stay_inside_round_screen(self):
        size = self.constants["DISPLAY_SIZE"]
        width = self.constants["AOD_MAX_WIDTH"]
        height = self.constants["AOD_MAX_HEIGHT"]
        shift = self.constants["AOD_SHIFT"]
        for box_width, box_height in ((width, height), (width - 1, height - 1), (1, 1)):
            for dx in (-shift, 0, shift):
                for dy in (-shift, 0, shift):
                    left = (size - box_width) // 2 + dx
                    top = (size - box_height) // 2 + dy
                    for x in (left, left + box_width - 1):
                        for y in (top, top + box_height - 1):
                            with self.subTest(box=(box_width, box_height), shift=(dx, dy), corner=(x, y)):
                                self.assertLessEqual((2 * x + 1 - size) ** 2 +
                                                     (2 * y + 1 - size) ** 2, size ** 2)

    def test_control_rejects_a_box_that_square_denominator_would_admit(self):
        # A hypothetical changed 170x100 box fits a square-based 10% calculation
        # but violates the project's visible-round-pixel rule.
        wrong_box_area = 170 * 100
        size = self.constants["DISPLAY_SIZE"]
        self.assertLess(wrong_box_area * 10, size * size)
        self.assertGreaterEqual(wrong_box_area * 10, self.round_pixels)


if __name__ == "__main__":
    unittest.main()
