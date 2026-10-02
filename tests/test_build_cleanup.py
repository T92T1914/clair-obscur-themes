"""Failure precedence through staging and output-lock retirement."""
import json
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from themeforge import build as module


class CleanupFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tokens = self.root / "tokens.json"
        self.tokens.write_bytes((module.PROJECT_ROOT / "tokens.json").read_bytes())
        self.output = self.root / "release"
        module.build_release(self.tokens, self.output)
        self.before = module._verify_owned(self.output)

    def cleanup_faults(self, domain, stage_error, lock_error):
        original_remove = module._remove_owned_tree
        original_unlink = Path.unlink

        def remove(path, expected):
            if domain in ("stage", "both") and ".stage-" in path.name:
                raise stage_error
            return original_remove(path, expected)

        def unlink(path, *args, **kwargs):
            if domain in ("lock", "both") and path.name == ".themeforge-release.lock":
                raise lock_error
            return original_unlink(path, *args, **kwargs)

        return patch.object(module, "_remove_owned_tree", remove), patch.object(Path, "unlink", unlink)

    def retained_cleanup_state(self, domain):
        self.assertEqual(module._verify_owned(self.output), self.before)
        self.assertEqual(bool(list(self.root.glob(".release.stage-*"))), domain in ("stage", "both"))
        self.assertEqual((self.root / ".themeforge-release.lock").exists(), domain in ("lock", "both"))

    def isolate_leftovers(self):
        # These directories and lock belong only to this temporary fixture.
        # Keep their bytes until TemporaryDirectory's final teardown.
        for path in self.root.glob(".release.stage-*"):
            path.rename(self.root / ("retained-" + path.name))
        lock = self.root / ".themeforge-release.lock"
        if lock.exists():
            lock.rename(self.root / ("retained-lock-" + str(len(list(self.root.glob("retained-lock-*"))))))

    def test_generation_failure_survives_one_or_both_cleanup_faults(self):
        for kind in (ValueError, OSError, KeyboardInterrupt, SystemExit):
            for domain in ("stage", "lock", "both"):
                with self.subTest(kind=kind.__name__, domain=domain):
                    primary = kind("primary generation failure")
                    stage_error = PermissionError("stage cleanup refusal")
                    lock_error = PermissionError("lock cleanup refusal")
                    stage_patch, lock_patch = self.cleanup_faults(domain, stage_error, lock_error)
                    with patch.object(module, "_generate", side_effect=primary), stage_patch, lock_patch:
                        with self.assertRaises(kind) as caught:
                            module.build_release(self.tokens, self.output)
                    self.assertIs(caught.exception, primary)
                    notes = primary.__notes__
                    self.assertEqual(len(notes), 2 if domain == "both" else 1)
                    self.assertIn("Inspect remaining temporary files", " ".join(notes))
                    if domain in ("stage", "both"):
                        self.assertIn("Staging cleanup", notes[0])
                    if domain in ("lock", "both"):
                        self.assertIn("Output lock cleanup", notes[-1])
                    self.retained_cleanup_state(domain)
                    self.isolate_leftovers()

    def test_install_failure_and_restoration_survive_combined_cleanup_faults(self):
        primary = KeyboardInterrupt("install interrupted")
        original_rename = Path.rename

        def rename(path, target):
            if path.name.startswith(".release.stage-"):
                raise primary
            return original_rename(path, target)

        stage_patch, lock_patch = self.cleanup_faults("both", PermissionError("stage"), OSError("lock"))
        with patch.object(Path, "rename", rename), stage_patch, lock_patch:
            with self.assertRaises(KeyboardInterrupt) as caught:
                module.build_release(self.tokens, self.output)
        self.assertIs(caught.exception, primary)
        self.assertEqual(len(primary.__notes__), 2)
        self.retained_cleanup_state("both")
        self.assertFalse(list(self.root.glob(".release.previous-*")))

    def test_stage_cleanup_failure_after_successful_check_is_reported(self):
        cleanup_error = PermissionError("stage retirement")
        stage_patch, lock_patch = self.cleanup_faults("stage", cleanup_error, OSError("unused"))
        with stage_patch, lock_patch:
            with self.assertRaises(PermissionError) as caught:
                module.build_release(self.tokens, self.output, check=True)
        self.assertIs(caught.exception, cleanup_error)
        self.retained_cleanup_state("stage")

    def test_lock_cleanup_failure_keeps_new_committed_output(self):
        document = json.loads(self.tokens.read_text())
        document["version"] = "0.9.8"
        self.tokens.write_text(json.dumps(document))
        cleanup_error = PermissionError("lock retirement")
        stage_patch, lock_patch = self.cleanup_faults("lock", OSError("unused"), cleanup_error)
        with stage_patch, lock_patch:
            with self.assertRaises(PermissionError) as caught:
                module.build_release(self.tokens, self.output)
        self.assertIs(caught.exception, cleanup_error)
        files = module._verify_owned(self.output)
        self.assertEqual(json.loads(files[module.MANIFEST])["version"], "0.9.8")
        self.assertFalse(list(self.root.glob(".release.stage-*")))
        self.assertFalse(list(self.root.glob(".release.previous-*")))
        self.assertTrue((self.root / ".themeforge-release.lock").is_file())

    def test_diagnostic_failure_cannot_replace_original(self):
        class HostileNote(ValueError):
            def add_note(self, text):
                raise RuntimeError("note formatting failed")

        primary = HostileNote("primary")
        stage_patch, lock_patch = self.cleanup_faults("both", OSError("stage"), OSError("lock"))
        with patch.object(module, "_generate", side_effect=primary), stage_patch, lock_patch:
            with self.assertRaises(HostileNote) as caught:
                module.build_release(self.tokens, self.output)
        self.assertIs(caught.exception, primary)
        self.retained_cleanup_state("both")

    def test_cli_reports_primary_failure_and_cleanup_notes(self):
        primary = ValueError("primary generation failure")
        errors = io.StringIO()
        stage_patch, lock_patch = self.cleanup_faults("both", OSError("stage"), OSError("lock"))
        with patch.object(module, "_generate", side_effect=primary), stage_patch, lock_patch, redirect_stderr(errors):
            with self.assertRaises(SystemExit) as caught:
                module.main(["--tokens", str(self.tokens), "--output", str(self.output)])
        self.assertEqual(caught.exception.code, 1)
        message = errors.getvalue()
        self.assertTrue(message.startswith("Build failed: primary generation failure\n"))
        self.assertIn("Staging cleanup could not finish", message)
        self.assertIn("Output lock cleanup could not finish", message)
        self.retained_cleanup_state("both")


if __name__ == "__main__":
    unittest.main()
