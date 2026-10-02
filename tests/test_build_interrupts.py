"""Fault schedules for owned package installation, without native installation."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from themeforge.build import PROJECT_ROOT, _remove_owned_tree, _verify_owned, build_release


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


class BuildInterruptionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tokens = self.root / "tokens.json"
        self.tokens.write_bytes((PROJECT_ROOT / "tokens.json").read_bytes())
        self.output = self.root / "release"

    def replacement(self):
        document = json.loads(self.tokens.read_text(encoding="utf-8"))
        document["version"] = "0.9.9"
        self.tokens.write_text(json.dumps(document), encoding="utf-8")

    def stop_at(self, point, failure, extra=None):
        rename = Path.rename
        fired = False

        def interrupted(path, target):
            nonlocal fired
            stage = path.name.startswith(".release.stage-")
            old = path == self.output
            if not fired and point == "before-stage" and stage:
                fired = True
                if extra:
                    extra()
                raise failure
            result = rename(path, target)
            if not fired and ((point == "after-old" and old) or
                              (point == "after-stage" and stage)):
                fired = True
                if extra:
                    extra()
                raise failure
            return result

        with patch.object(Path, "rename", interrupted):
            with self.assertRaises(type(failure)) as caught:
                build_release(self.tokens, self.output)
        self.assertTrue(fired)
        self.assertIs(caught.exception, failure)

    def assert_no_temporary_output(self):
        self.assertFalse(list(self.root.glob(".release.stage-*")))
        self.assertFalse(list(self.root.glob(".release.previous-*")))
        self.assertFalse(list(self.root.glob(".themeforge-*.lock")))

    def test_replacement_restores_original_across_install_interruptions(self):
        for kind in (KeyboardInterrupt, SystemExit, OSError):
            for point in ("before-stage", "after-old", "after-stage"):
                with self.subTest(kind=kind.__name__, point=point):
                    self.tokens.write_bytes((PROJECT_ROOT / "tokens.json").read_bytes())
                    build_release(self.tokens, self.output)
                    old = contents(self.output)
                    self.replacement()
                    failure = kind("controlled interruption")
                    self.stop_at(point, failure)
                    self.assertTrue(self.output.is_dir())
                    self.assertEqual(contents(self.output), old)
                    self.assert_no_temporary_output()

    def test_new_output_interruption_restores_absence(self):
        for kind in (KeyboardInterrupt, SystemExit, OSError):
            for point in ("before-stage", "after-stage"):
                with self.subTest(kind=kind.__name__, point=point):
                    self.stop_at(point, kind("controlled interruption"))
                    self.assertFalse(self.output.exists())
                    self.assert_no_temporary_output()

    def test_existing_empty_output_is_restored(self):
        for point in ("before-stage", "after-old", "after-stage"):
            with self.subTest(point=point):
                self.output.mkdir(exist_ok=True)
                self.stop_at(point, KeyboardInterrupt("controlled interruption"))
                self.assertTrue(self.output.is_dir())
                self.assertEqual(list(self.output.iterdir()), [])
                self.assert_no_temporary_output()

    def test_foreign_output_blocks_rollback_without_masking_interrupt(self):
        build_release(self.tokens, self.output)
        old = contents(self.output)
        self.replacement()

        def foreign_output():
            self.output.mkdir()
            (self.output / "keep.txt").write_text("intervening user file", encoding="utf-8")

        failure = KeyboardInterrupt("controlled interruption")
        self.stop_at("before-stage", failure, foreign_output)
        self.assertEqual((self.output / "keep.txt").read_text(), "intervening user file")
        backups = list(self.root.glob(".release.previous-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(contents(backups[0]), old)
        self.assertIn("recovery could not finish", failure.__notes__[0])
        self.assertFalse(list(self.root.glob(".release.stage-*")))
        self.assertFalse(list(self.root.glob(".themeforge-*.lock")))

    def test_changed_previous_files_are_preserved_for_recovery(self):
        build_release(self.tokens, self.output)
        self.replacement()

        def edit_backup():
            backup = next(self.root.glob(".release.previous-*"))
            (backup / "equicord" / "Clair.theme.css").write_text("intervening edit", encoding="utf-8")

        failure = SystemExit("controlled interruption")
        self.stop_at("before-stage", failure, edit_backup)
        backup = next(self.root.glob(".release.previous-*"))
        self.assertEqual((backup / "equicord" / "Clair.theme.css").read_text(), "intervening edit")
        self.assertFalse(self.output.exists())
        self.assertIn("recovery could not finish", failure.__notes__[0])

    def test_placeholder_interrupt_preserves_intervening_directory(self):
        for foreign_directory in (False, True):
            with self.subTest(foreign_directory=foreign_directory):
                build_release(self.tokens, self.output)
                old = contents(self.output)
                failure = KeyboardInterrupt("controlled placeholder interruption")
                rmdir = Path.rmdir
                fired = False

                def stop_placeholder(path):
                    nonlocal fired
                    if not fired and path.name.startswith(".release.previous-"):
                        fired = True
                        if foreign_directory:
                            (path / "personal").mkdir()
                        raise failure
                    return rmdir(path)

                with patch.object(Path, "rmdir", stop_placeholder):
                    with self.assertRaises(KeyboardInterrupt) as caught:
                        build_release(self.tokens, self.output)
                self.assertTrue(fired)
                self.assertIs(caught.exception, failure)
                self.assertEqual(contents(self.output), old)
                if foreign_directory:
                    backup = next(self.root.glob(".release.previous-*"))
                    self.assertTrue((backup / "personal").is_dir())
                    self.assertIn("recovery could not finish", failure.__notes__[0])
                    backup.rename(self.root / ("retained-" + backup.name))
                self.assert_no_temporary_output()

    def test_failed_restore_preserves_original_exception_and_previous_tree(self):
        build_release(self.tokens, self.output)
        old = contents(self.output)
        self.replacement()
        rename = Path.rename
        failure = KeyboardInterrupt("controlled interruption")

        def interrupted(path, target):
            if path.name.startswith(".release.stage-"):
                raise failure
            if path.name.startswith(".release.previous-"):
                raise OSError("controlled recovery failure")
            return rename(path, target)

        with patch.object(Path, "rename", interrupted):
            with self.assertRaises(KeyboardInterrupt) as caught:
                build_release(self.tokens, self.output)
        self.assertIs(caught.exception, failure)
        self.assertFalse(self.output.exists())
        backup = next(self.root.glob(".release.previous-*"))
        self.assertEqual(contents(backup), old)
        self.assertIn("recovery could not finish (OSError)", failure.__notes__[0])
        self.assertFalse(list(self.root.glob(".themeforge-*.lock")))

    def test_cleanup_interrupt_after_commit_keeps_complete_new_output(self):
        for point in ("before-cleanup", "after-first-old-file"):
            with self.subTest(point=point):
                self.tokens.write_bytes((PROJECT_ROOT / "tokens.json").read_bytes())
                build_release(self.tokens, self.output)
                self.replacement()
                failure = KeyboardInterrupt("controlled retirement interruption")
                unlink = Path.unlink

                def stop_cleanup(path, expected):
                    if path.name.startswith(".release.previous-"):
                        raise failure
                    return _remove_owned_tree(path, expected)

                def stop_after_file(path, *args, **kwargs):
                    result = unlink(path, *args, **kwargs)
                    if any(parent.name.startswith(".release.previous-") for parent in path.parents):
                        raise failure
                    return result

                target = (patch("themeforge.build._remove_owned_tree", stop_cleanup)
                          if point == "before-cleanup" else patch.object(Path, "unlink", stop_after_file))
                with target:
                    with self.assertRaises(KeyboardInterrupt) as caught:
                        build_release(self.tokens, self.output)
                self.assertIs(caught.exception, failure)
                verified = _verify_owned(self.output)
                self.assertEqual(json.loads(verified["artifact-manifest.json"])["version"], "0.9.9")
                self.assertFalse(list(self.root.glob(".release.stage-*")))
                self.assertFalse(list(self.root.glob(".themeforge-*.lock")))
                # Each remaining backup belongs to this fixture. Preserve the
                # partial retirement evidence without passing it to a rebuild.
                for backup in self.root.glob(".release.previous-*"):
                    backup.rename(self.root / ("retained-" + backup.name))


if __name__ == "__main__":
    unittest.main()
