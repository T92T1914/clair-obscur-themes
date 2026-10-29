"""Declared mapping availability, without PNG preparation or device queries."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from themeforge import android_iconpack
from themeforge.icon_availability import mapping_availability
from themeforge.icons import icon_catalog


def encoded(document):
    return (json.dumps(document, sort_keys=True, indent=2) + "\n").encode("utf-8")


def app(identifier, package):
    return {"id": identifier, "kind": "app", "label": identifier, "android_package": package}


def function(identifier):
    return {"id": identifier, "kind": "function", "label": identifier}


def mapping(identifier, package, activity):
    component = f"ComponentInfo{{{package}/{activity}}}"
    return {"icon_id": identifier, "android_package": package, "activity": activity,
            "component": component, "source_lines": [7], "source_components": [component],
            "source_types": ["item"]}


class CanonicalMappingAvailabilityTests(unittest.TestCase):
    def test_current_declarations_are_separate_from_artwork_and_device_coverage(self):
        catalog = icon_catalog()
        path = android_iconpack.COMPONENTS
        captured = path.read_bytes()
        result = mapping_availability(catalog, path, captured)
        self.assertEqual(set(result), {row["id"] for row in catalog})
        self.assertEqual(len(result), 300)
        apps = [result[row["id"]] for row in catalog if row["kind"] == "app"]
        functions = [result[row["id"]] for row in catalog if row["kind"] == "function"]
        self.assertEqual((sum(row.included for row in apps), sum(row.included for row in functions)),
                         (264, 13))
        self.assertEqual(sum(row.included for row in result.values()), 277)
        self.assertEqual(sum(not row.included for row in result.values()), 23)
        self.assertEqual(sum(row.exact_component_count for row in result.values()), 1354)
        for row in result.values():
            self.assertIs(type(row.included), bool)
            self.assertIs(type(row.exact_component_count), int)
            self.assertIsInstance(row.packages, tuple)
        self.assertTrue(result["google-chrome"].included)
        self.assertTrue(result["slack"].included)
        self.assertEqual(result["slack"].packages, ("com.Slack",))
        self.assertFalse(result["us-bank"].included)
        self.assertTrue(result["phone"].included)
        self.assertFalse(result["browser"].included)
        self.assertFalse(result["calendar"].included)
        self.assertEqual(path.read_bytes(), captured)


class MappingAvailabilityFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="clair-obscur-availability-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "components.json"
        self.catalog = [app("main-app", "com.example.main"),
                        app("beta-app", "com.example.main.beta"),
                        function("phone"), function("browser")]
        self.table = {"schema_version": 1, "source": copy.deepcopy(android_iconpack.COMPONENT_SOURCE),
                      "generic_packages": {"phone": ["com.example.phone"],
                                           "browser": ["com.example.browser"]},
                      "mappings": [mapping("main-app", "com.example.main", "com.example.main.Launcher"),
                                   mapping("main-app", "com.example.main", "vendor.alias.Entry-default"),
                                   mapping("phone", "com.example.phone", "com.example.phone.Dialer")]}
        self.canonical = patch.object(android_iconpack, "COMPONENTS", self.path)
        self.canonical.start()
        self.addCleanup(self.canonical.stop)
        self.write_table()

    def write_table(self):
        payload = encoded(self.table)
        self.path.write_bytes(payload)
        return payload

    def availability(self, *, captured=None, catalog=None, path=None):
        return mapping_availability(self.catalog if catalog is None else catalog,
                                    self.path if path is None else path,
                                    self.path.read_bytes() if captured is None else captured)

    def test_aliases_are_counted_but_a_package_hint_without_rows_is_manual(self):
        result = self.availability()
        self.assertTrue(result["main-app"].included)
        self.assertEqual(result["main-app"].exact_component_count, 2)
        self.assertEqual(result["main-app"].packages, ("com.example.main",))
        for identifier in ("beta-app", "browser"):
            with self.subTest(identifier=identifier):
                self.assertFalse(result[identifier].included)
                self.assertEqual(result[identifier].exact_component_count, 0)
                self.assertEqual(result[identifier].packages, ())

    def test_a_prefix_or_beta_package_does_not_upgrade_the_primary_app(self):
        self.table["mappings"] = [mapping("beta-app", "com.example.main.beta", "beta.Launcher"),
                                  mapping("phone", "com.example.phone", "phone.Launcher")]
        self.write_table()
        result = self.availability()
        self.assertFalse(result["main-app"].included)
        self.assertEqual(result["main-app"].exact_component_count, 0)
        self.assertTrue(result["beta-app"].included)
        self.assertEqual(result["beta-app"].packages, ("com.example.main.beta",))

    def test_generic_row_does_not_upgrade_named_owner_or_disappear_from_function(self):
        self.table["generic_packages"]["browser"] = ["com.example.main"]
        self.table["mappings"] = [mapping("browser", "com.example.main", "generic.BrowserAlias"),
                                  mapping("phone", "com.example.phone", "phone.Launcher")]
        self.write_table()
        result = self.availability()
        self.assertFalse(result["main-app"].included)
        self.assertEqual(result["main-app"].packages, ())
        self.assertTrue(result["browser"].included)
        self.assertEqual(result["browser"].exact_component_count, 1)
        self.assertEqual(result["browser"].packages, ("com.example.main",))

    def test_generic_counts_keep_distinct_packages_and_all_aliases(self):
        self.table["generic_packages"]["browser"] = ["com.example.browser", "com.example.second"]
        self.table["mappings"].extend([
            mapping("browser", "com.example.second", "second.One"),
            mapping("browser", "com.example.browser", "browser.One"),
            mapping("browser", "com.example.second", "second.Two")])
        self.write_table()
        result = self.availability()["browser"]
        self.assertTrue(result.included)
        self.assertEqual(result.exact_component_count, 3)
        self.assertIsInstance(result.packages, tuple)
        self.assertEqual(len(result.packages), 2)
        self.assertEqual(set(result.packages), {"com.example.browser", "com.example.second"})

    def test_wrong_primary_package_or_case_is_not_a_valid_mapping(self):
        for package in ("com.example.main.beta", "com.Example.main"):
            self.table["mappings"][0] = mapping("main-app", package, "vendor.Launcher")
            self.write_table()
            with self.subTest(package=package), self.assertRaisesRegex(ValueError, "package differs"):
                self.availability()

    def test_conflicting_component_is_not_resolved_by_named_priority(self):
        self.table["generic_packages"]["browser"] = ["com.example.main"]
        self.table["mappings"].append(mapping("browser", "com.example.main", "com.example.main.Launcher"))
        self.write_table()
        with self.assertRaisesRegex(ValueError, "Repeated or conflicting"):
            self.availability()

    def test_unavailable_or_empty_table_is_not_reported_as_valid_zero_coverage(self):
        captured = self.path.read_bytes()
        with self.assertRaises((ValueError, OSError)):
            self.availability(path=self.root / "missing.json", captured=captured)
        self.table["mappings"] = []
        self.write_table()
        with self.assertRaisesRegex(ValueError, "bounded exact component"):
            self.availability()

    def test_malformed_json_and_wrong_source_do_not_become_zero_coverage(self):
        for payload in (b"", b"{", b'{"schema_version": 1, "schema_version": 1}', b'{"schema_version": NaN}'):
            self.path.write_bytes(payload)
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.availability(captured=payload)
        self.table["source"]["revision"] = "0" * 40
        self.write_table()
        with self.assertRaisesRegex(ValueError, "component source|table schema"):
            self.availability()

    def test_changed_source_snapshot_is_refused_even_when_new_table_is_valid(self):
        captured = self.path.read_bytes()
        self.table["mappings"].append(mapping("beta-app", "com.example.main.beta", "beta.Launcher"))
        self.write_table()
        # The new file and patched canonical table agree. Only the source-snapshot
        # binding can distinguish this from an ordinary valid additional row.
        with self.assertRaises(ValueError):
            self.availability(captured=captured)

    def test_noncanonical_input_is_refused_even_with_its_own_captured_bytes(self):
        alternate = copy.deepcopy(self.table)
        alternate["mappings"].append(mapping("beta-app", "com.example.main.beta", "beta.Launcher"))
        path = self.root / "alternate.json"
        path.write_bytes(encoded(alternate))
        with self.assertRaisesRegex(ValueError, "reviewed canonical table"):
            self.availability(path=path, captured=path.read_bytes())

    def test_invalid_catalogue_shapes_and_duplicate_ids_fail_clearly(self):
        invalid = [None, {}, "catalog", [], [None],
                   self.catalog + [copy.deepcopy(self.catalog[0])],
                   [app("main-app", None)], [app("main-app", "com.example..main")],
                   [{"id": "main-app", "kind": "unknown", "android_package": "com.example.main"}]]
        for catalog in invalid:
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                mapping_availability(catalog, self.path, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
