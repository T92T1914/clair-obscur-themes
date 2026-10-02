"""Preview staging failure precedence with small, inert payloads."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preview
from themeforge import build as release


class PreviewCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(self.retire_fixture)
        self.files = {'first.html': b'synthetic first file', 'second.html': b'synthetic second file'}
        self.payloads = patch.object(preview, 'preview_files', return_value=self.files)
        self.payloads.start()
        self.addCleanup(self.payloads.stop)

    def retire_fixture(self):
        # Delete only the exact task-owned temporary directory created here.
        self.assertEqual(Path(self.temporary.name).resolve(), self.root)
        self.temporary.cleanup()

    def build(self, output):
        return preview.build_preview(self.root, self.root / 'unused-artifacts', output)

    def write_failure(self, primary):
        original = Path.write_bytes

        def write(path, data):
            if path.name == 'second.html' and path.parent.name.startswith('.preview-stage-'):
                raise primary
            return original(path, data)

        return patch.object(Path, 'write_bytes', write)

    def retained_stage(self, parent):
        stages = list(parent.glob('.preview-stage-*'))
        self.assertEqual(len(stages), 1)
        files = {p.relative_to(stages[0]).as_posix(): p.read_bytes()
                 for p in stages[0].rglob('*') if p.is_file()}
        self.assertEqual(files, {'first.html': self.files['first.html']})

    def test_write_or_caller_failure_survives_failed_inventory_or_retirement(self):
        for kind in (ValueError, OSError, KeyboardInterrupt, SystemExit):
            for point in ('_inventory', '_remove_owned_tree'):
                with self.subTest(primary=kind.__name__, cleanup=point):
                    parent = self.root / (kind.__name__ + point)
                    output = parent / 'preview'
                    primary = kind('original preview write failure')
                    cleanup = PermissionError('secondary cleanup failure')
                    with self.write_failure(primary), patch.object(release, point, side_effect=cleanup):
                        with self.assertRaises(kind) as caught:
                            self.build(output)
                    self.assertIs(caught.exception, primary)
                    self.assertIn('Preview staging cleanup', ' '.join(primary.__notes__))
                    self.assertIn('PermissionError', ' '.join(primary.__notes__))
                    self.assertFalse(output.exists())
                    self.retained_stage(parent)

    def test_successful_retirement_preserves_the_original_write_failure(self):
        primary = ValueError('original write failure')
        output = self.root / 'preview'
        with self.write_failure(primary), self.assertRaises(ValueError) as caught:
            self.build(output)
        self.assertIs(caught.exception, primary)
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob('.preview-stage-*')))

    def test_failed_diagnostic_note_cannot_replace_the_original_failure(self):
        class DiagnosticFailure(ValueError):
            def add_note(self, note):
                raise OSError('diagnostic note failed')

        primary = DiagnosticFailure('original write failure')
        with self.write_failure(primary), patch.object(release, '_remove_owned_tree',
                side_effect=PermissionError('stage cleanup failed')):
            with self.assertRaises(DiagnosticFailure) as caught:
                self.build(self.root / 'preview')
        self.assertIs(caught.exception, primary)
        self.retained_stage(self.root)

    def test_rename_interruption_keeps_actual_before_and_after_effect_state(self):
        original = Path.rename
        for after_effect in (False, True):
            with self.subTest(after_effect=after_effect):
                output = self.root / str(after_effect) / 'preview'
                primary = KeyboardInterrupt('preview install interrupted')

                def rename(path, target):
                    if path.name.startswith('.preview-stage-'):
                        if after_effect:
                            original(path, target)
                        raise primary
                    return original(path, target)

                with patch.object(Path, 'rename', rename), self.assertRaises(KeyboardInterrupt) as caught:
                    self.build(output)
                self.assertIs(caught.exception, primary)
                self.assertEqual(output.exists(), after_effect)
                if after_effect:
                    self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, self.files)
                self.assertFalse(list(output.parent.glob('.preview-stage-*')))

    def test_standalone_retirement_callback_failure_remains_visible(self):
        # The callback fault is injected after an actual successful rename.
        # The complete preview remains inspectable even though the call raises.
        output = self.root / 'preview'
        cleanup = PermissionError('retirement callback failed')
        with patch.object(preview, '_retire_stage', side_effect=cleanup):
            with self.assertRaises(PermissionError) as caught:
                self.build(output)
        self.assertIs(caught.exception, cleanup)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, self.files)
        self.assertFalse(list(self.root.glob('.preview-stage-*')))

    def test_successful_install_and_repeat_do_not_change_payloads(self):
        output = self.root / 'preview'
        unrelated = self.root / 'keep.txt'
        unrelated.write_bytes(b'unrelated fixture file')
        self.build(output)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
        self.build(output)
        self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                          for p in output.iterdir()}, before)
        self.assertEqual(unrelated.read_bytes(), b'unrelated fixture file')
        self.assertFalse(list(self.root.glob('.preview-stage-*')))

    def test_existing_foreign_preview_is_preserved_before_any_stage(self):
        output = self.root / 'preview'
        output.mkdir()
        keep = output / 'keep.txt'
        keep.write_bytes(b'unrelated output')
        with self.assertRaisesRegex(ValueError, 'fresh output'):
            self.build(output)
        self.assertEqual(keep.read_bytes(), b'unrelated output')
        self.assertFalse(list(self.root.glob('.preview-stage-*')))

    def test_cli_prints_primary_error_and_secondary_retirement_note(self):
        primary = ValueError('original preview failure')
        primary.add_note('Preview staging cleanup could not finish (PermissionError). Inspect remaining temporary files before retrying.')
        stderr = io.StringIO()
        with patch.object(preview, 'build_preview', side_effect=primary), \
                patch('sys.argv', ['preview.py']), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                preview.main()
        self.assertEqual(caught.exception.code, 1)
        self.assertIn('Preview build failed: original preview failure', stderr.getvalue())
        self.assertIn(primary.__notes__[0], stderr.getvalue())

    def test_cli_preserves_caller_interruption(self):
        primary = KeyboardInterrupt('caller stopped preview')
        with patch.object(preview, 'build_preview', side_effect=primary), patch('sys.argv', ['preview.py']):
            with self.assertRaises(KeyboardInterrupt) as caught:
                preview.main()
        self.assertIs(caught.exception, primary)


if __name__ == '__main__':
    unittest.main()
