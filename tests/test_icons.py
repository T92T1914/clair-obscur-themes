"""Original vector geometry, palette consumption and output-preservation checks."""

import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from themeforge import icons


ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "phone messages contacts camera gallery settings calendar clock files notes mail "
    "browser maps music video store wallet calculator weather health fitness "
    "voice-recorder home search"
).split()
NS = "{http://www.w3.org/2000/svg}"


def tree_snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def geometry(svg):
    root = ET.fromstring(svg)
    root.attrib.pop("aria-label", None)
    for element in root.iter():
        element.attrib.pop("fill", None)
        element.attrib.pop("stroke", None)
    return ET.tostring(root)


def path_hull(data):
    """Conservatively bound absolute line/Bezier paths by endpoints and controls."""
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", data)
    points = []
    x = y = 0
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6}
        if command not in counts:
            raise AssertionError(f"Unqualified SVG path command {command}")
        count = counts[command]
        values = [float(value) for value in tokens[index:index + count]]
        if len(values) != count:
            raise AssertionError("Incomplete SVG path")
        index += count
        if command == "H":
            x = values[0]
            points.append((x, y))
        elif command == "V":
            y = values[0]
            points.append((x, y))
        else:
            points.extend(zip(values[::2], values[1::2]))
            x, y = values[-2:]
    return points


class FunctionalIconTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))

    def test_exact_function_inventory_and_each_manifest_digest(self):
        files = icons.render_icons(self.document)
        expected = {f"{theme}/{name}.svg" for theme in ("Clair", "Obscur") for name in NAMES}
        self.assertEqual(set(files), expected | {"manifest.json"})
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["functions"], NAMES)
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["token_schema"], 1)
        self.assertEqual(manifest["token_version"], "0.1.1")
        self.assertEqual(len(manifest["files"]), 48)
        for record in manifest["files"]:
            self.assertEqual(record["path"], f'{record["appearance"]}/{record["function"]}.svg')
            payload = files[record["path"]]
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
        # Relabeling the same drawing must not count as new geometry.
        relabeled = files["Clair/phone.svg"].replace(b'aria-label="phone"', b'aria-label="messages"')
        self.assertEqual(geometry(relabeled), geometry(files["Clair/phone.svg"]))
        # The 24 meanings must not be aliases of one repeated glyph.
        self.assertEqual(len({geometry(files[f"Clair/{name}.svg"]) for name in NAMES}), 24)

    def test_palette_roles_and_geometry_are_shared_without_hardcoded_colors(self):
        files = icons.render_icons(self.document)
        for name in NAMES:
            self.assertEqual(geometry(files[f"Clair/{name}.svg"]), geometry(files[f"Obscur/{name}.svg"]))
            for theme in ("Clair", "Obscur"):
                root = ET.fromstring(files[f"{theme}/{name}.svg"])
                palette = self.document["themes"][theme]
                self.assertEqual(root.find(NS + "rect").get("fill"), palette["panel"])
                self.assertEqual(root.find(NS + "g").get("stroke"), palette["text"])
                colors = {value for element in root.iter() for key, value in element.attrib.items()
                          if key in ("stroke", "fill") and value != "none"}
                self.assertEqual(colors, {palette["panel"], palette["text"], palette["accent"]})
        changed = copy.deepcopy(self.document)
        changed["themes"]["Clair"].update(panel="#fcfbf7", text="#252525", accent="#355e77")
        changed["version"] = "2.3.4"
        updated = icons.render_icons(changed)
        for name in NAMES:
            self.assertNotEqual(updated[f"Clair/{name}.svg"], files[f"Clair/{name}.svg"])
            self.assertEqual(updated[f"Obscur/{name}.svg"], files[f"Obscur/{name}.svg"])
            self.assertEqual(geometry(updated[f"Clair/{name}.svg"]), geometry(files[f"Clair/{name}.svg"]))
        self.assertEqual(json.loads(updated["manifest.json"])["token_version"], "2.3.4")

    def test_output_is_deterministic_and_does_not_mutate_tokens(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {name: dict(reversed(list(values.items())))
                               for name, values in reversed(list(self.document["themes"].items()))}
        self.assertEqual(icons.render_icons(reordered), icons.render_icons(self.document))
        self.assertEqual(self.document, before)

    def test_svg_has_only_local_geometric_primitives_and_embedded_project_license(self):
        license_body = (ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
        allowed = {"svg", "rect", "g", "path", "line", "circle", "ellipse"}
        for path, payload in icons.render_icons(self.document).items():
            if not path.endswith(".svg"):
                continue
            self.assertIn(license_body, payload.decode())
            root = ET.fromstring(payload)
            self.assertEqual(root.get("aria-label"), Path(path).stem)
            for element in root.iter():
                self.assertIn(element.tag.removeprefix(NS), allowed)
                for key, value in element.attrib.items():
                    self.assertNotIn("href", key.lower())
                    self.assertFalse(key.lower().startswith("on"))
                    self.assertNotIn("url(", value.lower())
                    self.assertNotIn("font", key.lower())
                self.assertFalse((element.text or "").strip())

    def test_glyph_control_hulls_and_strokes_stay_inside_safe_tile_inset(self):
        for name in NAMES:
            root = ET.fromstring(icons.render_icons(self.document)[f"Clair/{name}.svg"])
            self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")),
                             ("512", "512", "0 0 512 512"))
            tile = root.find(NS + "rect")
            self.assertEqual({key: tile.get(key) for key in ("x", "y", "width", "height", "rx")},
                             {"x": "32", "y": "32", "width": "448", "height": "448", "rx": "104"})
            group = root.find(NS + "g")
            self.assertEqual(group.get("stroke-width"), "12")
            self.assertEqual(group.get("stroke-linecap"), "round")
            self.assertEqual(group.get("stroke-linejoin"), "round")
            for element in group:
                tag = element.tag.removeprefix(NS)
                values = element.attrib
                if tag == "path":
                    points = path_hull(values["d"])
                elif tag == "line":
                    points = [(float(values["x1"]), float(values["y1"])),
                              (float(values["x2"]), float(values["y2"]))]
                elif tag == "rect":
                    x, y, width, height = (float(values[key]) for key in ("x", "y", "width", "height"))
                    points = [(x, y), (x + width, y + height)]
                elif tag in ("circle", "ellipse"):
                    x, y = float(values["cx"]), float(values["cy"])
                    rx, ry = ((float(values["r"]),) * 2 if tag == "circle"
                              else (float(values["rx"]), float(values["ry"])))
                    points = [(x - rx, y - ry), (x + rx, y + ry)]
                else:
                    self.fail(f"Unqualified geometric primitive {tag}")
                self.assertTrue(points)
                for x, y in points:
                    self.assertGreaterEqual(min(x, y), 112, (name, tag, x, y))
                    self.assertLessEqual(max(x, y), 400, (name, tag, x, y))
                    self.assertGreaterEqual(min(x - 6, y - 6), 106)
                    self.assertLessEqual(max(x + 6, y + 6), 406)

    def test_fresh_build_and_check_preserve_bytes_and_refuse_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            result = icons.build_icons(self.document, output)
            self.assertEqual(len(result["files"]), 48)
            before = tree_snapshot(output)
            self.assertEqual(before, icons.render_icons(self.document))
            icons.build_icons(self.document, output, check=True)
            self.assertEqual(tree_snapshot(output), before)
            with self.assertRaisesRegex(ValueError, "new output"):
                icons.build_icons(self.document, output)
            self.assertEqual(tree_snapshot(output), before)

    def test_foreign_existing_file_folder_and_empty_folder_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("foreign", "empty"):
                output = base / name
                output.mkdir()
                if name == "foreign":
                    (output / "personal.txt").write_bytes(b"keep this exact file")
                before = tree_snapshot(output)
                for check in (False, True):
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output, check=check)
                    self.assertEqual(tree_snapshot(output), before)
            existing = base / "existing-file"
            existing.write_bytes(b"unchanged")
            with self.assertRaises(ValueError):
                icons.build_icons(self.document, existing)
            self.assertEqual(existing.read_bytes(), b"unchanged")

    def test_check_refuses_changed_missing_extra_file_and_extra_directory_without_repair(self):
        for mutation in ("changed", "missing", "extra-file", "extra-dir", "manifest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                icons.build_icons(self.document, output)
                item = output / "Clair/phone.svg"
                if mutation == "changed":
                    item.write_bytes(item.read_bytes() + b" ")
                elif mutation == "missing":
                    item.unlink()
                elif mutation == "extra-file":
                    (output / "extra.txt").write_bytes(b"preserve")
                elif mutation == "extra-dir":
                    (output / "extra").mkdir()
                else:
                    (output / "manifest.json").write_bytes(b"{}\n")
                before = tree_snapshot(output)
                with self.assertRaisesRegex(ValueError, "differs"):
                    icons.build_icons(self.document, output, check=True)
                self.assertEqual(tree_snapshot(output), before)
                if mutation == "extra-dir":
                    self.assertTrue((output / "extra").is_dir())

    def test_invalid_tokens_are_rejected_before_output_creation(self):
        invalid = [None, [], {**self.document, "schema_version": True},
                   {**self.document, "version": None}, {**self.document, "themes": None}]
        injection = copy.deepcopy(self.document)
        injection["themes"]["Clair"]["accent"] = '#355e77" onload="bad'
        invalid.append(injection)
        contrast = copy.deepcopy(self.document)
        contrast["themes"]["Obscur"]["text"] = contrast["themes"]["Obscur"]["panel"]
        invalid.append(contrast)
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                with self.assertRaises(ValueError):
                    icons.build_icons(document, output)
                self.assertFalse(output.exists())

    def test_managed_dist_and_filesystem_root_are_not_output_targets(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(icons, "ROOT", Path(temporary)):
            for output in (Path(temporary) / "dist", Path(temporary) / "dist/icons", Path(Path(temporary).anchor)):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
            self.assertFalse((Path(temporary) / "dist").exists())

    def test_linked_output_ancestor_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "target"
            target.mkdir()
            (target / "keep.txt").write_bytes(b"unchanged")
            link = base / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink fixture unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "links or reparse"):
                icons.build_icons(self.document, link / "icons")
            self.assertEqual(tree_snapshot(target), {"keep.txt": b"unchanged"})

    def test_cli_requires_output_and_check_does_not_create_missing_tree(self):
        with self.assertRaises(SystemExit) as error:
            icons.main([])
        self.assertEqual(error.exception.code, 2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            self.assertEqual(icons.main(["--output", str(output)]), 0)
            self.assertEqual(icons.main(["--output", str(output), "--check"]), 0)
            before = tree_snapshot(output)
            with self.assertRaises(SystemExit) as existing:
                icons.main(["--output", str(output)])
            self.assertEqual(existing.exception.code, 1)
            self.assertEqual(tree_snapshot(output), before)
            missing = Path(temporary) / "missing"
            with self.assertRaises(SystemExit) as check:
                icons.main(["--output", str(missing), "--check"])
            self.assertEqual(check.exception.code, 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
