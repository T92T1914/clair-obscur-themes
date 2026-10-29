"""Bind the reviewed five-app art direction while preserving accepted artwork."""

import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET

from themeforge import icons
from themeforge.build import _zip_bytes


NS = "{http://www.w3.org/2000/svg}"
# Literal identities from the actually compared original selected SVGs, including
# the independently reviewed Southwest seam correction. No private files are
# required by these portable regression tests.
SELECTED = {
    "Clair/fly-delta.svg": "ea18286b2f67917030829df83192b7545ed3593f2347ecb4da4fbf91e342b044",
    "Obscur/fly-delta.svg": "12d249822da9bd159aeeb2c77b09f99f82cf6b8c1784d31fe6cd79f4e88a4d0f",
    "Clair/american-airlines.svg": "6c36083844a4356fcd65ae7ee79c39b7728708d73836048b6fd18b7e0f91b9b8",
    "Obscur/american-airlines.svg": "5c9d07d91f2d19f598493ba33165b6babaa1cc584ad8bd60a5a962b59ce6b91b",
    "Clair/southwest-airlines.svg": "4b808b91fef5d1dfebdf2818da0a946057ce951fd0f2552881028cb0b0110665",
    "Obscur/southwest-airlines.svg": "4bbf8aef0d2b528cdc20a7dd6cfbeae56c540d3f174b52dc780d7ec1326d2c58",
    "Clair/wikipedia.svg": "ac99efb6aa80a95875da5f04f2b07ed72c83dcd4350c4883b39b00415dd087fe",
    "Obscur/wikipedia.svg": "81940baa726e5dd68a89edf43f2fa3bf728d3a36a499bd54f8795435e9c3db5b",
    "Clair/google-earth.svg": "50b6687a2c7448297f657cccef686cc526daae73399be1457d100a3ff8a17d62",
    "Obscur/google-earth.svg": "21dfd0fb5eea71dbb0d0bc7e227b897b87b440944020493da60a28212f5a9a44",
}
TARGETS = {"fly-delta", "american-airlines", "southwest-airlines", "wikipedia", "google-earth"}


class ArtDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = icons.render_icons(icons.load_icon_tokens("0.28.0"), version="0.28.0")
        cls.after = icons.render_icons(icons.load_icon_tokens("0.29.0"), version="0.29.0")

    def test_only_five_selected_drawings_change_and_590_other_svgs_stay_exact(self):
        self.assertEqual(set(icons.ART_DIRECTION_GLYPHS), TARGETS)
        self.assertEqual(set(self.before), set(self.after))
        changed = {name for name in self.after if name.endswith(".svg")
                   and self.before[name] != self.after[name]}
        self.assertEqual(changed, set(SELECTED))
        unchanged = {name for name in self.after if name.endswith(".svg")} - changed
        self.assertEqual(len(unchanged), 590)
        for appearance in ("Clair", "Obscur"):
            self.assertEqual(sum(name.startswith(appearance + "/") for name in unchanged), 295)
        for name in unchanged:
            self.assertEqual(self.before[name], self.after[name], name)

    def test_selected_full_svg_bytes_match_the_actual_reviewed_sources(self):
        for name, expected in SELECTED.items():
            self.assertEqual(hashlib.sha256(self.after[name]).hexdigest(), expected, name)
            before, after = (ET.fromstring(tree[name]) for tree in (self.before, self.after))
            self.assertEqual(before.attrib, after.attrib)
            self.assertEqual(before.find(NS + "rect").attrib, after.find(NS + "rect").attrib)
            group = after.find(NS + "g")
            self.assertEqual(group.get("stroke-width"), "16")
            self.assertEqual(group.get("stroke-linecap"), "round")
            self.assertEqual(group.get("stroke-linejoin"), "round")

    def test_counterparts_keep_the_same_geometry_and_semantic_foreground(self):
        for identifier in TARGETS:
            pair = []
            for appearance, foreground in (("Clair", "#000000"), ("Obscur", "#ffffff")):
                group = ET.fromstring(self.after[f"{appearance}/{identifier}.svg"]).find(NS + "g")
                self.assertEqual(group.get("stroke"), foreground)
                geometry = []
                for node in group:
                    attributes = dict(node.attrib)
                    for paint in ("fill", "stroke"):
                        value = attributes.get(paint)
                        if value and value.startswith("#"):
                            self.assertEqual(value, foreground)
                            attributes[paint] = "foreground"
                    geometry.append((node.tag, attributes))
                pair.append(geometry)
            self.assertEqual(pair[0], pair[1], identifier)

    def test_corrected_seams_and_limited_serif_weight_are_retained(self):
        southwest = ET.fromstring(self.after["Obscur/southwest-airlines.svg"]).find(NS + "g")
        self.assertEqual(len(southwest), 2)
        self.assertEqual(southwest[1].get("d"),
                         "M140.508 189.985 L340.373 305.292 M143.388 257.414 L282.133 363.514")
        wikipedia = ET.fromstring(self.after["Obscur/wikipedia.svg"]).find(NS + "g")
        self.assertEqual([node.get("stroke-width") for node in wikipedia], [None, None, None, "12"])
        self.assertEqual(wikipedia.get("stroke-width"), "16")
        delta = ET.fromstring(self.after["Obscur/fly-delta.svg"]).find(NS + "g")
        self.assertEqual(len(delta), 3)
        self.assertTrue(all(node.get("fill") == "#ffffff" and node.get("stroke") == "none"
                            for node in delta))

    def test_catalogue_and_component_assignments_do_not_change(self):
        old, new = (json.loads(tree["manifest.json"]) for tree in (self.before, self.after))
        self.assertEqual(new["version"], "0.29.0")
        self.assertEqual(icons.VERSIONS[-4:], ("0.28.0", "0.29.0", "0.30.0", "0.31.0"))
        for field in ("catalog", "catalog_date", "catalog_scope", "functions", "palette_variant",
                      "token_schema", "token_version", "tile", "stroke_width"):
            self.assertEqual(old[field], new[field], field)
        self.assertEqual(len(new["catalog"]), 300)
        self.assertEqual(sum(row["kind"] == "app" for row in new["catalog"]), 276)
        mapping_bytes = (icons.ROOT / "android/iconpack/components.json").read_bytes()
        self.assertEqual(hashlib.sha256(mapping_bytes).hexdigest(),
                         "f37fcd87858500b6e389143194fdf67c74eaea8c42f10b6d4098da37b508c8a2")
        self.assertEqual(len(json.loads(mapping_bytes)["mappings"]), 1354)

    def test_current_artwork_keeps_monochrome_admission_and_accepted_028_archive(self):
        wrong = copy.deepcopy(icons.load_icon_tokens("0.29.0"))
        wrong["themes"]["Clair"]["text"] = "#111111"
        with self.assertRaisesRegex(ValueError, "opposite pure black and white"):
            icons.render_icons(wrong, version="0.29.0")
        archive = _zip_bytes({**self.before, "LICENSE.txt": (icons.ROOT / "LICENSE").read_bytes()})
        self.assertEqual(hashlib.sha256(archive).hexdigest(),
                         "fe021dff47c0927fcd8098f8da688309d734b40317d72d6ae876f3c4d36dd92a")
