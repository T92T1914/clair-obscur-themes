"""Bind the compared identity drawings without turning design review into usability proof."""

import hashlib
import json
import unittest
import xml.etree.ElementTree as ET

from themeforge import icons
from themeforge.build import _zip_bytes


NS = "{http://www.w3.org/2000/svg}"
# Literal SVG identities captured after matching the selected source to the
# independently inspected concept geometry. They are not computed by the test.
SELECTED = {
    "Clair/claude.svg": "c4bbebf5b19c39405b5bbac44f97664b1eb7d93a3d6dba5123891dbc74e83f80",
    "Obscur/claude.svg": "eb9e82168935fc0744df5865afbf604b29322f9fe1df331a37c443815a0247ac",
    "Clair/perplexity.svg": "685d6aa1d16eb53b234c313bf6734822f192f275f9c9f7c05e9114389cb034d2",
    "Obscur/perplexity.svg": "db0e4441ee9caaddf9d268614f8ec0dffe92b16083e0dca6bb2e4893b1b6235d",
}


class IconIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = icons.render_icons(icons.load_icon_tokens("0.27.0"), version="0.27.0")
        cls.after = icons.render_icons(icons.load_icon_tokens("0.28.0"), version="0.28.0")

    def test_only_selected_two_drawings_change_and_298_per_appearance_stay_exact(self):
        self.assertEqual(set(icons.IDENTITY_GLYPHS), {"claude", "perplexity"})
        self.assertEqual(set(self.after), set(self.before))
        changed = {name for name in self.after if name.endswith(".svg")
                   and self.after[name] != self.before[name]}
        self.assertEqual(changed, set(SELECTED))
        for appearance in ("Clair", "Obscur"):
            unchanged = [name for name in self.after if name.startswith(appearance + "/")
                         and name.endswith(".svg") and name not in changed]
            self.assertEqual(len(unchanged), 298)
            for name in unchanged:
                self.assertEqual(self.after[name], self.before[name], name)
        old, new = (json.loads(tree["manifest.json"]) for tree in (self.before, self.after))
        self.assertEqual(new["version"], "0.28.0")
        self.assertEqual(old["catalog"], new["catalog"])
        self.assertEqual(old["functions"], new["functions"])
        self.assertEqual(len(new["catalog"]), 300)

    def test_reviewed_shapes_keep_labels_tile_palette_stroke_and_paired_geometry(self):
        for name, expected in SELECTED.items():
            self.assertEqual(hashlib.sha256(self.after[name]).hexdigest(), expected, name)
            before, after = (ET.fromstring(tree[name]) for tree in (self.before, self.after))
            self.assertEqual(before.attrib, after.attrib)
            self.assertEqual(before.find(NS + "rect").attrib, after.find(NS + "rect").attrib)
            self.assertEqual(after.find(NS + "g").get("stroke-width"), "16")
        for identifier in ("claude", "perplexity"):
            groups = []
            for appearance in ("Clair", "Obscur"):
                group = ET.fromstring(self.after[f"{appearance}/{identifier}.svg"]).find(NS + "g")
                expected = "#000000" if appearance == "Clair" else "#ffffff"
                self.assertEqual(group.get("stroke"), expected)
                groups.append([(node.tag, {k: v for k, v in node.attrib.items()
                                          if k not in ("fill", "stroke")}) for node in group])
            self.assertEqual(groups[0], groups[1])

    def test_selected_cues_retain_open_scaffold_and_full_radial_extent(self):
        group = ET.fromstring(self.after["Obscur/perplexity.svg"]).find(NS + "g")
        self.assertEqual(len(group), 3)
        self.assertEqual(group[0].get("d"), "M256 120 V392")
        self.assertEqual(group.get("fill"), "none")
        self.assertEqual(group[1].get("d"), "M176 144 L256 208 L336 144 V368 L256 304 L176 368 Z")
        claude = ET.fromstring(self.after["Obscur/claude.svg"]).find(NS + "g")
        self.assertEqual(len(claude), 13)
        self.assertEqual(claude[0].tag, NS + "circle")
        self.assertEqual(claude[0].attrib, {"cx": "256", "cy": "256", "r": "32",
                                          "fill": "#ffffff", "stroke": "none"})
        self.assertTrue(all(node.tag == NS + "path" and node.get("d").count("L") == 1
                            for node in list(claude)[1:]))

    def test_accepted_027_archive_remains_exact(self):
        archive = _zip_bytes({**self.before, "LICENSE.txt": (icons.ROOT / "LICENSE").read_bytes()})
        self.assertEqual(hashlib.sha256(archive).hexdigest(),
                         "96fc1be033628ec1df75d8fd6302f6ede55e65ac617719a1742c1e41ad673592")
