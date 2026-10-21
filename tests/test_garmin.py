"""Palette and source-derived geometry checks, not Monkey C runtime acceptance."""

import copy
import json
import math
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from themeforge.garmin import VERSION, main, render_palette


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

EXPECTED_MONOCHROME_COLORS = {
    "CLAIR_CANVAS": 0xFFFFFF, "CLAIR_PANEL": 0xFFFFFF,
    "CLAIR_TEXT": 0x000000, "CLAIR_MUTED": 0x444444,
    "CLAIR_DIVIDER": 0xAAAAAA, "CLAIR_CONTROL": 0xF0F0F0,
    "CLAIR_HOVER": 0xE0E0E0, "CLAIR_SELECTED": 0xE8E8E8,
    "CLAIR_BORDER": 0x666666, "CLAIR_ACCENT": 0x000000,
    "CLAIR_ON_ACCENT": 0xFFFFFF, "CLAIR_FOCUS": 0x000000,
    "CLAIR_SUCCESS": 0x000000, "CLAIR_WARNING": 0x000000,
    "CLAIR_ERROR": 0x000000, "CLAIR_CODE": 0xF5F5F5,
    "CLAIR_DISABLED": 0x666666,
    "OBSCUR_CANVAS": 0x000000, "OBSCUR_PANEL": 0x000000,
    "OBSCUR_TEXT": 0xFFFFFF, "OBSCUR_MUTED": 0xCCCCCC,
    "OBSCUR_DIVIDER": 0x505050, "OBSCUR_CONTROL": 0x151515,
    "OBSCUR_HOVER": 0x252525, "OBSCUR_SELECTED": 0x202020,
    "OBSCUR_BORDER": 0x999999, "OBSCUR_ACCENT": 0xFFFFFF,
    "OBSCUR_ON_ACCENT": 0x000000, "OBSCUR_FOCUS": 0xFFFFFF,
    "OBSCUR_SUCCESS": 0xFFFFFF, "OBSCUR_WARNING": 0xFFFFFF,
    "OBSCUR_ERROR": 0xFFFFFF, "OBSCUR_CODE": 0x080808,
    "OBSCUR_DISABLED": 0xAAAAAA,
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
        current = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / "garmin/watchface/source/GeneratedPalette.mc").read_bytes(),
                         render_palette(current).encode("utf-8"))

    def test_current_palette_has_exact_black_white_and_neutral_roles(self):
        current = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))
        source = render_palette(current)
        self.assertEqual(VERSION, "0.6.0")
        self.assertEqual(colors(source), EXPECTED_MONOCHROME_COLORS)
        self.assertIn('const WATCHFACE_VERSION = "0.6.0";', source)
        self.assertIn('const TOKEN_VERSION = "1.0.0";', source)
        for color in colors(source).values():
            self.assertEqual((color >> 16) & 255, (color >> 8) & 255)
            self.assertEqual((color >> 8) & 255, color & 255)
        # The active primary text and battery accent use opposite black/white
        # endpoints: (1 + .05) / (0 + .05) = 21. Native pixels remain untested.
        for name, background, foreground in (("CLAIR", 0xFFFFFF, 0), ("OBSCUR", 0, 0xFFFFFF)):
            for role in ("CANVAS", "PANEL"):
                self.assertEqual(colors(source)[name + "_" + role], background)
            for role in ("TEXT", "ACCENT"):
                self.assertEqual(colors(source)[name + "_" + role], foreground)

    def test_default_cli_is_monochrome_and_legacy_input_remains_explicit(self):
        current = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "current.mc"
            self.assertEqual(main(["--output", str(output)]), 0)
            self.assertEqual(output.read_bytes(), render_palette(current).encode("utf-8"))
            self.assertEqual(main(["--output", str(output), "--check"]), 0)
            legacy = Path(temporary) / "legacy.mc"
            self.assertEqual(main(["--tokens", str(ROOT / "tokens.json"), "--output", str(legacy)]), 0)
            self.assertEqual(colors(legacy.read_text(encoding="utf-8")), EXPECTED_COLORS)
            self.assertEqual(main(["--tokens", str(ROOT / "tokens.json"), "--output", str(legacy), "--check"]), 0)

    def test_monochrome_update_retains_app_storage_keys_fonts_and_black_aod(self):
        face = ROOT / "garmin/watchface"
        manifest = ET.parse(face / "manifest.xml").getroot()
        namespace = {"iq": "http://www.garmin.com/xml/connectiq"}
        app = manifest.find("iq:application", namespace)
        self.assertEqual(app.get("id"), "358023fe938b4d0dafa59913baf7ceec")
        self.assertEqual([node.get("id") for node in app.findall("iq:products/iq:product", namespace)],
                         ["fenix9pro47mm"])
        properties = ET.parse(face / "resources/settings/properties.xml").getroot()
        self.assertEqual([(node.get("id"), node.get("type"), node.text) for node in properties],
                         [("appVersion", "string", "0.6.0"), ("appearance", "number", "1"),
                          ("layout", "number", "0"),
                          ("leftData", "number", "0"), ("rightData", "number", "1")])
        view = (face / "source/ClairObscurView.mc").read_text(encoding="utf-8")
        self.assertIn('(clair ? ThemePalette.CLAIR_CANVAS : ThemePalette.OBSCUR_CANVAS) : 0x000000;', view)
        self.assertIn('dc.setColor(ThemePalette.OBSCUR_MUTED, 0x000000);', view)
        for native_face in ("BionicBold", "RobotoMedium", "RobotoCondensedRegular"):
            self.assertIn('fonts("' + native_face + '"', view)

    def test_launcher_retains_geometry_with_only_black_white_and_neutral_ink(self):
        launcher = ET.parse(ROOT / "garmin/watchface/resources/drawables/launcher.svg").getroot()
        self.assertEqual((launcher.get("width"), launcher.get("height"), launcher.get("viewBox")),
                         ("65", "65", "0 0 65 65"))
        current = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))
        ink = [node.get(attribute) for node in launcher for attribute in ("fill", "stroke")
               if node.get(attribute) is not None]
        self.assertEqual(ink, [current["themes"]["Obscur"]["canvas"],
                               current["themes"]["Obscur"]["canvas"],
                               current["themes"]["Obscur"]["text"],
                               current["themes"]["Clair"]["canvas"],
                               current["themes"]["Clair"]["border"]])
        self.assertEqual(set(ink), {"#000000", "#ffffff", "#666666"})
        self.assertEqual([node.tag.rsplit("}", 1)[-1] for node in launcher],
                         ["rect", "circle", "path", "circle"])
        self.assertEqual(launcher[2].get("d"), "M 32.5 10.5 A 22 22 0 0 0 32.5 54.5 Z")
        self.assertEqual(launcher[3].get("r"), "5")


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


class GarminActiveBandGeometryTests(unittest.TestCase):
    """Source geometry and requested font sizes, not measured Garmin font fit."""

    @classmethod
    def setUpClass(cls):
        source = ROOT / "garmin/watchface/source"
        model = (source / "FaceModel.mc").read_text(encoding="utf-8")
        cls.bands = {}
        for name, edge, value in re.findall(
                r"^    const ([A-Z]+)_(TOP|BOTTOM|WIDTH) = (\d+);$", model, re.MULTILINE):
            cls.bands.setdefault(name, {})[edge] = int(value)
        cls.view = (source / "ClairObscurView.mc").read_text(encoding="utf-8")
        # Keep the accepted digital font contract explicit while the analog
        # branch has its own, separately qualified candidates.
        refresh = cls.view.split("function refreshFonts(", 1)[1].split("    function pickFont(", 1)[0]
        analog, digital = refresh.split("        } else {", 1)
        cls.fonts = {}
        declarations = re.findall(
            r'_(\w+)Fonts\s*=\s*fonts\("([A-Za-z]+)",\s*\[([\d, ]+)\],\s*'
            r'Graphics\.(FONT_[A-Z_]+),\s*scale\);', digital)
        for role, face, sizes, fallback in declarations:
            if role in cls.fonts:
                raise AssertionError("Duplicate active font candidate declaration")
            cls.fonts[role] = {"face": face, "sizes": [int(size) for size in sizes.split(",")],
                               "fallback": fallback}
        cls.line_bindings = re.findall(
            r"_(\w+)Fonts,\s*FaceModel\.([A-Z]+)_WIDTH,\s*"
            r"FaceModel\.([A-Z]+)_TOP,\s*FaceModel\.([A-Z]+)_BOTTOM\);", cls.view)
        cls.slots = [(name, int(left), int(width)) for name, left, width in re.findall(
            r"drawSlot\(dc,\s*(left|right),\s*(\d+),\s*(\d+),\s*FaceModel\.DATA_TOP,\s*FaceModel\.DATA_BOTTOM,\s*text,\s*muted,\s*canvas\);",
            cls.view)]
        cls.row_caps = {role: int(height) for role, height in re.findall(
            r'pickFont\(dc,\s*data\["(label|detail)"\],\s*_\1Fonts,\s*width,\s*(\d+)\);',
            cls.view)}

    def test_four_separate_bands_fit_inside_the_round_display(self):
        order = ["CALENDAR", "TIME", "DATA", "BATTERY"]
        self.assertEqual(set(self.bands), set(order))
        previous_bottom = 0
        for name in order:
            band = self.bands[name]
            self.assertEqual(set(band), {"TOP", "BOTTOM", "WIDTH"})
            self.assertGreater(band["BOTTOM"], band["TOP"])
            self.assertGreater(band["WIDTH"], 0)
            self.assertGreaterEqual(band["TOP"], previous_bottom)
            left = (454 - band["WIDTH"]) // 2
            for x in (left, left + band["WIDTH"] - 1):
                for y in (band["TOP"], band["BOTTOM"] - 1):
                    with self.subTest(band=name, corner=(x, y)):
                        self.assertLessEqual((2 * x + 1 - 454) ** 2 +
                                             (2 * y + 1 - 454) ** 2, 454 ** 2)
            previous_bottom = band["BOTTOM"]

    def test_native_font_requests_bind_to_the_actual_single_line_bands(self):
        self.assertEqual(set(self.fonts), {"clock", "calendar", "value", "label", "detail", "battery"})
        for role, candidates in self.fonts.items():
            with self.subTest(role=role):
                self.assertIn(candidates["face"], {"BionicBold", "RobotoMedium", "RobotoCondensedRegular"})
                self.assertTrue(candidates["sizes"])
                self.assertTrue(all(size > 0 for size in candidates["sizes"]))
                self.assertEqual(candidates["sizes"], sorted(set(candidates["sizes"]), reverse=True))
                self.assertIn(candidates["fallback"], {"FONT_XTINY", "FONT_LARGE"})
        self.assertEqual(self.line_bindings, [
            ("calendar", "CALENDAR", "CALENDAR", "CALENDAR"),
            ("clock", "TIME", "TIME", "TIME"),
            ("battery", "BATTERY", "BATTERY", "BATTERY"),
        ])
        # Installed target scale limits bound the requested vector font sizes.
        # A size request does not establish actual Dc.getFontHeight or text width.
        for role, name, _, _ in self.line_bindings:
            available_height = self.bands[name]["BOTTOM"] - self.bands[name]["TOP"]
            for scale_percent in (80, 100, 135):
                with self.subTest(band=name, scale_percent=scale_percent):
                    self.assertTrue(all(math.ceil(size * scale_percent / 100) <= available_height
                                        for size in self.fonts[role]["sizes"]))

    def test_two_clipped_data_slots_have_a_gap_inside_the_actual_data_band(self):
        self.assertEqual(self.slots, [("left", 77, 140), ("right", 237, 140)])
        data = self.bands["DATA"]
        data_left = (454 - data["WIDTH"]) // 2
        previous_right = data_left
        for name, left, width in self.slots:
            with self.subTest(slot=name):
                self.assertGreater(width, 0)
                self.assertGreaterEqual(left, previous_right)
                self.assertGreaterEqual(left, data_left)
                self.assertLessEqual(left + width, data_left + data["WIDTH"])
            previous_right = left + width
        self.assertEqual(self.slots[1][1] - (self.slots[0][1] + self.slots[0][2]), 20)
        self.assertIn("var height = bottom - top;", self.view)
        self.assertIn("dc.setClip(x, top, width, height);", self.view)
        self.assertEqual(re.findall(
            r"var (left|right) = FaceData\.readSlot\(FaceSettings\.readSlot\(([01])\), moment\.value\(\)\);",
            self.view), [("left", "0"), ("right", "1")])

    def test_scaled_data_font_requests_leave_room_for_all_three_rows(self):
        self.assertEqual(self.row_caps, {"label": 34, "detail": 28})
        gaps = re.findall(r"y \+= dc\.getFontHeight\((label|value)\) \+ (\d+);", self.view)
        self.assertEqual(gaps, [("label", "3"), ("value", "3")])
        total_gap = sum(int(gap) for _, gap in gaps)
        self.assertIn("var available = height - dc.getFontHeight(label) - dc.getFontHeight(detail) - 6;",
                      self.view)
        self.assertIn('value = pickFont(dc, data["value"], _valueFonts, width, available);',
                      self.view)
        self.assertEqual(total_gap, 6)
        available_height = self.bands["DATA"]["BOTTOM"] - self.bands["DATA"]["TOP"]
        for scale_percent in (80, 100, 135):
            # Independent arithmetic checks the largest requested size in each
            # row. Runtime metrics, font availability and fitting still require
            # actual target execution; a vector size is not a measured glyph box.
            requested = {role: math.ceil(max(self.fonts[role]["sizes"]) * scale_percent / 100)
                         for role in ("label", "value", "detail")}
            with self.subTest(scale_percent=scale_percent):
                self.assertLessEqual(requested["label"], self.row_caps["label"])
                self.assertLessEqual(requested["detail"], self.row_caps["detail"])
                self.assertLessEqual(sum(requested.values()) + total_gap, available_height)

    def test_hot_numeric_font_cannot_be_admitted_by_width_alone(self):
        time = self.bands["TIME"]
        # The initial width-only selection would accept this horizontal fit even
        # though the target's documented HOT height overlaps following content.
        plausible_width = 300
        self.assertLessEqual(plausible_width, time["WIDTH"])
        self.assertGreater(173, time["BOTTOM"] - time["TOP"])
        self.assertNotEqual("FONT_NUMBER_HOT", self.fonts["clock"]["fallback"])
        self.assertRegex(self.view,
                         r"dc\.getTextWidthInPixels\(text, candidates\[i\]\) <= width &&\s*"
                         r"dc\.getFontHeight\(candidates\[i\]\) <= height")


class GarminAnalogGeometryTests(unittest.TestCase):
    """Executable source/resource bounds, separate from Monkey C runtime tests."""

    @classmethod
    def setUpClass(cls):
        source = ROOT / "garmin/watchface/source"
        cls.model = (source / "FaceModel.mc").read_text(encoding="utf-8")
        cls.view = (source / "ClairObscurView.mc").read_text(encoding="utf-8")
        cls.constants = {name: int(value) for name, value in re.findall(
            r"^    const ([A-Z_]+) = (\d+);$", cls.model, re.MULTILINE)}

    def test_marker_track_and_distinct_hands_fit_the_round_display(self):
        c = self.constants
        self.assertEqual(c["DISPLAY_SIZE"], 454)
        self.assertEqual(c["DIAL_CENTER"], 227)
        self.assertLess(c["HOUR_HAND_LENGTH"] * 1.3, c["MINUTE_HAND_LENGTH"])
        self.assertLess(c["MINUTE_HAND_LENGTH"], c["MARKER_OUTER"])
        self.assertLess(c["MARKER_OUTER"], c["TICK_INNER"])
        self.assertLess(c["TICK_INNER"], c["TICK_OUTER"])
        # Include half the one-pixel track stroke and worst coordinate rounding.
        self.assertLess(c["TICK_OUTER"] + 0.5 + math.sqrt(0.5), 454 / 2)
        # Double-twelve offset and baton half-width total ten pixels.
        self.assertLess(math.hypot(c["MARKER_OUTER"], 10), c["TICK_INNER"])

    def test_all_three_analog_text_regions_stay_inside_the_circle(self):
        c = self.constants
        rectangles = [
            ((454 - c["ANALOG_DATE_WIDTH"]) / 2, c["ANALOG_DATE_TOP"],
             c["ANALOG_DATE_WIDTH"], c["ANALOG_DATE_BOTTOM"] - c["ANALOG_DATE_TOP"]),
            (c["ANALOG_LEFT_X"], c["ANALOG_DATA_TOP"], c["ANALOG_DATA_WIDTH"],
             c["ANALOG_DATA_BOTTOM"] - c["ANALOG_DATA_TOP"]),
            (c["ANALOG_RIGHT_X"], c["ANALOG_DATA_TOP"], c["ANALOG_DATA_WIDTH"],
             c["ANALOG_DATA_BOTTOM"] - c["ANALOG_DATA_TOP"]),
            ((454 - c["ANALOG_CHARGE_WIDTH"]) / 2, c["ANALOG_CHARGE_TOP"],
             c["ANALOG_CHARGE_WIDTH"], c["ANALOG_CHARGE_BOTTOM"] - c["ANALOG_CHARGE_TOP"]),
        ]
        self.assertGreaterEqual(c["ANALOG_DATA_BOTTOM"] - c["ANALOG_DATA_TOP"], 82)
        self.assertLess(c["ANALOG_LEFT_X"] + c["ANALOG_DATA_WIDTH"], c["ANALOG_RIGHT_X"])
        self.assertLess(c["ANALOG_DATE_BOTTOM"], c["ANALOG_DATA_TOP"])
        self.assertLess(c["ANALOG_DATA_BOTTOM"], c["ANALOG_CHARGE_TOP"])
        for left, top, width, height in rectangles:
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
            for x in (left, left + width - 1):
                for y in (top, top + height - 1):
                    with self.subTest(rect=(left, top, width, height), corner=(x, y)):
                        self.assertLess((x + 0.5 - 227) ** 2 + (y + 0.5 - 227) ** 2, 227 ** 2)
        # Bind those measured regions to the actual renderer, not unused constants.
        for band in ("DATE", "CHARGE"):
            self.assertRegex(self.view, rf"FaceModel\.ANALOG_{band}_WIDTH,\s*"
                             rf"FaceModel\.ANALOG_{band}_TOP,\s*FaceModel\.ANALOG_{band}_BOTTOM")
        for side in ("LEFT", "RIGHT"):
            self.assertRegex(self.view, rf"FaceModel\.ANALOG_{side}_X,\s*FaceModel\.ANALOG_DATA_WIDTH,\s*"
                             r"FaceModel\.ANALOG_DATA_TOP,\s*FaceModel\.ANALOG_DATA_BOTTOM")

    def test_layout_resource_is_numeric_analog_default_with_digital_alternative(self):
        resources = ROOT / "garmin/watchface/resources"
        properties = ET.parse(resources / "settings/properties.xml").getroot()
        layout = properties.findall("property[@id='layout']")
        self.assertEqual(len(layout), 1)
        self.assertEqual((layout[0].get("type"), layout[0].text), ("number", "0"))
        settings = ET.parse(resources / "settings/settings.xml").getroot()
        selection = settings.findall("setting[@propertyKey='@Properties.layout']")
        self.assertEqual(len(selection), 1)
        strings = {node.get("id"): node.text for node in
                   ET.parse(resources / "strings/strings.xml").getroot().findall("string")}
        config = selection[0].find("settingConfig")
        self.assertEqual(config.get("type"), "list")
        self.assertEqual([(entry.get("value"), strings[entry.text.removeprefix("@Strings.")])
                          for entry in config], [("0", "Analog"), ("1", "Digital")])
        self.assertEqual((self.constants["LAYOUT_ANALOG"], self.constants["LAYOUT_DIGITAL"]), (0, 1))
        namespace = {"iq": "http://www.garmin.com/xml/connectiq"}
        manifest = ET.parse(ROOT / "garmin/watchface/manifest.xml").getroot()
        permissions = manifest.findall("iq:application/iq:permissions/iq:uses-permission", namespace)
        self.assertEqual([node.get("id") for node in permissions], ["ComplicationSubscriber"])

    def test_original_digital_aod_body_and_early_exit_before_active_reads(self):
        import hashlib
        start = self.view.index("    function drawAlwaysOn(")
        opening = self.view.index("{", start)
        depth = 0
        closing = None
        for index in range(opening, len(self.view)):
            if self.view[index] == "{":
                depth += 1
            elif self.view[index] == "}":
                depth -= 1
                if depth == 0:
                    closing = index + 1
                    break
        self.assertIsNotNone(closing)
        body = self.view[start:closing]
        # Independently captured accepted 0.3 method, not recomputed from current output.
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),
                         "c6a3beb2f450153cf7ef1fb116c66d5dfd6f55ab8b66809eaf1ffc82ce0adbbd")
        self.assertEqual((self.constants["AOD_MAX_WIDTH"], self.constants["AOD_MAX_HEIGHT"]), (192, 64))
        on_update = self.view.split("function onUpdate(", 1)[1].split("function analogSlotFonts(", 1)[0]
        analog = re.search(r"if \(mode == :aod && layout == FaceModel\.LAYOUT_ANALOG\) \{\s*"
                          r"drawAnalogAlwaysOn\(dc, local\.hour, local\.min\);\s*return;\s*\}", on_update)
        digital = re.search(r"if \(mode == :aod\) \{ drawAlwaysOn\(dc, time, local\.min\); return; \}",
                            on_update)
        self.assertIsNotNone(analog)
        self.assertIsNotNone(digital)
        self.assertLess(on_update.index("FaceSettings.readLayout()"), analog.start())
        self.assertLess(analog.end(), on_update.index("System.getDeviceSettings()"))
        self.assertLess(analog.end(), digital.start())
        for active_read in ("refreshFonts(layout)", "FaceData.readSlot(", "FaceSettings.readSlot(",
                            "System.getSystemStats()", "FaceModel.formatBattery("):
            self.assertLess(digital.end(), on_update.index(active_read), active_read)


class GarminAnalogAodGeometryTests(unittest.TestCase):
    """Source-bound host geometry and conservative budgets, not native pixels."""

    @classmethod
    def setUpClass(cls):
        source = ROOT / "garmin/watchface/source"
        cls.model = (source / "FaceModel.mc").read_text(encoding="utf-8")
        cls.view = (source / "ClairObscurView.mc").read_text(encoding="utf-8")
        cls.palette = (source / "GeneratedPalette.mc").read_text(encoding="utf-8")
        cls.constants = {name: int(value) for name, value in re.findall(
            r"^    const ([A-Z_]+) = (\d+);$", cls.model, re.MULTILINE)}
        offset = cls.function(cls.model, "aodAnalogOffset")
        cls.offsets = [tuple(map(int, pair)) for pair in re.findall(
            r"return \[(-?\d+), (-?\d+)\];", offset)]
        size = cls.constants["DISPLAY_SIZE"]
        cls.round_pixels = sum((2 * x + 1 - size) ** 2 + (2 * y + 1 - size) ** 2 <= size ** 2
                               for y in range(size) for x in range(size))

    @staticmethod
    def function(source, name):
        start = source.index("    function " + name + "(")
        opening = source.index("{", start)
        depth = 0
        for index in range(opening, len(source)):
            depth += (source[index] == "{") - (source[index] == "}")
            if depth == 0:
                return source[start:index + 1]
        raise AssertionError("Unclosed source function: " + name)

    @classmethod
    def radial(cls, turn, radius, lateral):
        angle = turn * math.tau
        center = cls.constants["DIAL_CENTER"]
        # Positive display coordinates use nearest integer, with halves upward.
        return (math.floor(center + math.sin(angle) * radius + math.cos(angle) * lateral + 0.5),
                math.floor(center - math.cos(angle) * radius + math.sin(angle) * lateral + 0.5))

    @classmethod
    def outlines(cls, hour, minute, shift):
        """Independent polar construction for the bound active marker/hand source."""
        paths = []
        for index in range(12):
            for part in range(2 if index == 0 else 1):
                offset = (-7 if part == 0 else 7) if index == 0 else 0
                half = 4 if index != 0 and index % 3 == 0 else 3
                inner = 172 if index % 3 == 0 else 178
                paths.append([cls.radial(index / 12, radius, side) for radius, side in
                              ((inner, offset - half), (cls.constants["MARKER_OUTER"], offset - half),
                               (cls.constants["MARKER_OUTER"], offset + half), (inner, offset + half))])
        for hour_hand in (True, False):
            turn = (hour % 12) / 12 + minute / 720 if hour_hand else minute / 60
            length = cls.constants["HOUR_HAND_LENGTH" if hour_hand else "MINUTE_HAND_LENGTH"]
            half, tail = (9, 6) if hour_hand else (5, 3)
            paths.append([cls.radial(turn, radius, side) for radius, side in
                          ((-18, -tail), (length - 18, -half), (length, 0),
                           (length - 18, half), (-18, tail))])
        return [[(x + shift[0], y + shift[1]) for x, y in path] for path in paths]

    @staticmethod
    def guarded_l1_bound(paths, width):
        # A width-wide L1 strip plus a square endpoint guard for every closed
        # edge. Summing overlapping strips overcounts. The circle gets its own
        # larger square, including its radius-three outline and AA allowance.
        center_square = 9 if width == 3 else 13
        return center_square ** 2 + sum(
            width * (abs(b[0] - a[0]) + abs(b[1] - a[1]) + width)
            for path in paths for a, b in zip(path, path[1:] + path[:1]))

    def assert_shifted_helper(self, source, name, active):
        body = self.function(source, name)
        self.assertIn("var shift = aodAnalogOffset(minute);", body)
        self.assertIn("if (shift.size() != 2) { return []; }" if active == "handPoints" else
                      "if (i == null || p == null || shift.size() != 2) { return []; }", body)
        self.assertIn("var points = " + active + "(", body)
        self.assertRegex(body, r"for \(var point = 0; point < points\.size\(\); point \+= 1\)")
        self.assertEqual(re.findall(r"result\.add\(([^;]+)\);", body),
                         ["[points[point][0] + shift[0], points[point][1] + shift[1]]"])
        self.assertTrue(body.rstrip().endswith("return result;\n    }"))

    def assert_outline_renderer(self, source):
        outline = self.function(source, "drawAlwaysOnOutline")
        analog = self.function(source, "drawAnalogAlwaysOn")
        self.assertIn("if (points.size() < 3) { return; }", outline)
        self.assertIn("var next = (point + 1) % points.size();", outline)
        self.assertRegex(outline, r"dc\.drawLine\(points\[point\]\[0\], points\[point\]\[1\], "
                         r"points\[next\]\[0\], points\[next\]\[1\]\);")
        self.assertEqual(re.findall(r"\bdc\.(\w+)\(", outline), ["drawLine"])
        self.assertEqual(re.findall(r"\bdc\.(\w+)\(", analog), ["setColor", "setPenWidth", "drawCircle"])
        self.assertIn("dc.setColor(ThemePalette.OBSCUR_BORDER, 0x000000);", analog)
        self.assertIn("dc.setPenWidth(1);", analog)
        self.assertIn("for (var index = 0; index < 12; index += 1)", analog)
        self.assertRegex(analog, r"drawAlwaysOnOutline\(dc, FaceModel\.aodAnalogMarker\(index, 0, minute\)\);")
        self.assertRegex(analog, r"if \(index == 0\) \{\s*drawAlwaysOnOutline\(dc, "
                         r"FaceModel\.aodAnalogMarker\(index, 1, minute\)\);\s*\}")
        for which in ("true", "false"):
            self.assertIn(f"drawAlwaysOnOutline(dc, FaceModel.aodAnalogHandPoints(hour, minute, {which}));", analog)
        self.assertIn("dc.drawCircle(FaceModel.DIAL_CENTER + shift[0], FaceModel.DIAL_CENTER + shift[1], 3);", analog)
        self.assertNotRegex(outline + analog, r"fillPolygon|fillCircle|drawText|drawHand\(|drawSlot\(|"
                            r"FaceData|System\.|Time\.|Timer|requestUpdate|refreshFonts|interClock")

    def test_geometry_is_bound_to_accepted_active_shapes_and_shifted_outline_renderer(self):
        import hashlib
        # Independently captured from accepted main 87148's unchanged active
        # functions. The Python polar model cannot silently validate other code.
        expected = {
            "radialPoint": "2c7a11d9fa53ab1d968ae51190a830961e9c91c1de28e3df0eee5c4317f9cb37",
            "hourTurns": "cb83ffef970693a7f8919e0174b76654b86f6b21a00ad0421518e00d391cc4e8",
            "minuteTurns": "09807ffd398176aed87deb7fc70c5f56ec875e6173aaa833631df546dee48f86",
            "hourMarker": "a3442689c1c0c9d3d20d7507f59a21230df5befbb16d704ba92761746d97ce38",
            "handPoints": "14ffd7a770ea13e1832b2bfc6c67954674311b9e50a9acfb9857edae64a7e72a",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(self.function(self.model, name).encode()).hexdigest(), digest, name)
        self.assert_shifted_helper(self.model, "aodAnalogMarker", "hourMarker")
        self.assert_shifted_helper(self.model, "aodAnalogHandPoints", "handPoints")
        self.assert_outline_renderer(self.view)
        color = colors(self.palette)["OBSCUR_BORDER"]
        self.assertEqual(color, EXPECTED_MONOCHROME_COLORS["OBSCUR_BORDER"])
        self.assertEqual(color, 0x999999)
        self.assertTrue(0 < color < 0xFFFFFF)

    def test_four_phases_move_all_outlines_together_and_wrap_the_minute(self):
        self.assertEqual(self.offsets, [(-2, -2), (2, -2), (2, 2), (-2, 2)])
        offset = self.function(self.model, "aodAnalogOffset")
        self.assertIn("var phase = m % 4;", offset)
        self.assertIn("if (m == null || m < 0 || m >= 60) { return []; }", offset)
        self.assertEqual(re.findall(r"if \(phase == (\d)\)", offset), ["0", "1", "2"])
        for minute in range(60):
            before, after = self.offsets[minute % 4], self.offsets[((minute + 1) % 60) % 4]
            self.assertEqual(sum((a - b) ** 2 for a, b in zip(after, before)), 16)
            active = self.outlines(11, minute, (0, 0))
            shifted = self.outlines(11, minute, before)
            self.assertNotEqual(shifted, active)
            self.assertEqual([[(x - before[0], y - before[1]) for x, y in path] for path in shifted], active)

    def test_all_720_clock_positions_at_every_phase_keep_guarded_edges_in_round_display(self):
        self.assertEqual((self.constants["DISPLAY_SIZE"], self.constants["DIAL_CENTER"]), (454, 227))
        center, radius = self.constants["DIAL_CENTER"], self.constants["DISPLAY_SIZE"] / 2
        scenarios = 0
        for hour in range(12):
            for minute in range(60):
                for shift in self.offsets:
                    paths = self.outlines(hour, minute, shift)
                    self.assertEqual([len(path) for path in paths], [4] * 13 + [5, 5])
                    # The round disk is convex. Guarding every vertex also
                    # bounds each intervening closed edge and its square guard.
                    for path in paths:
                        for x, y in path:
                            for dx, dy in ((-3, -3), (-3, 3), (3, -3), (3, 3)):
                                self.assertLess((x + dx - center) ** 2 + (y + dy - center) ** 2, radius ** 2)
                    # Radius-three center outline plus a larger AA guard.
                    for dx, dy in ((-6, -6), (-6, 6), (6, -6), (6, 6)):
                        self.assertLess((shift[0] + dx) ** 2 + (shift[1] + dy) ** 2, radius ** 2)
                    scenarios += 1
        self.assertEqual(scenarios, 720 * 4)

    def test_closed_edge_l1_bounds_keep_even_guarded_white_luminance_below_round_ten_percent(self):
        maxima = {3: 0, 5: 0}
        for hour in range(12):
            for minute in range(60):
                for shift in self.offsets:
                    paths = self.outlines(hour, minute, shift)
                    self.assertEqual(sum(len(path) for path in paths), 62)
                    for width in maxima:
                        maxima[width] = max(maxima[width], self.guarded_l1_bound(paths, width))
        self.assertGreater(maxima[5], maxima[3])
        for bound in maxima.values():
            self.assertGreater(bound, 0)
            self.assertLess(bound * 10, self.round_pixels)
        # This is a conservative source-geometry budget, including a five-pixel
        # edge strip, overlaps counted repeatedly and a 13x13 center guard.
        # Treating all that coverage as full white also bounds normalized
        # luminance. Actual Garmin AA, pixel coverage and burn-in remain unknown.

    def test_controls_reject_filled_edges_and_an_unshifted_aod_path(self):
        filled = self.view.replace("dc.drawLine(points[point][0]", "dc.fillPolygon(points[point][0]", 1)
        self.assertNotEqual(filled, self.view)
        with self.assertRaises(AssertionError):
            self.assert_outline_renderer(filled)
        unshifted = self.model.replace("points[point][0] + shift[0]", "points[point][0]", 1)
        self.assertNotEqual(unshifted, self.model)
        with self.assertRaises(AssertionError):
            self.assert_shifted_helper(unshifted, "aodAnalogMarker", "hourMarker")


class GarminSettingsResourcesTests(unittest.TestCase):
    def test_one_numeric_property_matches_both_labeled_choices_and_dark_default(self):
        resources = ROOT / "garmin/watchface/resources"
        properties = ET.parse(resources / "settings/properties.xml").getroot()
        appearance = properties.findall("property[@id='appearance']")
        self.assertEqual(len(appearance), 1)
        self.assertEqual(appearance[0].get("type"), "number")
        self.assertEqual(appearance[0].text.strip(), "1")
        settings = ET.parse(resources / "settings/settings.xml").getroot()
        selection = settings.findall("setting[@propertyKey='@Properties.appearance']")
        self.assertEqual(len(selection), 1)
        config = selection[0].find("settingConfig")
        self.assertIsNotNone(config)
        self.assertEqual(config.get("type"), "list")
        strings = {element.get("id"): element.text for element in
                   ET.parse(resources / "strings/strings.xml").getroot().findall("string")}
        entries = []
        for entry in config.findall("listEntry"):
            self.assertRegex(entry.get("value"), r"^[01]$")
            self.assertTrue(entry.text.startswith("@Strings."))
            entries.append((int(entry.get("value")), strings[entry.text.removeprefix("@Strings.")]))
        self.assertEqual(entries, [(0, "Clair"), (1, "Obscur")])
        # This checks the resource binding, not persistence or menu activation.
        self.assertEqual(dict(entries)[int(appearance[0].text)], "Obscur")

    def test_both_numeric_data_slots_resolve_unique_choices_and_distinct_defaults(self):
        resources = ROOT / "garmin/watchface/resources"
        properties = ET.parse(resources / "settings/properties.xml").getroot()
        settings = ET.parse(resources / "settings/settings.xml").getroot()
        string_elements = ET.parse(resources / "strings/strings.xml").getroot().findall("string")
        strings = {element.get("id"): element.text for element in string_elements}
        self.assertEqual(len(strings), len(string_elements), "Resource string IDs must be unique")
        for name, default, title, label in (("leftData", 0, "Left data", "Weather"),
                                            ("rightData", 1, "Right data", "Steps")):
            with self.subTest(slot=name):
                prop = properties.findall(f"property[@id='{name}']")
                self.assertEqual(len(prop), 1)
                self.assertEqual(prop[0].get("type"), "number")
                self.assertEqual(prop[0].text.strip(), str(default))
                selection = settings.findall(f"setting[@propertyKey='@Properties.{name}']")
                self.assertEqual(len(selection), 1)
                title_reference = selection[0].get("title")
                self.assertTrue(title_reference.startswith("@Strings."))
                self.assertEqual(strings[title_reference.removeprefix("@Strings.")], title)
                config = selection[0].find("settingConfig")
                self.assertIsNotNone(config)
                self.assertEqual(config.get("type"), "list")
                entries = []
                for entry in config.findall("listEntry"):
                    self.assertRegex(entry.get("value"), r"^[012]$")
                    self.assertTrue(entry.text.startswith("@Strings."))
                    entries.append((int(entry.get("value")), strings[entry.text.removeprefix("@Strings.")]))
                self.assertEqual(entries, [(0, "Weather"), (1, "Steps"), (2, "Body Battery")])
                self.assertEqual(len({value for value, _ in entries}), len(entries))
                # Resource identity and defaults only, not native menu or phone
                # activation, observed data availability or persistence.
                self.assertEqual(dict(entries)[int(prop[0].text)], label)


if __name__ == "__main__":
    unittest.main()
