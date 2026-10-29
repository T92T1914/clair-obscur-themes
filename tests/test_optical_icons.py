"""Fixed selected artwork identities and the bounded dated launcher admission."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from themeforge import android_iconpack as pack, icons
from themeforge.icon_availability import mapping_availability


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


class OpticalIconRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((Path(__file__).parent / "fixtures/icon-optical-0.32.json").read_bytes())
        cls.before = icons.render_icons(icons.load_icon_tokens("0.31.0"), version="0.31.0")
        cls.after = icons.render_icons(icons.load_icon_tokens("0.32.0"), version="0.32.0")

    def test_only_three_selected_original_drawings_change(self):
        expected = self.fixture["svg_sha256"]
        self.assertEqual(set(icons.OPTICAL_GLYPHS), set(self.fixture["changed_ids"]))
        changed = {name for name in self.after if name.endswith(".svg") and self.after[name] != self.before[name]}
        self.assertEqual(changed, set(expected))
        for name, wanted in expected.items():
            self.assertEqual(digest(self.after[name]), wanted, name)
        retained = {name for name in self.after if name.endswith(".svg")} - changed
        self.assertEqual(len(retained), 594)
        for appearance in ("Clair", "Obscur"):
            for identifier in ("coinbase", "coursera", "chime", "contacts", "asus-router"):
                self.assertIn(f"{appearance}/{identifier}.svg", retained)
        old, new = (json.loads(tree["manifest.json"]) for tree in (self.before, self.after))
        self.assertEqual(new["version"], "0.32.0")
        self.assertEqual(new["catalog"], old["catalog"])
        self.assertEqual(new["functions"], old["functions"])
        self.assertEqual(len(new["catalog"]), 300)

    def test_the_complete_031_renderer_identity_is_retained(self):
        self.assertEqual(digest(self.before["manifest.json"]), self.fixture["retained_031_manifest_sha256"])
        pairs = "".join(name + "\0" + digest(payload) + "\n"
                        for name, payload in sorted(self.before.items())).encode()
        self.assertEqual(digest(pairs), self.fixture["retained_031_tree_sha256"])
        self.assertEqual(icons.VERSIONS[:31], tuple(f"0.{number}.0" for number in range(1, 32)))


class DatedDominosAdmissionTests(unittest.TestCase):
    def test_exact_observation_preserves_prefix_queries_and_choice_availability(self):
        path = pack.COMPONENTS
        captured = path.read_bytes()
        table = json.loads(captured)
        self.assertEqual(len(table["mappings"]), 1355)
        self.assertEqual(digest(json.dumps(table["mappings"][:1354], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "af2fe774168d48ab21634202263d37662947df861fa24e2e675b2c7bd13f913e")
        row = table["mappings"][-1]
        self.assertEqual(row, {"icon_id": "dominos", "android_package": "com.dominospizza",
                               "activity": "com.dominospizza.SplashScreenActivity",
                               "component": "ComponentInfo{com.dominospizza/com.dominospizza.SplashScreenActivity}",
                               "source_kind": "observed-launcher", "observed_on": "2026-10-29"})
        catalog = json.loads(icons.render_icons(icons.load_icon_tokens())["manifest.json"])["catalog"]
        result = mapping_availability(catalog, path, captured)
        self.assertEqual(result["dominos"].exact_component_count, 6)
        self.assertEqual(sum(value.included for value in result.values()), 277)
        self.assertEqual(sum(not value.included for value in result.values()), 23)
        with tempfile.TemporaryDirectory(prefix="clair-obscur-dated-alias-") as directory:
            fixture = Path(directory) / "components.json"
            fixture.write_bytes(captured)
            with patch.object(pack, "COMPONENTS", fixture):
                current = pack._components(fixture, catalog)
                fixture.write_text(json.dumps({**table, "mappings": table["mappings"][:1354]}), encoding="utf-8")
                previous = pack._components(fixture, catalog)
        self.assertEqual(current[0]["generic_packages"], previous[0]["generic_packages"])
        packages = [{"package": item["android_package"], "label": item["label"], "id": item["id"]}
                    for item in catalog if item["kind"] == "app"]
        seen = {item["package"] for item in packages}
        for item in catalog:
            for package in table["generic_packages"].get(item["id"], []):
                if package not in seen:
                    packages.append({"package": package, "label": item["label"], "id": item["id"]})
                    seen.add(package)
        self.assertEqual(len(packages), 290)
        self.assertEqual(digest(json.dumps([item["package"] for item in packages], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "6cbcc4b748aafdb89ae2c1e1e68e8d573ed5daf50ad5039666eb975ed2555bd2")
        self.assertEqual(path.read_bytes(), captured)

    def test_observed_alias_rejects_wrong_owner_duplicate_and_unqualified_date(self):
        table = json.loads(pack.COMPONENTS.read_bytes())
        catalog = json.loads(icons.render_icons(icons.load_icon_tokens())["manifest.json"])["catalog"]
        faults = (("owner", {"icon_id": "pinterest"}), ("date", {"observed_on": "2026-02-30"}),
                  ("guessed-relative", {"activity": ".SplashScreenActivity"}))
        with tempfile.TemporaryDirectory(prefix="clair-obscur-dated-negative-") as directory:
            fixture = Path(directory) / "components.json"
            with patch.object(pack, "COMPONENTS", fixture):
                for label, changes in faults:
                    changed = copy.deepcopy(table)
                    changed["mappings"][-1].update(changes)
                    fixture.write_text(json.dumps(changed), encoding="utf-8")
                    with self.subTest(fault=label), self.assertRaises(ValueError):
                        pack._components(fixture, catalog)
                table["mappings"].append(copy.deepcopy(table["mappings"][-1]))
                fixture.write_text(json.dumps(table), encoding="utf-8")
                with self.assertRaises(ValueError):
                    pack._components(fixture, catalog)


if __name__ == "__main__":
    unittest.main()
