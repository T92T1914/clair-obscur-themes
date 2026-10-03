from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from themeforge import chrome
from themeforge.tokens import load


ROOT = Path(__file__).resolve().parents[1]


class ChromeCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.tokens = load(ROOT / 'tokens.json')['themes']['Obscur']
        self.target = chrome.build_theme('Obscur', self.tokens, self.root, '1')
        self.original = {p.name: p.read_bytes() for p in self.target.iterdir()}

    def refuse_cleanup(self, failure):
        unlink = Path.unlink

        def remove(path, *args, **kwargs):
            if path.parent == self.target and path.name.startswith('.theme-'):
                raise failure
            return unlink(path, *args, **kwargs)

        return patch.object(Path, 'unlink', remove)

    def assert_original_and_temporary_retained(self):
        for name, content in self.original.items():
            self.assertEqual((self.target / name).read_bytes(), content)
        remaining = list(self.target.glob('.theme-*'))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].read_bytes(), self.original['icon128.png'])

    def test_replacement_error_and_caller_stops_survive_cleanup_refusal(self):
        for primary in (OSError('replacement refused'), KeyboardInterrupt('caller stopped'), SystemExit(9)):
            with self.subTest(primary=type(primary).__name__):
                cleanup = PermissionError('temporary removal refused')
                with patch.object(chrome.os, 'replace', side_effect=primary), self.refuse_cleanup(cleanup):
                    with self.assertRaises(type(primary)) as caught:
                        chrome.build_theme('Obscur', self.tokens, self.root, '2')
                self.assertIs(caught.exception, primary)
                self.assertIn('PermissionError', primary.__notes__[0])
                self.assertIn('temporary file may remain', primary.__notes__[0])
                self.assert_original_and_temporary_retained()
                for temporary in self.target.glob('.theme-*'):
                    temporary.unlink()

    def test_partial_write_error_and_stops_survive_close_and_unlink_failures(self):
        create = chrome.tempfile.NamedTemporaryFile
        for primary in (OSError('payload write refused'), KeyboardInterrupt('write stopped'), SystemExit(11)):
            with self.subTest(primary=type(primary).__name__):
                close_error = OSError('stream close refused')

                class PartialWrite:
                    def __init__(self, *args, **kwargs):
                        self.stream = create(*args, **kwargs)
                        self.name = self.stream.name

                    def write(self, payload):
                        self.stream.write(payload[:7])
                        raise primary

                    def close(self):
                        self.stream.close()
                        raise close_error

                with patch.object(chrome.tempfile, 'NamedTemporaryFile', PartialWrite), self.refuse_cleanup(PermissionError('unlink refused')):
                    with self.assertRaises(type(primary)) as caught:
                        chrome.build_theme('Obscur', self.tokens, self.root, '2')
                self.assertIs(caught.exception, primary)
                self.assertEqual(len(primary.__notes__), 2)
                self.assertIn('closure', primary.__notes__[0])
                self.assertIn('OSError', primary.__notes__[0])
                self.assertIn('cleanup', primary.__notes__[1])
                self.assertIn('PermissionError', primary.__notes__[1])
                self.assertEqual({name: (self.target / name).read_bytes() for name in self.original}, self.original)
                remaining = list(self.target.glob('.theme-*'))
                self.assertEqual(len(remaining), 1)
                self.assertEqual(remaining[0].read_bytes(), self.original['icon128.png'][:7])
                remaining[0].unlink()

    def test_close_failure_without_prior_write_failure_remains_primary(self):
        create = chrome.tempfile.NamedTemporaryFile
        primary = OSError('stream close refused')

        class CloseFailure:
            def __init__(self, *args, **kwargs):
                self.stream = create(*args, **kwargs)
                self.name = self.stream.name

            def write(self, payload):
                return self.stream.write(payload)

            def close(self):
                self.stream.close()
                raise primary

        with patch.object(chrome.tempfile, 'NamedTemporaryFile', CloseFailure), self.refuse_cleanup(PermissionError('unlink refused')):
            with self.assertRaises(OSError) as caught:
                chrome.build_theme('Obscur', self.tokens, self.root, '2')
        self.assertIs(caught.exception, primary)
        self.assertIn('cleanup', primary.__notes__[0])
        self.assert_original_and_temporary_retained()

    def test_diagnostic_note_failure_cannot_replace_original_error(self):
        class NoteFailure(OSError):
            def add_note(self, text):
                raise SystemExit('diagnostic stopped')

        primary = NoteFailure('replacement refused')
        with patch.object(chrome.os, 'replace', side_effect=primary), self.refuse_cleanup(PermissionError('cleanup')):
            with self.assertRaises(NoteFailure) as caught:
                chrome.build_theme('Obscur', self.tokens, self.root, '2')
        self.assertIs(caught.exception, primary)
        self.assert_original_and_temporary_retained()

    def test_cleanup_stop_preserves_original_replacement_error(self):
        primary = OSError('replacement refused')
        with patch.object(chrome.os, 'replace', side_effect=primary), self.refuse_cleanup(KeyboardInterrupt('cleanup stopped')):
            with self.assertRaises(OSError) as caught:
                chrome.build_theme('Obscur', self.tokens, self.root, '2')
        self.assertIs(caught.exception, primary)
        self.assertIn('KeyboardInterrupt', primary.__notes__[0])
        self.assert_original_and_temporary_retained()

    def test_cleanup_failure_after_completed_write_is_not_silenced(self):
        cleanup = PermissionError('metadata check refused')
        with self.refuse_cleanup(cleanup):
            with self.assertRaises(PermissionError) as caught:
                chrome.build_theme('Obscur', self.tokens, self.root, '2')
        self.assertIs(caught.exception, cleanup)
        # Replacement completed before cleanup failed. The old manifest and
        # license remain valid because the first atomic icon write stopped.
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, self.original)


if __name__ == '__main__':
    unittest.main()
