"""Release output safety, determinism and pure-theme boundaries."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from themeforge.build import CHECKSUMS, MANIFEST, PROJECT_ROOT, build_release


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class ReleaseBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "tokens.json"
        self.source.write_bytes((PROJECT_ROOT / "tokens.json").read_bytes())
        self.output = self.root / "release"

    def build(self, **kwargs):
        return build_release(self.source, self.output, **kwargs)

    def test_complete_repeatable_build_and_read_only_check(self):
        manifest = self.build()
        before = contents(self.output)
        mtimes = {p: p.stat().st_mtime_ns for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(len(manifest["downloads"]), 4)
        self.assertEqual(len(manifest["files"]), 10)
        self.build(check=True)
        self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in mtimes})
        self.build()
        self.assertEqual(before, contents(self.output))
        second = self.root / "unrelated-name"
        build_release(self.source, second)
        self.assertEqual(before, contents(second))
        self.assertNotIn(str(self.root).encode(), b"".join(before.values()))

    def test_archives_have_only_native_package_bytes_and_fixed_metadata(self):
        manifest = self.build()
        for artifact in manifest["downloads"]:
            path = self.output / artifact["path"]
            self.assertTrue(path.is_file())
            if artifact["platform"] == "chrome":
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(archive.namelist(), ["LICENSE.txt", "icon128.png", "manifest.json"])
                    canonical = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8").encode("utf-8")
                    self.assertEqual(archive.read("LICENSE.txt"), canonical)
                    for item in archive.infolist():
                        self.assertEqual(item.date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(item.compress_type, zipfile.ZIP_STORED)
                        self.assertEqual(item.create_system, 3)
                        self.assertEqual(item.external_attr >> 16, 0o100644)
                        source = self.output / "chrome" / artifact["name"].lower() / item.filename
                        self.assertEqual(source.read_bytes(), archive.read(item))

    def test_checksums_cover_manifest_and_every_payload(self):
        self.build()
        files = contents(self.output)
        lines = files.pop(CHECKSUMS).decode().splitlines()
        observed = dict(line.split("  ", 1)[::-1] for line in lines)
        self.assertEqual(set(observed), set(files))
        for name, payload in files.items():
            self.assertEqual(observed[name], hashlib.sha256(payload).hexdigest())

    def test_license_failure_preserves_the_previous_release(self):
        self.build()
        before = contents(self.output)
        invalid = self.root / "invalid-license"
        for payload in ("MIT License\n*/ body { color: red; }", "not the expected license", "MIT License\n" + "x" * 65536):
            with self.subTest(payload_length=len(payload)):
                invalid.write_text(payload, encoding="utf-8")
                with patch("themeforge.legal.LICENSE_PATH", invalid):
                    with self.assertRaisesRegex(ValueError, "Canonical license"):
                        self.build()
                self.assertEqual(contents(self.output), before)
        with patch("themeforge.legal.LICENSE_PATH", self.root / "missing-license"):
            with self.assertRaises(FileNotFoundError):
                self.build()
        self.assertEqual(contents(self.output), before)

    def test_crlf_license_source_produces_the_same_artifacts(self):
        self.build()
        before = contents(self.output)
        alternate = self.root / "windows-license"
        canonical = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
        alternate.write_bytes(canonical.replace("\n", "\r\n").encode("utf-8"))
        with patch("themeforge.legal.LICENSE_PATH", alternate):
            self.build(check=True)
        self.assertEqual(contents(self.output), before)

    def test_payload_review_rejects_omitted_or_changed_license_grants(self):
        from themeforge.build import _review_payloads

        self.build()
        original = {name: payload for name, payload in contents(self.output).items()
                    if name.startswith(("chrome/", "equicord/"))}
        for name in ("chrome/clair/LICENSE.txt", "equicord/Obscur.theme.css"):
            with self.subTest(path=name):
                changed = dict(original)
                changed[name] = changed[name].replace(b"Permission is hereby granted", b"Permission was omitted")
                with self.assertRaisesRegex(ValueError, "complete canonical license"):
                    _review_payloads(changed)

    def test_foreign_tree_is_preserved(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_text("unrelated user work")
        before = contents(self.output)
        with self.assertRaisesRegex(ValueError, "complete manifest"):
            self.build()
        self.assertEqual(before, contents(self.output))

    def test_modified_artifact_or_extra_directory_blocks_replacement(self):
        self.build()
        css = self.output / "equicord" / "Clair.theme.css"
        css.write_text("a user's local modification")
        with self.assertRaisesRegex(ValueError, "changed or is missing"):
            self.build()
        self.assertEqual(css.read_text(), "a user's local modification")

    def test_empty_foreign_directory_is_not_silently_discarded(self):
        self.build()
        (self.output / "personal").mkdir()
        with self.assertRaisesRegex(ValueError, "unrelated directories"):
            self.build()
        self.assertTrue((self.output / "personal").is_dir())

    def test_changed_source_check_fails_without_rewriting_output(self):
        self.build()
        before = contents(self.output)
        data = json.loads(self.source.read_text())
        data["version"] = "0.2.0"
        self.source.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "differs"):
            self.build(check=True)
        self.assertEqual(contents(self.output), before)
        self.build()
        self.assertNotEqual(contents(self.output), before)
        self.assertFalse((self.output / "artifacts" / "Clair-Chrome-0.1.0.zip").exists())

    def test_failed_generation_preserves_previous_build_and_cleans_owned_stage(self):
        self.build()
        before = contents(self.output)
        with patch("themeforge.build.render_theme", side_effect=ValueError("controlled generation failure")):
            with self.assertRaisesRegex(ValueError, "controlled generation failure"):
                self.build()
        self.assertEqual(contents(self.output), before)
        self.assertFalse(list(self.root.glob(".release.stage-*")))
        self.assertFalse(list(self.root.glob(".themeforge-*.lock")))

    def test_output_lock_is_not_removed_by_another_build(self):
        lock = self.root / ".themeforge-release.lock"
        lock.write_text("external owner\n")
        with self.assertRaisesRegex(ValueError, "Another build"):
            self.build()
        self.assertEqual(lock.read_text(), "external owner\n")

    def test_remote_css_and_executable_manifest_are_rejected_before_install(self):
        with patch("themeforge.build.render_theme", return_value='@import url("https://invalid.example/private.css");'):
            with self.assertRaisesRegex(ValueError, "remote resources"):
                self.build()
        self.assertFalse(self.output.exists())
        from themeforge.chrome import build_theme as real_build

        def injected(name, tokens, destination, version):
            directory = real_build(name, tokens, destination, version)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["permissions"] = ["history"]
            path.write_text(json.dumps(manifest))
            return directory

        with patch("themeforge.build.build_theme", side_effect=injected):
            with self.assertRaisesRegex(ValueError, "unexpected manifest capabilities"):
                self.build()
        self.assertFalse(self.output.exists())

    def test_machine_paths_are_not_published(self):
        with patch("themeforge.build.render_theme", return_value='/* C:\\Users\\Example\\private */'):
            with self.assertRaisesRegex(ValueError, "machine-local path"):
                self.build()

    def test_malformed_input_fails_before_output_creation(self):
        for payload in ('{"schema_version": 9}', 'null', '[]', '"string"', '{'):
            with self.subTest(payload=payload):
                self.source.write_text(payload)
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse(self.output.exists())

    def test_failed_stage_install_restores_the_previous_directory(self):
        self.build()
        before = contents(self.output)
        rename = Path.rename

        def interrupted(path, target):
            if path.name.startswith(".release.stage-"):
                raise OSError("controlled rename failure")
            return rename(path, target)

        with patch.object(Path, "rename", interrupted):
            with self.assertRaisesRegex(OSError, "controlled rename failure"):
                self.build()
        self.assertEqual(before, contents(self.output))
        self.assertFalse(list(self.root.glob(".release.previous-*")))
        self.assertFalse(list(self.root.glob(".release.stage-*")))

    def test_check_requires_existing_build(self):
        with self.assertRaisesRegex(ValueError, "existing complete"):
            self.build(check=True)

    def test_manifest_path_cannot_escape_output(self):
        self.build()
        path = self.output / MANIFEST
        manifest = json.loads(path.read_text())
        manifest["files"][0]["path"] = "../outside.txt"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "stay inside"):
            self.build()

    def test_symlink_output_is_refused(self):
        target = self.root / "preserve"
        target.mkdir()
        try:
            self.output.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("This host cannot create a symlink without additional privilege")
        with self.assertRaisesRegex(ValueError, "symlinks or reparse"):
            self.build()
        self.assertEqual(list(target.iterdir()), [])
