"""Freeze reviewed drawings and keep retained artwork and assignments exact."""
import hashlib
import json
from pathlib import Path
import unittest

from themeforge import icons
from themeforge.icon_craft import CRAFT_GLYPHS

ROOT = Path(__file__).resolve().parents[1]


class CompleteIconCraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = icons.render_icons(icons.load_icon_tokens('0.29.0'), version='0.29.0')
        cls.after = icons.render_icons(icons.load_icon_tokens('0.30.0'), version='0.30.0')
        cls.pins = json.loads((ROOT / 'tests/fixtures/icon-craft-0.30.json').read_text())['selected']

    def test_exact_reviewed_pairs_and_retained_controls(self):
        self.assertEqual(len(self.pins), 184)
        self.assertEqual(set(CRAFT_GLYPHS), set(self.pins))
        changed = set()
        for name, payload in self.after.items():
            if not name.endswith('.svg'):
                continue
            appearance, filename = name.split('/')
            identifier = filename.removesuffix('.svg')
            if identifier in self.pins:
                self.assertEqual(hashlib.sha256(payload).hexdigest(), self.pins[identifier][appearance], name)
                self.assertNotEqual(payload, self.before[name], name)
                changed.add(name)
            else:
                self.assertEqual(payload, self.before[name], name)
        self.assertEqual(len(changed), 368)
        self.assertEqual(len([name for name in self.after if name.endswith('.svg')]) - len(changed), 232)

    def test_assignments_and_historical_manifest_are_preserved(self):
        old, new = [json.loads(tree['manifest.json']) for tree in (self.before, self.after)]
        self.assertEqual(new['catalog'], old['catalog'])
        self.assertEqual(new['functions'], old['functions'])
        self.assertEqual(len(new['catalog']), 300)
        self.assertEqual(sum(row['kind'] == 'app' for row in new['catalog']), 276)
        self.assertEqual(hashlib.sha256(self.before['manifest.json']).hexdigest(),
                         '5e24ec84b4f495a0da954416232c5b18ecc5933761c89e828042625f062b3723')
        self.assertEqual(new['version'], '0.30.0')


if __name__ == '__main__':
    unittest.main()
