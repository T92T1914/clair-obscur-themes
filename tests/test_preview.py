import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from preview import ROOT, build_preview, preview_files, source_files, source_identity
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
            self.assertTrue({'README.md', 'tokens.json', 'build.py', 'preview.py', 'LICENSE'} <= names)
            self.assertEqual(archive.read('README.md'), (ROOT / 'README.md').read_bytes())
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
        major, minor, micro = map(int, document['version'].split('.'))
        document['version'] = f'{major}.{minor}.{micro + 1}'
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

    def test_release_checksums_verify_flat_downloads_including_source(self):
        files = preview_files(ROOT, self.artifacts)
        manifest = json.loads(files['downloads/artifact-manifest.json'])
        expected = {Path(item['path']).name: files['downloads/' + item['path']]
                    for item in manifest['downloads']}
        expected['source.zip'] = files['source.zip']
        expected['artifact-manifest.json'] = files['downloads/artifact-manifest.json']
        actual = {}
        for line in files['release-SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ', 1)
            self.assertNotIn(name, actual)
            self.assertEqual(Path(name).name, name)
            actual[name] = digest
        self.assertEqual(set(actual), set(expected))
        for name, payload in expected.items():
            self.assertEqual(actual[name], hashlib.sha256(payload).hexdigest())

    def test_released_source_and_current_snapshot_have_separate_identity(self):
        files = preview_files(ROOT, self.artifacts)
        manifest = json.loads(files['site-manifest.json'])
        version = json.loads((ROOT / 'tokens.json').read_text())['version']
        release_url = f'https://github.com/T92T1914/clair-obscur-themes/releases/download/v{version}'
        page = files['index.html'].decode()
        self.assertIn(f'id="released-source" href="{release_url}/source.zip"', page)
        self.assertIn(f'id="released-checksums" href="{release_url}/release-SHA256SUMS"', page)
        self.assertIn('id="current-source" href="source.zip"', page)
        self.assertNotIn(f'>Source {version}</a>', page)
        digest = hashlib.sha256(files['source.zip']).hexdigest()
        self.assertEqual(manifest['source']['sha256'], digest)
        self.assertEqual(files['source-SHA256SUMS'], f'{digest}  source.zip\n'.encode())
        self.assertEqual(manifest['release']['source_url'], release_url + '/source.zip')
        self.assertNotIn('{{', page)


class SourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sources = {'README.md': b'Original public source\n'}
        (self.root / 'README.md').write_bytes(self.sources['README.md'])

    def checkout(self):
        if shutil.which('git') is None:
            self.skipTest('Git is unavailable for the repository identity fixture')
        commands = [
            ['init', '--quiet'],
            ['-c', 'core.autocrlf=false', 'add', 'README.md'],
            ['-c', 'user.name=Preview fixture', '-c', 'user.email=preview@example.invalid',
             '-c', f'core.hooksPath={self.root / "unused-hooks"}', 'commit', '--quiet', '--no-gpg-sign', '-m', 'Fixture'],
        ]
        for arguments in commands:
            result = subprocess.run(['git', '-C', str(self.root), *arguments], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        return subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], timeout=15).decode().strip()

    def test_unpacked_source_has_no_claimed_revision(self):
        self.assertEqual(source_identity(self.root, self.sources), {'revision': None, 'state': 'unavailable'})
        with self.assertRaisesRegex(ValueError, 'requires a Git checkout'):
            source_identity(self.root, self.sources, 'a' * 40)

    def test_committed_source_identifies_exact_revision(self):
        revision = self.checkout()
        self.assertEqual(source_identity(self.root, self.sources, revision), {'revision': revision, 'state': 'clean'})

    def test_modified_source_is_labeled_and_rejected_for_deployment(self):
        revision = self.checkout()
        self.sources['README.md'] = b'Changed public source\n'
        (self.root / 'README.md').write_bytes(self.sources['README.md'])
        self.assertEqual(source_identity(self.root, self.sources)['state'], 'modified')
        with self.assertRaisesRegex(ValueError, 'unchanged committed source'):
            source_identity(self.root, self.sources, revision)

    def test_captured_changed_bytes_cannot_claim_clean_even_after_file_restoration(self):
        revision = self.checkout()
        captured = {'README.md': b'Captured before restoration\n'}
        self.assertEqual(source_identity(self.root, captured)['state'], 'modified')
        with self.assertRaisesRegex(ValueError, 'unchanged committed source'):
            source_identity(self.root, captured, revision)

    def test_untracked_public_source_cannot_claim_clean_revision(self):
        revision = self.checkout()
        self.sources['new-source.py'] = b'print("new source")\n'
        self.assertEqual(source_identity(self.root, self.sources)['state'], 'modified')
        with self.assertRaisesRegex(ValueError, 'unchanged committed source'):
            source_identity(self.root, self.sources, revision)

    def test_wrong_expected_revision_is_rejected(self):
        self.checkout()
        with self.assertRaisesRegex(ValueError, 'differs from the expected'):
            source_identity(self.root, self.sources, 'a' * 40)

    def test_git_failure_cannot_be_reported_as_clean_or_unavailable(self):
        self.checkout()
        with patch('preview.subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', b'failed')):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect'):
                source_identity(self.root, self.sources)

    def test_expected_revision_cannot_be_a_floating_ref(self):
        with self.assertRaisesRegex(ValueError, 'complete lowercase Git commit ID'):
            source_identity(self.root, self.sources, 'main')
