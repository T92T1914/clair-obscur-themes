import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from preview import ROOT, build_preview, preview_files, source_files
from themeforge.build import build_release


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.artifacts = self.base / 'artifacts'
        build_release(ROOT / 'tokens.json', self.artifacts)

    def test_site_and_downloads_are_repeatable_and_all_hashes_match(self):
        first = preview_files(ROOT, self.artifacts)
        self.assertEqual(first, preview_files(ROOT, self.artifacts))
        manifest = json.loads(first['site-manifest.json'])
        for path, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256(first[path]).hexdigest(), digest)
        release = json.loads(first['downloads/artifact-manifest.json'])
        for entry in release['files']:
            self.assertEqual(hashlib.sha256(first['downloads/' + entry['path']]).hexdigest(), entry['sha256'])

    def test_source_archive_contains_rebuild_inputs_without_runtime_state(self):
        with zipfile.ZipFile(io.BytesIO(preview_files(ROOT, self.artifacts)['source.zip'])) as archive:
            names = set(archive.namelist())
            self.assertTrue({'tokens.json', 'build.py', 'preview.py', 'LICENSE'} <= names)
            self.assertFalse(any(n.startswith(('node_modules/', '.git/', 'outputs/', 'dist/')) for n in names))
            self.assertFalse(any(n.endswith(('.ttf', '.woff2', '.icc', '.icm')) for n in names))

    def test_preview_refuses_to_overwrite_foreign_or_changed_files(self):
        output = self.base / 'site'
        build_preview(ROOT, self.artifacts, output)
        build_preview(ROOT, self.artifacts, output)
        (output / 'index.html').write_text('user change')
        with self.assertRaisesRegex(ValueError, 'fresh output'):
            build_preview(ROOT, self.artifacts, output)
        self.assertEqual((output / 'index.html').read_text(), 'user change')

    def test_changed_artifact_is_not_published(self):
        (self.artifacts / 'equicord' / 'Clair.theme.css').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            preview_files(ROOT, self.artifacts)

    def test_source_download_rebuilds_identical_themes_in_an_isolated_directory(self):
        isolated = self.base / 'source'
        isolated.mkdir()
        source = preview_files(ROOT, self.artifacts)['source.zip']
        with zipfile.ZipFile(io.BytesIO(source)) as archive:
            for name in archive.namelist():
                self.assertTrue((isolated / name).resolve().is_relative_to(isolated.resolve()))
            archive.extractall(isolated)
        for arguments in (['build.py'], ['build.py', '--check']):
            result = subprocess.run([sys.executable, *arguments], cwd=isolated, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in self.artifacts.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (isolated / 'dist' / path.relative_to(self.artifacts)).read_bytes())

    def test_change_between_initial_check_and_snapshot_is_rejected(self):
        def changed_after_check(*args, **kwargs):
            result = build_release(*args, **kwargs)
            (self.artifacts / 'equicord' / 'Clair.theme.css').write_text('intervening edit')
            return result
        with patch('preview.build_release', side_effect=changed_after_check):
            with self.assertRaisesRegex(ValueError, 'changed'):
                preview_files(ROOT, self.artifacts)

    def test_newer_complete_build_cannot_replace_the_verified_snapshot(self):
        document = json.loads((ROOT / 'tokens.json').read_text())
        document['version'] = '0.1.1'
        alternative = self.base / 'other-tokens.json'
        alternative.write_text(json.dumps(document))
        def changed_after_check(*args, **kwargs):
            result = build_release(*args, **kwargs)
            build_release(alternative, self.artifacts)
            return result
        with patch('preview.build_release', side_effect=changed_after_check):
            with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                preview_files(ROOT, self.artifacts)

    def test_unreviewed_web_files_cannot_enter_the_preview(self):
        # Substitute the directory listing without adding files to the source tree.
        original = Path.iterdir
        def extra_entry(path):
            values = list(original(path))
            return iter(values + [path / 'private-notes.txt']) if path == ROOT / 'web' else iter(values)
        with patch.object(Path, 'iterdir', extra_entry):
            with self.assertRaisesRegex(ValueError, 'Unreviewed web'):
                preview_files(ROOT, self.artifacts)

    def test_linked_source_directory_is_rejected_before_traversal(self):
        with patch('preview._linked', side_effect=lambda path: path == ROOT / 'docs'):
            with self.assertRaisesRegex(ValueError, 'Linked source directories'):
                source_files(ROOT)
