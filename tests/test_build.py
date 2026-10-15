"""Release output safety, determinism and pure-theme boundaries."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from themeforge.build import CHECKSUMS, MANIFEST, PROJECT_ROOT, build_release


# Accepted payload identities before the Clair-only 0.1.2 correction.
ACCEPTED_PAYLOAD_HASHES = {
    "artifacts/Clair-Chrome-0.1.1.zip": "4bfa96dd8ffa50647d507c5b7aabb0d82f7c96b7cf07f4beaa73c43a5579aad5",
    "artifacts/Clair-Firefox-0.2.0.xpi": "72fb8c7cdb5db8465382a897bce07701f3ffc9172af3d2808e390997c6190ae2",
    "artifacts/Clair-Obscur-OperaGX-0.3.0.zip": "44d2073cc0c727027627699ddda292ead0c09e964cd247cd490736b37d43b342",
    "artifacts/Clair-Vivaldi-0.3.0.zip": "7af6406839d404cbaf8195eda64eb1af248c62c2f34e45d178202102f9b518f5",
    "artifacts/Obscur-Chrome-0.1.1.zip": "b8bb73a48ddbc1e8f2f92258d30c3875b17d9d5ec98eab04c457eab2f2a5474a",
    "artifacts/Obscur-Firefox-0.2.0.xpi": "3bf5bdfc6436eff3219fefd00a88d095567d51c60d2851a073cb0a8a04de7a0b",
    "artifacts/Obscur-Vivaldi-0.3.0.zip": "f179e62920efc75068de69940f4ff77a351780e3c3682e532a44aad22f1f94de",
    "betterdiscord/Clair-BetterDiscord.theme.css": "fd7f6dd7453f8e01afc53ceb97c095919bb37106f6ddcde327a347bc8b5bcb66",
    "betterdiscord/Obscur-BetterDiscord.theme.css": "2661e2341fef8f02ceed4b47779e85a980c546ca8fe10b1559f16e4d25961806",
    "chrome/clair/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "chrome/clair/icon128.png": "ecf946129ba69ca83feaaa6aa588d874ed091b626de5c774fd24536881893d1c",
    "chrome/clair/manifest.json": "7c8d5d82f1f182708dab801b624cbf4b6628ccc97760701acd63b648110e705b",
    "chrome/obscur/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "chrome/obscur/icon128.png": "15ced3ef1221aec8810fbb260aa483107c2a015efb10a70f137c65270f9b7852",
    "chrome/obscur/manifest.json": "d620a89908f6e400614159d7ee12a4ea395d9f48c71b77185980ce388eb9ba90",
    "equicord/Clair.theme.css": "0f3337db8fc9ea35ff52e36e0d1028d242f1af30e2c1edd144af11939173f847",
    "equicord/Obscur.theme.css": "b2fc01e87f749c1138ca5635eb77f1463d2bcb2eac6d5de898bb8d840741d1dd",
    "firefox/clair/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "firefox/clair/manifest.json": "6162945f989ced1d96d51b56ad064b7612178f79cf8c1581693c479f321d1e5d",
    "firefox/obscur/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "firefox/obscur/manifest.json": "63a45cef4ade23fe8e68221b6bd8e0d3a9f21191fc9b6ca2bfa07ca783ca3e69",
    "opera-gx/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "opera-gx/icon512.png": "54166075cc3f3d363041eda86696a7984e3cfa8940cdc1445b465df641cfefed",
    "opera-gx/manifest.json": "0102df238b7cd0792f7a84329885cafcb8be9ebc6a17cb64539d36bea21b4e16",
    "vencord/Clair-Vencord.theme.css": "f46e5ad65bbcb6ed3d68988ec064c8ea5cd824075c630c81695cb3b1c52b92ea",
    "vencord/Obscur-Vencord.theme.css": "22608a0ea5600b44b12fc0299f1f5981162c702197cfad2907a06086e9f4664a",
    "vivaldi/LICENSE.txt": "4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd",
    "vivaldi/clair/settings.json": "2db074af99419c97c6655e941f7727e3656b2a74ce9387dcc9fb2fdb79205098",
    "vivaldi/obscur/settings.json": "bbffadeca79b4f1f2ea0bfd4640dd6f8a08fa6d07d740837089f6b9e7e943e65",
}


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
        self.assertEqual(len(manifest["downloads"]), 17)
        self.assertEqual(len({item["path"] for item in manifest["downloads"]}), 13)
        self.assertEqual(len(manifest["files"]), 30)
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

    def test_clair_focus_package_retains_all_accepted_payload_identities(self):
        manifest = self.build()
        records = {record["path"]: record for record in manifest["files"]}
        corrected = "equicord/Clair-Equicord-0.1.2.theme.css"
        self.assertEqual(set(records), set(ACCEPTED_PAYLOAD_HASHES) | {corrected})
        for path, expected in ACCEPTED_PAYLOAD_HASHES.items():
            with self.subTest(path=path):
                actual = hashlib.sha256((self.output / path).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)
                self.assertEqual(records[path]["sha256"], expected)
        self.assertEqual(manifest["version"], "0.1.1")
        self.assertEqual(manifest["adapter_version"], "0.2.0")
        self.assertEqual(manifest["browser_adapter_version"], "0.3.0")
        css = (self.output / corrected).read_text(encoding="utf-8")
        self.assertIn("@name Clair", css)
        self.assertIn("@version 0.1.2", css)
        self.assertNotEqual(records[corrected]["sha256"],
                            records["equicord/Clair.theme.css"]["sha256"])
        current = next(item for item in manifest["downloads"]
                       if item["platform"] == "equicord" and item["name"] == "Clair")
        self.assertEqual(current, {
            "name": "Clair", "platform": "equicord", "path": corrected,
            "kind": "local-theme-css", "version": "0.1.2",
        })
        self.assertFalse(any(item["path"] == "equicord/Clair.theme.css"
                             for item in manifest["downloads"]))

    def test_failed_clair_focus_generation_preserves_existing_release(self):
        self.build()
        before = contents(self.output)
        with patch("themeforge.build.render_clair_native_focus",
                   side_effect=ValueError("controlled Clair focus generation failure")):
            with self.assertRaisesRegex(ValueError, "controlled Clair focus generation failure"):
                self.build()
        self.assertEqual(contents(self.output), before)

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
                    if not name.startswith("artifacts/") and name not in (MANIFEST, CHECKSUMS)}
        for name in ("chrome/clair/LICENSE.txt", "equicord/Obscur.theme.css",
                     "equicord/Clair-Equicord-0.1.2.theme.css"):
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
