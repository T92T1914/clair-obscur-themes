"""Build admission and byte-boundary fixtures, without Android compilation or signing."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from android import build


class AndroidBuildAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_existing_output_and_managed_source_paths_are_refused(self):
        output = self.root / "existing"
        output.mkdir()
        retained = output / "retained.txt"
        retained.write_bytes(b"retain exactly")
        with self.assertRaisesRegex(ValueError, "already exists"):
            build._validate_output(output, [])
        self.assertEqual(retained.read_bytes(), b"retain exactly")
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            build._validate_output(build.ROOT / "android/new-build", [])

    def test_repository_outputs_are_refused_before_creation_or_sdk_work(self):
        output = build.ROOT / "outputs" / ("refused-android-" + self.root.name)
        self.assertFalse(output.exists())
        arguments = ["--png-dir", str(self.root / "missing-png"), "--sdk", str(self.root / "missing-sdk"),
                     "--java-bin", str(self.root / "missing-java/bin"), "--output-dir", str(output)]
        diagnostic = io.StringIO()
        with contextlib.redirect_stderr(diagnostic), self.assertRaises(SystemExit) as error:
            build.main(arguments)
        self.assertEqual(error.exception.code, 2)
        self.assertIn("Build output must stay outside the repository", diagnostic.getvalue())
        self.assertFalse(output.exists())

    def test_output_cannot_contaminate_selected_artwork_or_sdk(self):
        for name in ("artwork", "sdk", "jdk"):
            source = self.root / name
            source.mkdir()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "outside"):
                build._validate_output(source / "new-output", [source])
            self.assertEqual(list(source.iterdir()), [])

    def test_static_collision_refuses_the_whole_copy_before_overwrite(self):
        source, project = self.root / "static", self.root / "project"
        source.mkdir()
        project.mkdir()
        (source / "a-first.txt").write_text("new static file")
        (source / "z-existing.txt").write_text("replacement")
        (project / "z-existing.txt").write_text("generated original")
        with self.assertRaisesRegex(ValueError, "collides"):
            build._copy_static(source, project)
        self.assertEqual((project / "z-existing.txt").read_text(), "generated original")
        self.assertFalse((project / "a-first.txt").exists())

    def test_static_copy_is_exclusive_and_byte_exact(self):
        source, project = self.root / "static", self.root / "project"
        (source / "assets").mkdir(parents=True)
        project.mkdir()
        original = b"Original license bytes\r\n"
        (source / "assets/NOTICE.txt").write_bytes(original)
        build._copy_static(source, project)
        self.assertEqual((project / "assets/NOTICE.txt").read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "collides"):
            build._copy_static(source, project)

    def project(self, packages=None, permission=""):
        project = self.root / "project"
        (project / "assets").mkdir(parents=True)
        rows = packages if packages is not None else [
            {"package": "example.first", "label": "First", "id": "first"},
            {"package": "example.second", "label": "Second", "id": "second"},
        ]
        (project / "assets/catalog.json").write_text(json.dumps({"schema_version": 1,
            "artwork_version": "0.18.0", "pack_version": "0.1.1", "packages": rows}), encoding="utf-8")
        (project / "AndroidManifest.xml").write_text(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="' + build.PACKAGE + '">' +
            permission + '<queries/><application/></manifest>', encoding="utf-8")
        return project

    def test_queries_are_exactly_the_public_catalog_without_widening(self):
        project = self.project()
        self.assertEqual(build._write_queries(project), ["example.first", "example.second"])
        root = ET.parse(project / "AndroidManifest.xml").getroot()
        self.assertEqual([row.attrib for row in root.findall("queries/package")],
                         [{build.ANDROID + "name": "example.first"}, {build.ANDROID + "name": "example.second"}])
        self.assertEqual(root.findall("uses-permission"), [])
        with self.assertRaisesRegex(ValueError, "empty"):
            build._write_queries(project)

    def test_prior_catalog_versions_are_refused_before_manifest_change(self):
        project = self.project()
        manifest = project / "AndroidManifest.xml"
        before = manifest.read_bytes()
        catalog_path = project / "assets/catalog.json"
        original = json.loads(catalog_path.read_text())
        for field, value in (("pack_version", "0.1.0"), ("artwork_version", "0.17.0")):
            catalog_path.write_text(json.dumps({**original, field: value}), encoding="utf-8")
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "version is unsupported"):
                build._write_queries(project)
            self.assertEqual(manifest.read_bytes(), before)

    def test_duplicate_catalog_and_permission_fail_before_manifest_change(self):
        for duplicate, permission in ((True, ""), (False,
                '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"/>')):
            with self.subTest(duplicate=duplicate):
                case = self.root / str(duplicate)
                case.mkdir()
                self.root, previous = case, self.root
                try:
                    rows = [{"package": "example.one", "label": "One", "id": "one"}]
                    project = self.project(rows * (2 if duplicate else 1), permission)
                    manifest = project / "AndroidManifest.xml"
                    before = manifest.read_bytes()
                    with self.assertRaises(ValueError):
                        build._write_queries(project)
                    self.assertEqual(manifest.read_bytes(), before)
                finally:
                    self.root = previous

    def test_signing_arguments_must_be_paired_before_any_output(self):
        arguments = ["--png-dir", str(self.root / "png"), "--sdk", str(self.root / "sdk"),
                     "--java-bin", str(self.root / "java/bin"), "--output-dir", str(self.root / "build"),
                     "--ks-pass-env", "ANDROID_ICONPACK_PRIVATE_TEST_PASSWORD"]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            build.main(arguments)
        self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.root / "build").exists())

    def test_child_failure_retains_actual_diagnostics_and_nonzero_receipt(self):
        output = self.root / "failure"
        output.mkdir()
        report = {"status": "running", "commands": []}
        with self.assertRaisesRegex(ValueError, "command failed"):
            build._run([sys.executable, "-c", "print('retained diagnostic'); raise SystemExit(7)"],
                       output, "fixture-child", report, os.environ.copy())
        self.assertIn("retained diagnostic", (output / "fixture-child.log").read_text())
        receipt = json.loads((output / "build.json").read_text())
        self.assertEqual(receipt["commands"][0]["returncode"], 7)
        self.assertEqual(receipt["commands"][0]["status"], "failed")
        self.assertNotIn("APK", receipt)


class AndroidAPKByteBoundaryTests(unittest.TestCase):
    """Synthetic ZIPs test byte comparison only, never compilation or PNG validity."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        (self.project / "res/drawable-nodpi").mkdir(parents=True)
        (self.project / "assets").mkdir()
        mapping = '<resources><item component="ComponentInfo{example.app/example.app.Main}" drawable="co_icon_0"/></resources>'
        (self.project / "assets/appfilter.xml").write_text(mapping)
        (self.project / "assets/catalog.json").write_text('{"scope":"synthetic byte fixture"}')
        self.prepared = {"files": []}
        for index in range(281):
            (self.project / "res/drawable-nodpi" / ("co_icon_" + str(index) + ".png")).write_bytes(
                b"Synthetic original icon bytes " + str(index).encode("ascii"))
        for path in sorted(self.project.rglob("*")):
            if path.is_file():
                self.prepared["files"].append({"path": path.relative_to(self.project).as_posix(),
                                                **build._identity(path)})
        self.dump = ('E: resources (line=1)\n  E: item (line=1)\n'
                     '    A: component="ComponentInfo{example.app/example.app.Main}"\n'
                     '    A: drawable="co_icon_0"\n')
        self.badging = ("package: name='" + build.PACKAGE + "' versionCode='2' versionName='0.1.1'\n"
                        "minSdkVersion:'26'\ntargetSdkVersion:'36'\n")

    def apk(self, changed=None):
        path = self.root / "fixture.apk"
        with ZipFile(path, "x") as archive:
            for row in self.prepared["files"]:
                raw = (self.project / row["path"]).read_bytes()
                archive.writestr(row["path"].replace("drawable-nodpi/", "drawable-nodpi-v4/"),
                                 b"changed" if row["path"] == changed else raw)
            archive.writestr("classes.dex", b"dex\n035\0synthetic boundary fixture")
        return path

    def test_byte_boundary_accepts_unchanged_pngs_after_resource_path_versioning(self):
        result = build._verify_apk(self.apk(), self.project, self.prepared, self.dump, self.badging)
        self.assertEqual(result["drawables_byte_exact"], 281)
        self.assertEqual(result["compiled_component_mappings"], 1)

    def test_changed_png_bytes_are_refused(self):
        with self.assertRaisesRegex(ValueError, "PNG (size|byte)"):
            build._verify_apk(self.apk("res/drawable-nodpi/co_icon_0.png"), self.project,
                              self.prepared, self.dump, self.badging)

    def test_changed_project_asset_cannot_supply_its_own_expected_answer(self):
        (self.project / "assets/catalog.json").write_text('{"scope":"changed project"}')
        with self.assertRaisesRegex(ValueError, "Prepared project file changed"):
            build._verify_apk(self.apk(), self.project, self.prepared, self.dump, self.badging)

    def test_compiled_mapping_and_permissions_are_independent_rejections(self):
        apk = self.apk()
        with self.assertRaisesRegex(ValueError, "Compiled appfilter"):
            build._verify_apk(apk, self.project, self.prepared, self.dump.replace("co_icon_0", "co_wrong"), self.badging)
        with self.assertRaisesRegex(ValueError, "permission"):
            build._verify_apk(apk, self.project, self.prepared, self.dump,
                              self.badging + "uses-permission: name='android.permission.INTERNET'\n")

    def test_prior_or_mixed_apk_versions_are_refused(self):
        apk = self.apk()
        for code, name in (("1", "0.1.0"), ("1", "0.1.1"), ("2", "0.1.0")):
            badging = (f"package: name='{build.PACKAGE}' versionCode='{code}' versionName='{name}'\n"
                       "minSdkVersion:'26'\ntargetSdkVersion:'36'\n")
            with self.subTest(code=code, name=name), self.assertRaisesRegex(ValueError, "package/version differs"):
                build._verify_apk(apk, self.project, self.prepared, self.dump, badging)


if __name__ == "__main__":
    unittest.main()
