"""Source-bound crossing locations and fit envelopes, not a face renderer.

These checks locate filled hand geometry against declared content bands. They
do not execute Monkey C, measure Garmin glyphs, or qualify native readability.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import unittest

import test_garmin as garmin_contracts


ROOT = Path(__file__).resolve().parents[1]
FUNCTION = garmin_contracts.GarminAnalogAodGeometryTests.function

# Whitespace-normalized function identities acquired from accepted PR93,
# 0ed5d6f1aad25894d8e608b3b6f1969d0b30e09b. These preserve algorithms only.
# The 0.12 dimensions below intentionally change shared Hybrid AOD geometry;
# old native AOD evidence does not qualify these new shapes.
MODEL_PINS = {
    "integerValue": "2631abbe874d94ae4c256a3b4c6c3b0b867b301f801d681e541cccca52f95f6a",
    "validClock": "8253b2de5a4f08bbe83686762d7cf8a6aa6151a3b2e40bd4939686d869d947f4",
    "radialPoint": "6c7a52933d4c3e4f771d680b5918252be642f7eb01e1f3fcb86be3cd7cc1e6e8",
    "hourTurns": "54ae9a48d5680506bc59ac9953820bec07a2a8ec0f5727a3270426f0f1b46fcb",
    "minuteTurns": "4c6019638079cdeaab470674690f6e72ef3b4d3f5a86309e315cb9c459dbd139",
    "hybridHourStem": "f6baf1ecee42f67ee22114b3d026d2ddc7da206034d154f3a371a1c4136e14b6",
    "hybridHourTip": "4a9d7b982ea190079445544d68575accc7390f890738c01419cf4cf82d7fe3fa",
    "hybridHourDiscCenter": "6116c4260c22f2015a5535309c0153559d861687b33853faee8178e85b5edf4c",
    "hybridHourSpoke": "aa3e95f408dd87653eade24c550d66eeb7d8f6b866378464d8770e296be3492b",
    "hybridMinuteHand": "dba6330d41a9b5825a89fd70d6bf07775921d2f2ba81ac228cb836c4fba1130d",
    "hybridTriangle": "7e25dba84e06a62b9313dddcdeabcade61079b486fd8a8f1e1e28579ede1cf91",
    "hybridBaton": "dfca39ba5e651a4498ee676a81dc7e952898b8b6d6447f4b79224fc68b69cc84",
    "hybridCircleCenter": "44f17d8ecdd8308757047c4f8b78bfea60b629bb9a402a4d2d62091e2404bcea",
    "hybridShiftPoints": "21564f6adfe860c7cf1e26099bb6f4e233d05a37599f331cbc6d0eb714091628",
    "aodAnalogOffset": "78d2b110623682193aa2951825b2456235d8f57af37f2692470e6dd08595167a",
}
VIEW_PINS = {
    "drawAlwaysOnOutline": "5f25e8b6a5220355ee4a030ed76bcbc95ddfd99588c377adca305505690851ab",
    "drawHybridAlwaysOn": "ebbca3153ef464f62716d7699c4edbd424759407729f918efc7f9d978f92f64b",
    "drawAnalogAlwaysOn": "16934eff0c08dc59cff7ef6428d4c41ecafe95e7dd06fbd08ad5dcd21773eb4a",
    "drawAlwaysOn": "811355c6ec4da71189bb1fcb1a110721359dcdf9c1894fb2f8f9e86227176d3f",
}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def point(c, turn, radius, lateral=0):
    angle = turn * math.tau
    center = c["DIAL_CENTER"]
    return (math.floor(center + math.sin(angle) * radius + math.cos(angle) * lateral + 0.5),
            math.floor(center - math.cos(angle) * radius + math.sin(angle) * lateral + 0.5))


def hand_geometry(c, total):
    """Independent rotated polygons/circle using the independently selected dimensions."""
    hour_turn, minute_turn = total / 720, (total % 60) / 60
    inner, outer, half = (c["HYBRID_HOUR_STEM_" + key] for key in ("INNER", "OUTER", "HALF"))
    stem = [point(c, hour_turn, radius, side) for radius, side in
            ((inner, -half), (outer, -half), (outer, half), (inner, half))]
    base, half, tip = (c["HYBRID_HOUR_TIP_" + key] for key in ("BASE", "HALF", "LENGTH"))
    arrow = [point(c, hour_turn, radius, side) for radius, side in
             ((base, -half), (tip, 0), (base, half))]
    length, half, tail = (c["HYBRID_MINUTE_" + key] for key in ("LENGTH", "HALF", "TAIL_HALF"))
    minute = [point(c, minute_turn, radius, side) for radius, side in
              ((-18, -tail), (length - 18, -half), (length, 0), (length - 18, half), (-18, tail))]
    return {"stem": stem, "tip": arrow, "minute": minute}, (
        point(c, hour_turn, c["HYBRID_HOUR_DISC_CENTER"]), c["HYBRID_HOUR_DISC_RADIUS"])


def polygon_intersects_box(polygon, box):
    """Separating-axis test for a convex polygon and an axis-aligned box."""
    left, top, right, bottom = box
    rectangle = ((left, top), (right, top), (right, bottom), (left, bottom))
    axes = [(1, 0), (0, 1)] + [(-(b[1] - a[1]), b[0] - a[0])
                              for a, b in zip(polygon, polygon[1:] + polygon[:1])]
    for nx, ny in axes:
        p = [x * nx + y * ny for x, y in polygon]
        r = [x * nx + y * ny for x, y in rectangle]
        if max(p) < min(r) or max(r) < min(p):
            return False
    return True


def circle_intersects_box(center, radius, box):
    x, y = center
    left, top, right, bottom = box
    return max(left - x, 0, x - right) ** 2 + max(top - y, 0, y - bottom) ** 2 <= radius ** 2


def reading_bands(c):
    result = {}
    for key, name in (("DATE", "calendar"), ("CHARGE", "battery")):
        left = (c["DISPLAY_SIZE"] - c[f"HYBRID_{key}_WIDTH"]) / 2
        result[name] = (left, c[f"HYBRID_{key}_TOP"], left + c[f"HYBRID_{key}_WIDTH"],
                        c[f"HYBRID_{key}_BOTTOM"])
    for key, name in (("LEFT", "weather"), ("RIGHT", "steps")):
        x = c[f"HYBRID_{key}_X"]
        result[name] = (x, c["HYBRID_DATA_TOP"], x + c["HYBRID_DATA_WIDTH"], c["HYBRID_DATA_BOTTOM"])
    return result


def crossing_report(c):
    result = {name: [] for name in reading_bands(c)}
    for total in range(720):
        polygons, (center, radius) = hand_geometry(c, total)
        for name, box in reading_bands(c).items():
            if any(polygon_intersects_box(p, box) for p in polygons.values()) or circle_intersects_box(center, radius, box):
                result[name].append(total)
    return result


class GarminReadingGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / "garmin/watchface/source"
        cls.model = (source / "FaceModel.mc").read_text(encoding="utf-8")
        cls.view = (source / "ClairObscurView.mc").read_text(encoding="utf-8")
        cls.palette = (source / "GeneratedPalette.mc").read_text(encoding="utf-8")
        cls.constants = {key: int(value) for key, value in re.findall(
            r"^    const ([A-Z_]+) = (-?\d+);$", cls.model, re.MULTILINE)}

    def test_shared_algorithms_retain_identity_and_selected_geometry_is_explicit(self):
        for source, pins in ((self.model, MODEL_PINS), (self.view, VIEW_PINS)):
            for name, expected in pins.items():
                with self.subTest(function=name):
                    self.assertEqual(digest(" ".join(FUNCTION(source, name).split())), expected)
        # Explicit design dimensions replace the old aggregate geometry hash.
        # These literals make an unintended change reviewable by its meaning.
        selected = {
            "DISPLAY_SIZE": 454, "DIAL_CENTER": 227,
            "HYBRID_DATE_TOP": 145, "HYBRID_DATE_BOTTOM": 170, "HYBRID_DATE_WIDTH": 222,
            "HYBRID_DAY_LEFT": 346, "HYBRID_DAY_TOP": 208, "HYBRID_DAY_BOTTOM": 246,
            "HYBRID_DAY_WIDTH": 46, "HYBRID_CLOCK_LEFT": 165, "HYBRID_CLOCK_TOP": 238,
            "HYBRID_CLOCK_BOTTOM": 280, "HYBRID_CLOCK_WIDTH": 124,
            "HYBRID_DATA_TOP": 282, "HYBRID_DATA_BOTTOM": 338, "HYBRID_DATA_WIDTH": 110,
            "HYBRID_LEFT_X": 109, "HYBRID_RIGHT_X": 235,
            "HYBRID_CHARGE_TOP": 176, "HYBRID_CHARGE_BOTTOM": 206, "HYBRID_CHARGE_WIDTH": 118,
            "HYBRID_MARKER_CENTER": 155, "HYBRID_CIRCLE_RADIUS": 14, "HYBRID_CIRCLE_INNER": 11,
            "HYBRID_BATON_INNER": 137, "HYBRID_BATON_OUTER": 166, "HYBRID_BATON_HALF": 8,
            "HYBRID_TRIANGLE_INNER": 119, "HYBRID_TRIANGLE_OUTER": 164, "HYBRID_TRIANGLE_HALF": 17,
            "HYBRID_TICK_OUTER": 174, "HYBRID_TICK_INNER": 169,
            "HYBRID_HOUR_DISC_CENTER": 100, "HYBRID_HOUR_DISC_RADIUS": 17, "HYBRID_HOUR_DISC_INNER": 14,
            "HYBRID_HOUR_STEM_INNER": -18, "HYBRID_HOUR_STEM_OUTER": 86, "HYBRID_HOUR_STEM_HALF": 6,
            "HYBRID_HOUR_TIP_BASE": 114, "HYBRID_HOUR_TIP_HALF": 8, "HYBRID_HOUR_TIP_LENGTH": 131,
            "HYBRID_MINUTE_LENGTH": 160, "HYBRID_MINUTE_HALF": 7, "HYBRID_MINUTE_TAIL_HALF": 4,
            "HYBRID_BEZEL_OUTER": 226, "HYBRID_BEZEL_INNER": 177, "HYBRID_BEZEL_RADIUS": 203,
        }
        self.assertEqual({key: self.constants[key] for key in selected}, selected)
        colors = dict(re.findall(r"^    const ([A-Z_]+) = (0x[0-9A-Fa-f]+);$", self.palette, re.MULTILINE))
        self.assertEqual(digest(json.dumps(colors, sort_keys=True, separators=(",", ":"))),
                         "5d5057109c8ee4a19631011619e2606eb099ebcd6cf796da5c00335a9dd9f19e")

    def test_intersection_oracle_includes_containment_and_excludes_disjoint_shapes(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        for box in ((2, 2, 4, 4), (-1, -1, 11, 11), (10, 3, 12, 7)):
            self.assertTrue(polygon_intersects_box(square, box))
        self.assertFalse(polygon_intersects_box(square, (11, 2, 12, 4)))
        self.assertFalse(polygon_intersects_box([(0, 0), (10, 0), (0, 10)], (8, 8, 9, 9)))
        self.assertTrue(circle_intersects_box((0, 0), 5, (3, 4, 6, 8)))
        self.assertFalse(circle_intersects_box((0, 0), 5, (4, 4, 6, 8)))
        # Cardinal targets independently guard rotation, time units and rounding.
        for total, expected in ((0, (227, 67)), (15, (387, 227)), (30, (227, 387)), (45, (67, 227))):
            self.assertEqual(hand_geometry(self.constants, total)[0]["minute"][2], expected)

    def test_new_full_cycle_locates_crossing_cases_and_an_unobstructed_control(self):
        crossings = crossing_report(self.constants)
        self.assertIn(0, crossings["calendar"])       # 12:00, a geometric inspection case, not a new observation
        self.assertIn(390, crossings["weather"])    # 06:30
        self.assertNotIn(390, crossings["battery"])  # Battery moved above the pivot.
        self.assertIn(0, crossings["battery"])
        self.assertIn(415, crossings["calendar"])   # 18:55 is 06:55 on the analog dial
        self.assertIn(415, crossings["weather"])
        for name, totals in crossings.items():
            with self.subTest(band=name):
                self.assertGreater(len(totals), 0)
                self.assertLess(len(totals), 720)
                self.assertNotIn(195, totals)        # 03:15 control
                self.assertEqual(totals, sorted(set(totals)))
        # This re-evaluates the new bands across every minute. Historical
        # screenshots do not become new observations, and band intersections
        # do not count hidden glyph pixels or prove the new painter order.

    def test_single_row_with_one_pixel_separator_stays_inside_its_fitted_band(self):
        c = self.constants
        for name in ("DATE", "CHARGE"):
            width, top, bottom = (c[f"HYBRID_{name}_{key}"] for key in ("WIDTH", "TOP", "BOTTOM"))
            x = (c["DISPLAY_SIZE"] - width) // 2
            for glyph_width in range(1, width - 3):
                left = int(c["DIAL_CENTER"] - glyph_width / 2) - 1
                self.assertGreaterEqual(left, x)
                self.assertLessEqual(left + glyph_width + 2, x + width)
                for glyph_height in range(1, bottom - top - 3):
                    y = int(top + (bottom - top - glyph_height) / 2)
                    self.assertGreaterEqual(y - 1, top)
                    self.assertLessEqual(y + glyph_height + 1, bottom)

    def test_two_rows_with_one_pixel_separators_fit_with_truthful_status_gap(self):
        c = self.constants
        top, bottom, width = (c["HYBRID_DATA_" + key] for key in ("TOP", "BOTTOM", "WIDTH"))
        for side in ("LEFT", "RIGHT"):
            x = c[f"HYBRID_{side}_X"]
            center = int(x + width / 2)
            for glyph_width in range(1, width - 1):
                left = int(center - glyph_width / 2) - 1
                self.assertGreaterEqual(left, x)
                self.assertLessEqual(left + glyph_width + 2, x + width)
            for value_height in range(1, bottom - top - 3):
                for detail_height in range(1, bottom - top - value_height - 3):
                    total = value_height + detail_height + 2
                    y = int(top + (bottom - top - total) / 2)
                    detail_top = y + value_height + 2
                    self.assertGreaterEqual(y - 1, top)
                    self.assertEqual(detail_top - (y + value_height), 2)
                    self.assertLessEqual(detail_top + detail_height + 1, bottom)
        # This checks all positive integer sizes admitted by the width/height
        # inequalities. Actual target font availability and effective enlargement
        # still require SDK metrics and visual inspection.


if __name__ == "__main__":
    unittest.main()
