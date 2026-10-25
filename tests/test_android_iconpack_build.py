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
from unittest.mock import patch
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from android import build
from themeforge import android_iconpack as pack


class AndroidBuildAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_static_manifest_retains_the_current_separate_pack_identity(self):
        root = ET.parse(build.ROOT / "android/app/AndroidManifest.xml").getroot()
        self.assertEqual(root.attrib["package"], "io.github.t92t1914.obscuricons")
        self.assertEqual(root.attrib[build.ANDROID + "versionCode"], "12")
        self.assertEqual(root.attrib[build.ANDROID + "versionName"], "0.1.11")
        self.assertEqual(root.findall("uses-permission"), [])
        self.assertEqual(len(root.findall("queries")), 1)
        self.assertEqual(list(root.find("queries")), [])
        build._validate_source_identity(build.ROOT / "android/app", pack.VERSION, pack.ARTWORK_VERSION)

    def static_source(self):
        source = self.root / "source/android/app"
        (source / "res/values").mkdir(parents=True)
        for name in ("AndroidManifest.xml", "res/values/strings.xml"):
            (source / name).write_bytes((build.ROOT / "android/app" / name).read_bytes())
        return source

    def test_stale_displayed_versions_are_refused_before_build_output_or_sdk_work(self):
        source = self.static_source()
        strings = source / "res/values/strings.xml"
        original = strings.read_text(encoding="utf-8")
        output = self.root / "build"
        arguments = ["--png-dir", str(self.root / "missing-png"), "--sdk", str(self.root / "missing-sdk"),
                     "--java-bin", str(self.root / "missing-java/bin"), "--output-dir", str(output)]
        for label in ("Icon pack 0.1.8 | Artwork 0.25.0", "Icon pack 0.1.9 | Artwork 0.26.0",
                      "Icon pack 0.1.10 | Artwork 0.26.0", "Icon pack 0.1.11 | Artwork 0.26.0"):
            strings.write_text(original.replace(build._version_label(), label), encoding="utf-8")
            diagnostic = io.StringIO()
            with self.subTest(label=label), patch.object(build, "ROOT", source.parents[1]), \
                    contextlib.redirect_stderr(diagnostic), self.assertRaises(SystemExit) as error:
                build.main(arguments)
            self.assertEqual(error.exception.code, 2)
            self.assertIn("Static versions string differs", diagnostic.getvalue())
            self.assertFalse(output.exists())

    def test_missing_or_duplicate_static_versions_are_refused(self):
        source = self.static_source()
        strings = source / "res/values/strings.xml"
        label = '<string name="versions">' + build._version_label() + '</string>'
        for content in ("", label + label):
            strings.write_text("<resources>" + content + "</resources>", encoding="utf-8")
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, "Static versions string differs"):
                build._validate_source_identity(source, pack.VERSION, pack.ARTWORK_VERSION)

    def test_static_manifest_and_preparer_versions_must_match_build_identity(self):
        source = self.static_source()
        manifest = source / "AndroidManifest.xml"
        original = manifest.read_text(encoding="utf-8")
        for old, replacement in (('versionCode="12"', 'versionCode="11"'),
                                 ('versionName="0.1.11"', 'versionName="0.1.10"')):
            manifest.write_text(original.replace(old, replacement), encoding="utf-8")
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, "manifest package/version"):
                build._validate_source_identity(source, pack.VERSION, pack.ARTWORK_VERSION)
        manifest.write_text(original, encoding="utf-8")
        for version, artwork in (("0.1.10", "0.27.0"), ("0.1.11", "0.26.0")):
            with self.subTest(version=version, artwork=artwork), self.assertRaisesRegex(ValueError, "preparer versions"):
                build._validate_source_identity(source, version, artwork)

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
            "artwork_version": "0.27.0", "pack_version": "0.1.11", "packages": rows}), encoding="utf-8")
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
        for field, value in (("pack_version", "0.1.0"), ("pack_version", "0.1.2"), ("pack_version", "0.1.3"), ("pack_version", "0.1.4"), ("pack_version", "0.1.5"), ("pack_version", "0.1.6"), ("pack_version", "0.1.7"), ("pack_version", "0.1.8"), ("pack_version", "0.1.9"), ("pack_version", "0.1.10"),
                             ("artwork_version", "0.17.0"), ("artwork_version", "0.19.0"), ("artwork_version", "0.20.0"), ("artwork_version", "0.21.0"), ("artwork_version", "0.22.0"), ("artwork_version", "0.23.0"), ("artwork_version", "0.24.0"), ("artwork_version", "0.25.0"), ("artwork_version", "0.26.0")):
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
        for index in range(300):
            (self.project / "res/drawable-nodpi" / ("co_icon_" + str(index) + ".png")).write_bytes(
                b"Synthetic original icon bytes " + str(index).encode("ascii"))
        for path in sorted(self.project.rglob("*")):
            if path.is_file():
                self.prepared["files"].append({"path": path.relative_to(self.project).as_posix(),
                                                **build._identity(path)})
        self.dump = ('E: resources (line=1)\n  E: item (line=1)\n'
                     '    A: component="ComponentInfo{example.app/example.app.Main}"\n'
                     '    A: drawable="co_icon_0"\n')
        self.badging = ("package: name='" + build.PACKAGE + "' versionCode='12' versionName='0.1.11'\n"
                        "minSdkVersion:'26'\ntargetSdkVersion:'36'\n")
        self.resources = ('Package name=' + build.PACKAGE + ' id=7f\n'
                          '  type string id=02 entryCount=2\n'
                          '    resource 0x7f020007 string/introduction\n'
                          '      () "Black and white icons from Clair and Obscur."\n'
                          '    resource 0x7f020008 string/versions\n'
                          '      () "Icon pack 0.1.11 | Artwork 0.27.0"\n'
                          '  type style id=03 entryCount=1\n')

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
        result = build._verify_apk(self.apk(), self.project, self.prepared, self.dump, self.badging, self.resources)
        self.assertEqual(result["drawables_byte_exact"], 300)
        self.assertEqual(result["compiled_component_mappings"], 1)
        self.assertEqual(result["displayed_versions"], "Icon pack 0.1.11 | Artwork 0.27.0")

    def test_changed_png_bytes_are_refused(self):
        with self.assertRaisesRegex(ValueError, "PNG (size|byte)"):
            build._verify_apk(self.apk("res/drawable-nodpi/co_icon_0.png"), self.project,
                              self.prepared, self.dump, self.badging, self.resources)

    def test_changed_project_asset_cannot_supply_its_own_expected_answer(self):
        (self.project / "assets/catalog.json").write_text('{"scope":"changed project"}')
        with self.assertRaisesRegex(ValueError, "Prepared project file changed"):
            build._verify_apk(self.apk(), self.project, self.prepared, self.dump, self.badging, self.resources)

    def test_compiled_mapping_and_permissions_are_independent_rejections(self):
        apk = self.apk()
        with self.assertRaisesRegex(ValueError, "Compiled appfilter"):
            build._verify_apk(apk, self.project, self.prepared, self.dump.replace("co_icon_0", "co_wrong"), self.badging, self.resources)
        with self.assertRaisesRegex(ValueError, "permission"):
            build._verify_apk(apk, self.project, self.prepared, self.dump,
                              self.badging + "uses-permission: name='android.permission.INTERNET'\n", self.resources)

    def test_stale_compiled_versions_are_refused_despite_current_package_badging(self):
        apk = self.apk()
        for label in ("Icon pack 0.1.8 | Artwork 0.25.0", "Icon pack 0.1.9 | Artwork 0.26.0",
                      "Icon pack 0.1.10 | Artwork 0.26.0", "Icon pack 0.1.11 | Artwork 0.26.0"):
            resources = self.resources.replace(build._version_label(), label)
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "Compiled APK versions string differs"):
                build._verify_apk(apk, self.project, self.prepared, self.dump, self.badging, resources)

    def test_compiled_versions_require_one_default_without_configured_variants(self):
        apk = self.apk()
        default = '      () "' + build._version_label() + '"\n'
        declaration = '    resource 0x7f020008 string/versions\n'
        for resources in ("", self.resources.replace(declaration, declaration.replace("versions", "unrelated")),
                          self.resources.replace(default, ""), self.resources.replace(default, default + default),
                          self.resources.replace(default, '      (en) "' + build._version_label() + '"\n'),
                          self.resources.replace(default, default + '      (en) "obsolete label"\n'),
                          self.resources + declaration + default):
            with self.subTest(resources=resources), self.assertRaisesRegex(ValueError, "Compiled APK versions string differs"):
                build._verify_apk(apk, self.project, self.prepared, self.dump, self.badging, resources)

    def test_prior_or_mixed_apk_versions_are_refused(self):
        apk = self.apk()
        for code, name in (("1", "0.1.0"), ("2", "0.1.1"), ("2", "0.1.2"), ("3", "0.1.1"),
                           ("3", "0.1.2"), ("3", "0.1.3"), ("4", "0.1.2"), ("4", "0.1.3"),
                           ("4", "0.1.4"), ("5", "0.1.3"), ("5", "0.1.4"),
                           ("5", "0.1.5"), ("6", "0.1.4"), ("6", "0.1.5"),
                           ("6", "0.1.6"), ("7", "0.1.5"), ("7", "0.1.6"),
                           ("7", "0.1.7"), ("8", "0.1.6"), ("8", "0.1.7"),
                           ("8", "0.1.8"), ("9", "0.1.7"),
                           ("9", "0.1.8"), ("9", "0.1.9"), ("10", "0.1.8"),
                           ("10", "0.1.9"), ("10", "0.1.10"), ("11", "0.1.9"),
                           ("11", "0.1.10"), ("11", "0.1.11"), ("12", "0.1.10")):
            badging = (f"package: name='{build.PACKAGE}' versionCode='{code}' versionName='{name}'\n"
                       "minSdkVersion:'26'\ntargetSdkVersion:'36'\n")
            with self.subTest(code=code, name=name), self.assertRaisesRegex(ValueError, "package/version differs"):
                build._verify_apk(apk, self.project, self.prepared, self.dump, badging, self.resources)


if __name__ == "__main__":
    unittest.main()
