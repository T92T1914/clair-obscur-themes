"""Versioned icon refinements retain old bytes and clear measured outline collisions."""

import copy
import hashlib
import json
import math
import re
import unittest
import xml.etree.ElementTree as ET

from themeforge import icons


NS = "{http://www.w3.org/2000/svg}"
REFINED_IDS = {
    "ace-hardware", "dollar-general", "fandom", "google-messages",
    "google-translate", "myfitnesspal", "wallpaper-engine", "webtoon",
}

# Canonical sorted path -> SHA256 maps captured from the accepted renderer before
# the refinement. These constants cover every SVG and manifest in each version.
# No machine-local review file is required to execute the preservation test.
HISTORICAL_TREE_DIGESTS = {
    "0.1.0": "72c06eba9b118e2312b150523b5ee2016c11c5d060f2a20ddff07dc736df83e4",
    "0.2.0": "801bd46be5348b7baa88da1a46a514af2312c2e9e04eafb0ec5c1f60e69c96ec",
    "0.3.0": "5a6562768e180d315223ce1588266f596a41c8d46f7e0ef8a69c7e683cae9e90",
    "0.4.0": "f8fc0a2988b946c1eb5b3cf358f556fa81df1ab6d58b4c50069ab280d974f016",
    "0.5.0": "fe5b88f5422aee6c2ab91fd87fe62650618a851e449333fc351eefd1a473e5ed",
    "0.6.0": "47b0f8f653700de375161122866ef9024ace600d688990dfe3393dc841dbe099",
    "0.7.0": "b88a14f7f37e6910e66ad82e81bdf7871158263e1999cdd0e7333989d88b3d17",
    "0.8.0": "56282859ef5a4f1c8346e1494b700a93df06367bd9ea4d0d123fe31ebe66591f",
    "0.9.0": "b8a7a9e7f62ac7aa945580cbeef5629cdbdcdcc40c10da6f82ceaeaa1afcb07b",
    "0.10.0": "afee5c70bf5146b3b86450befc011f701145e1e22ac5ee26679678fd9031752e",
    "0.11.0": "3f339b04c6095804dd733b247dfa4c90312e1cddfcae1b6addeee419644015ce",
    "0.12.0": "9a1eb90c388a9da13bfd5dbfb53d254ab02b21a75c0d73ef9299c5cd7a93be0b",
    "0.13.0": "6ac07e375a480994bb897784ecf9fc68a049945c4a8d89d28338bd749a0f661c",
    "0.14.0": "73ceefa9f86648b74d1c0b75276b08c95e71542744630f654354f783977ce2bb",
    "0.15.0": "c833741df8dba45f5fec21df3dd561b64eb7431c56ad61fc81de830c106015b1",
    "0.16.0": "9c739b1cc6848aace60d9ad978283755d03270d9f72eb4ef8fa71a91c870ae45",
    "0.17.0": "3bec6b354f1d35d8cfedfa8a2f6dfaafbca767de64bd327343f4909708516071",
}


def _geometry(payload):
    root = ET.fromstring(payload)
    root.attrib.pop("aria-label", None)
    for element in root.iter():
        for attribute in ("fill", "stroke"):
            if re.fullmatch(r"#[0-9a-fA-F]{6}", element.get(attribute, "")):
                element.attrib.pop(attribute)
    return ET.tostring(root)


def _group(files, identifier):
    return ET.fromstring(files[f"Obscur/{identifier}.svg"]).find(NS + "g")


def _path_segments(data):
    """Read the small absolute M/L/H/V/Q/C/Z vocabulary used by these drawings.

    Curves are flattened for outline clearance checks, not treated as their
    control hulls. Straight segments and closed subpaths retain exact endpoints.
    """
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", data)
    index = 0
    point = start = (0.0, 0.0)
    segments = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            segments.append((point, start))
            point = start
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6}
        if command not in counts:
            raise AssertionError(f"Unqualified refinement path command: {command}")
        count = counts[command]
        values = [float(value) for value in tokens[index:index + count]]
        if len(values) != count:
            raise AssertionError("Incomplete refinement SVG path")
        index += count
        if command in ("M", "L"):
            end = tuple(values)
        elif command == "H":
            end = (values[0], point[1])
        elif command == "V":
            end = (point[0], values[0])
        else:
            controls = [point, *zip(values[::2], values[1::2])]
            previous = point
            degree = len(controls) - 1
            for step in range(1, 129):
                t = step / 128
                following = tuple(sum(
                    math.comb(degree, k) * (1 - t) ** (degree - k) * t ** k * control[axis]
                    for k, control in enumerate(controls)) for axis in (0, 1))
                segments.append((previous, following))
                previous = following
            point = controls[-1]
            continue
        if command == "M":
            start = end
        else:
            segments.append((point, end))
        point = end
    return segments


def _point_segment_distance(point, segment):
    start, end = segment
    delta = (end[0] - start[0], end[1] - start[1])
    length_squared = delta[0] ** 2 + delta[1] ** 2
    if not length_squared:
        return math.dist(point, start)
    t = max(0, min(1, ((point[0] - start[0]) * delta[0]
                      + (point[1] - start[1]) * delta[1]) / length_squared))
    nearest = (start[0] + t * delta[0], start[1] + t * delta[1])
    return math.dist(point, nearest)


def _segment_distance(first, second):
    a, b = first
    c, d = second

    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if (cross(a, b, c) * cross(a, b, d) <= 0
            and cross(c, d, a) * cross(c, d, b) <= 0
            and max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
            and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))):
        return 0.0
    return min(_point_segment_distance(a, second), _point_segment_distance(b, second),
               _point_segment_distance(c, first), _point_segment_distance(d, first))


def _segments(element):
    if element.tag == NS + "path":
        return _path_segments(element.get("d"))
    if element.tag == NS + "rect":
        # Only the straight edges relevant to these regressions are needed.
        # Trimming rounded corners keeps the test from inventing square corners.
        x, y, width, height = (float(element.get(name)) for name in ("x", "y", "width", "height"))
        radius = float(element.get("rx", "0"))
        return [((x + radius, y), (x + width - radius, y)),
                ((x + width, y + radius), (x + width, y + height - radius)),
                ((x + radius, y + height), (x + width - radius, y + height)),
                ((x, y + radius), (x, y + height - radius))]
    raise AssertionError(f"Unexpected outline shape: {element.tag}")


def _outline_gap(first, second, stroke_width):
    return min(_segment_distance(a, b) for a in _segments(first)
               for b in _segments(second)) - stroke_width


class IconRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = icons.load_icon_tokens("0.18.0")
        cls.old = icons.render_icons(cls.document, version="0.17.0")
        cls.current = icons.render_icons(cls.document, version="0.18.0")

    def test_all_historical_versions_preserve_every_svg_and_manifest_byte(self):
        for version, expected in HISTORICAL_TREE_DIGESTS.items():
            with self.subTest(version=version):
                files = icons.render_icons(icons.load_icon_tokens(version), version=version)
                hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
                digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                self.assertEqual(digest, expected)

    def test_only_eight_drawings_change_in_both_appearances(self):
        old_manifest = json.loads(self.old["manifest.json"])
        current_manifest = json.loads(self.current["manifest.json"])
        self.assertEqual(current_manifest["version"], "0.18.0")
        self.assertEqual(current_manifest["catalog"], old_manifest["catalog"])
        self.assertEqual(current_manifest["functions"], old_manifest["functions"])
        self.assertEqual(len(current_manifest["catalog"]), 281)
        self.assertEqual(set(self.current), set(self.old))
        changed = {name for name in self.current if name.endswith(".svg")
                   and _geometry(self.current[name]) != _geometry(self.old[name])}
        self.assertEqual(changed, {f"{appearance}/{identifier}.svg"
                                  for appearance in ("Clair", "Obscur") for identifier in REFINED_IDS})
        for name in self.current:
            if name.endswith(".svg") and name not in changed:
                self.assertEqual(self.current[name], self.old[name], name)

    def test_refined_drawings_keep_black_white_palette_geometry_parity_and_stroke(self):
        for identifier in REFINED_IDS:
            with self.subTest(identifier=identifier):
                self.assertEqual(_geometry(self.current[f"Clair/{identifier}.svg"]),
                                 _geometry(self.current[f"Obscur/{identifier}.svg"]))
                for appearance in ("Clair", "Obscur"):
                    root = ET.fromstring(self.current[f"{appearance}/{identifier}.svg"])
                    group = root.find(NS + "g")
                    self.assertGreaterEqual(len(group), 1)
                    self.assertEqual(group.get("stroke-width"), "16")
                    self.assertEqual(group.get("stroke-linecap"), "round")
                    self.assertEqual(group.get("stroke-linejoin"), "round")
                    colors = {value for element in root.iter() for key, value in element.attrib.items()
                              if key in ("fill", "stroke") and value != "none"}
                    self.assertEqual(colors, {"#ffffff", "#000000"})

    def test_removed_tiny_rivets_leave_the_original_tool_and_storefront(self):
        for identifier in ("ace-hardware", "dollar-general"):
            with self.subTest(identifier=identifier):
                old = _group(self.old, identifier)
                current = _group(self.current, identifier)
                self.assertEqual(len(old.findall(NS + "circle")), 1)
                self.assertEqual(current.findall(NS + "circle"), [])
                old_without_rivet = copy.deepcopy(old)
                old_without_rivet.remove(old_without_rivet.find(NS + "circle"))
                # Compare geometry attributes; serialization indentation is irrelevant.
                self.assertEqual([(e.tag, e.attrib) for e in current],
                                 [(e.tag, e.attrib) for e in old_without_rivet])

    def test_messages_rear_outline_clears_the_front_bubble(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "google-messages")
            rear, front = list(group)
            gap = _outline_gap(rear, front, float(group.get("stroke-width")))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertLessEqual(gap, 0)

    def test_translate_rear_card_and_character_clear_the_front_card(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "google-translate")
            front, rear, latin_character, rear_character = list(group)
            self.assertGreater(len(_segments(latin_character)), 0)
            for name, outline in (("rear card", rear), ("rear character", rear_character)):
                gap = _outline_gap(front, outline, float(group.get("stroke-width")))
                with self.subTest(version=label, outline=name):
                    if should_clear:
                        self.assertGreaterEqual(gap, 8)
                    else:
                        self.assertLessEqual(gap, 0)

    def test_fandom_book_and_bubble_are_separate_outlines(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "fandom")
            book, bubble = list(group)
            gap = _outline_gap(book, bubble, float(group.get("stroke-width")))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertLessEqual(gap, 0)

    def test_wallpaper_frame_and_mountain_clear_the_settings_badge(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "wallpaper-engine")
            frame, sun, mountain, badge, ticks = list(group)
            self.assertEqual(sun.tag, NS + "circle")
            self.assertGreater(len(_segments(ticks)), 0)
            self.assertEqual(badge.tag, NS + "circle")
            center = (float(badge.get("cx")), float(badge.get("cy")))
            radius = float(badge.get("r"))
            width = float(group.get("stroke-width"))
            gaps = [min(_point_segment_distance(center, segment) for segment in _segments(outline))
                    - radius - width for outline in (frame, mountain)]
            with self.subTest(version=label):
                if should_clear:
                    self.assertTrue(all(gap >= 8 for gap in gaps), gaps)
                else:
                    self.assertLessEqual(min(gaps), 0, gaps)

    def test_myfitnesspal_plate_has_clear_space_from_both_utensils(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "myfitnesspal")
            plate = group.find(NS + "circle")
            center = (float(plate.get("cx")), float(plate.get("cy")))
            radius = float(plate.get("r"))
            width = float(group.get("stroke-width"))
            gaps = [min(_point_segment_distance(center, segment) for segment in _segments(utensil))
                    - radius - width for utensil in group.findall(NS + "path")]
            self.assertEqual(len(gaps), 2)
            with self.subTest(version=label):
                if should_clear:
                    self.assertTrue(all(gap >= 8 for gap in gaps), gaps)
                else:
                    self.assertLessEqual(min(gaps), 0, gaps)

    def test_webtoon_bubble_has_clear_space_above_the_first_panel_divider(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "webtoon")
            paths = group.findall(NS + "path")
            horizontal = [segment for segment in _segments(paths[0])
                          if segment[0][1] == segment[1][1]]
            first_divider = min(horizontal, key=lambda segment: segment[0][1])
            bubble = paths[1]
            gap = min(_segment_distance(first_divider, segment) for segment in _segments(bubble))
            gap -= float(group.get("stroke-width"))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertEqual(gap, 0)


if __name__ == "__main__":
    unittest.main()
