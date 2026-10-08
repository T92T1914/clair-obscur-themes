import hashlib
from html.parser import HTMLParser
import io
import json
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from preview import PORTABLE_ARCHIVE, PORTABLE_CHECKSUMS, ROOT, build_preview, preview_files, source_files, source_identity
from themeforge.build import build_release
from themeforge.guides import GUIDE_HEADINGS, JOURNEY_HEADINGS, guide_anchor, render_guides


class PageLinks(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links = [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs)


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

    def test_portable_archive_has_safe_deterministic_members_and_complete_hash_coverage(self):
        files = preview_files(ROOT, self.artifacts)
        public = json.loads(files['site-manifest.json'])
        archive_bytes = files[PORTABLE_ARCHIVE]
        digest = hashlib.sha256(archive_bytes).hexdigest()
        self.assertEqual(files[PORTABLE_CHECKSUMS], f'{digest}  {PORTABLE_ARCHIVE}\n'.encode())
        self.assertEqual(public['distribution']['portable_kit'], {
            'archive': PORTABLE_ARCHIVE, 'checksums': PORTABLE_CHECKSUMS,
            'sha256': digest, 'bytes': len(archive_bytes),
        })
        self.assertEqual(set(public['files']), set(files) - {'site-manifest.json'})
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(set(names)))
            self.assertEqual(set(names), set(files) - {PORTABLE_ARCHIVE, PORTABLE_CHECKSUMS})
            self.assertIsNone(archive.testzip())
            for info in archive.infolist():
                member = PurePosixPath(info.filename)
                self.assertFalse(member.is_absolute())
                self.assertNotIn('..', member.parts)
                self.assertNotIn('\\', info.filename)
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.external_attr >> 16, 0o100644)
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            inner = json.loads(archive.read('site-manifest.json'))
            self.assertEqual(inner['distribution'], {'kind': 'portable-kit'})
            self.assertEqual(inner['source'], public['source'])
            self.assertEqual(inner['release'], public['release'])
            self.assertEqual(set(inner['files']), set(names) - {'site-manifest.json'})
            for name, expected in inner['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
                if name != 'index.html':
                    self.assertEqual(archive.read(name), files[name])

    def test_downloaded_kit_relocates_with_resolvable_local_links_and_distinct_delivery_text(self):
        files = preview_files(ROOT, self.artifacts)
        extracted = self.base / 'extracted'
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as archive:
            archive.extractall(extracted)
        relocated = self.base / 'moved' / 'preview'
        relocated.parent.mkdir()
        extracted.rename(relocated)
        page = (relocated / 'index.html').read_text(encoding='utf-8')
        parsed = PageLinks(page)
        self.assertIn('This is the extracted portable preview', page)
        self.assertNotIn('id="portable-preview"', page)
        self.assertNotIn(PORTABLE_ARCHIVE, page)
        self.assertNotIn(PORTABLE_CHECKSUMS, page)
        self.assertIn('id="portable-preview"', files['index.html'].decode())
        self.assertIn('id="portable-checksums"', files['index.html'].decode())
        self.assertIn('display a CSS file instead of downloading another copy', page)
        self.assertIn('Open included Clair for Google Chrome', page)
        for link in parsed.links:
            href = link.get('href', '')
            if href.startswith('#'):
                self.assertIn(href[1:], parsed.ids)
            elif not href.startswith('https://'):
                target = (relocated / href).resolve()
                self.assertTrue(target.is_relative_to(relocated.resolve()), href)
                self.assertTrue(target.is_file(), href)
        release = json.loads((relocated / 'downloads/artifact-manifest.json').read_bytes())
        self.assertEqual(len(release['downloads']), 17)
        self.assertEqual(len({item['path'] for item in release['downloads']}), 13)
        for item in release['downloads']:
            self.assertIn(f'<code>downloads/{item["path"]}</code>', page)
        self.assertEqual(len([anchor for anchor in parsed.ids
                              if any(anchor == guide_anchor(item['platform'], name)
                                     for item in release['downloads']
                                     for name in (('Clair', 'Obscur') if item['platform'] == 'opera-gx'
                                                  else (item['name'],)))]), 18)
        self.assertNotIn('{{', page)

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

    def test_all_download_appearances_have_complete_local_guides_and_exact_packages(self):
        files = preview_files(ROOT, self.artifacts)
        page = files['index.html'].decode()
        parsed = PageLinks(page)
        manifest = json.loads(files['downloads/artifact-manifest.json'])
        records = {item['path']: item for item in manifest['files']}
        self.assertEqual(len(parsed.ids), len(set(parsed.ids)), 'Duplicate page anchors')
        for platform, heading in GUIDE_HEADINGS.items():
            body = re.search(rf'<article[^>]+id="guide-{platform}".*?</article>', page, re.DOTALL).group()
            self.assertIn(heading.replace('&', '&amp;'), body)
            for required in JOURNEY_HEADINGS:
                self.assertIn(f'<h4>{required}</h4>', body)
        for item in manifest['downloads']:
            appearances = ('Clair', 'Obscur') if item['platform'] == 'opera-gx' else (item['name'],)
            for appearance in appearances:
                anchor = guide_anchor(item['platform'], appearance)
                self.assertIn(anchor, parsed.ids)
                self.assertTrue(any(link.get('class') == 'guide-link' and link['href'] == '#' + anchor
                                    for link in parsed.links))
                package = re.search(rf'<div[^>]+id="{anchor}".*?</div>', page, re.DOTALL).group()
                self.assertIn(f'Package {item["version"]}.', package)
                self.assertIn(f'href="downloads/{item["path"]}"', package)
                self.assertIn(records[item['path']]['sha256'], package)
        self.assertIn('installation-only native evidence', page)
        self.assertIn('Full client coverage', page)
        self.assertIn('unsigned static-theme candidates', page)
        self.assertIn('Upload Theme', page)
        self.assertIn('userscript does not support Themes', page)
        self.assertIn('one paired candidate', page)

    def test_relocated_static_guides_have_resolvable_local_links_without_script(self):
        generated, relocated = self.base / 'generated', self.base / 'relocated' / 'preview'
        build_preview(ROOT, self.artifacts, generated)
        relocated.parent.mkdir()
        generated.rename(relocated)
        page = (relocated / 'index.html').read_text(encoding='utf-8')
        parsed = PageLinks(page)
        self.assertIn('instructions remain available below', page)
        self.assertIn('without JavaScript or a network connection', page)
        for link in parsed.links:
            href = link.get('href', '')
            if href.startswith('#'):
                self.assertIn(href[1:], parsed.ids)
            elif not href.startswith('https://'):
                target = (relocated / href).resolve()
                self.assertTrue(target.is_relative_to(relocated.resolve()), href)
                self.assertTrue(target.is_file(), href)
        self.assertIn('id="guide-client-fonts"', page)
        self.assertNotIn('{{', page)

    def test_guide_renderer_escapes_text_and_refuses_active_or_file_links(self):
        source = (ROOT / 'docs/installation.md').read_bytes()
        manifest = json.loads((self.artifacts / 'artifact-manifest.json').read_bytes())
        marker = b'Use standard desktop Google Chrome.'
        escaped = render_guides(source.replace(marker, b'Use <script>alert(1)</script> as plain text.'), manifest)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', escaped)
        self.assertNotIn('<script>', escaped)
        for scheme in (b'javascript:alert', b'file:///private', b'data:text/plain,test'):
            with self.subTest(scheme=scheme):
                changed = source.replace(marker, b'Use [an unsupported link](' + scheme + b').')
                with self.assertRaisesRegex(ValueError, 'Unsupported installation-guide link'):
                    render_guides(changed, manifest)
        self.assertEqual(render_guides(source, manifest), render_guides(source.replace(b'\n', b'\r\n'), manifest))

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
        self.assertEqual(len(expected), len({item['path'] for item in manifest['downloads']}))
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


class PreviewTokenSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'source'
        for name, data in source_files(ROOT).items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.tokens = self.root / 'tokens.json'
        self.original = json.loads(self.tokens.read_bytes())
        major, minor, patch_version = map(int, self.original['version'].split('.'))
        self.changed = dict(self.original, version=f'{major}.{minor}.{patch_version + 1}')
        self.artifacts = self.base / 'artifacts'
        self.output = self.base / 'preview'
        build_release(self.tokens, self.artifacts)

    def test_token_change_during_artifact_check_cannot_mix_preview_versions(self):
        # The display read sees old tokens, but the artifact check sees the
        # newer complete build. Both inputs are individually valid.
        self.tokens.write_text(json.dumps(self.changed), encoding='utf-8')
        build_release(self.tokens, self.artifacts)
        self.tokens.write_text(json.dumps(self.original), encoding='utf-8')

        def change_after_display_read(path):
            document = json.loads(path.read_bytes())
            self.tokens.write_text(json.dumps(self.changed), encoding='utf-8')
            return document

        with patch('preview.load', side_effect=change_after_display_read):
            with self.assertRaisesRegex(ValueError, 'Token snapshot'):
                build_preview(self.root, self.artifacts, self.output)
        self.assertFalse(self.output.exists())

    def test_guide_and_source_archive_use_one_captured_document_even_after_live_edit(self):
        path = self.root / 'docs' / 'installation.md'
        captured = path.read_bytes().replace(b'Use standard desktop Google Chrome.', b'Captured Chrome prerequisite.')
        path.write_bytes(captured)

        def change_after_capture(root):
            sources = source_files(root)
            path.write_bytes(captured.replace(b'Captured Chrome prerequisite.', b'Later live Chrome prerequisite.'))
            return sources

        with patch('preview.source_files', side_effect=change_after_capture):
            files = preview_files(self.root, self.artifacts)
        self.assertIn(b'Captured Chrome prerequisite.', files['index.html'])
        self.assertNotIn(b'Later live Chrome prerequisite.', files['index.html'])
        with zipfile.ZipFile(io.BytesIO(files['source.zip'])) as archive:
            self.assertEqual(archive.read('docs/installation.md'), captured)

    def test_missing_or_incomplete_guide_is_refused_before_output(self):
        path = self.root / 'docs' / 'installation.md'
        original = path.read_bytes()
        for changed in (original.replace(b'## Brave\n', b'## Removed Brave\n'),
                        original.replace(b'### Troubleshooting\n', b'### Details\n', 1)):
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'Missing installation guide|Incomplete installation guide'):
                build_preview(self.root, self.artifacts, self.output)
            self.assertFalse(self.output.exists())

    def test_token_change_during_source_capture_cannot_publish_unmatched_source(self):
        def change_before_capture(root):
            self.tokens.write_text(json.dumps(self.changed), encoding='utf-8')
            return source_files(root)

        with patch('preview.source_files', side_effect=change_before_capture):
            with self.assertRaisesRegex(ValueError, 'Source tokens'):
                build_preview(self.root, self.artifacts, self.output)
        self.assertFalse(self.output.exists())

    def test_rejected_token_change_preserves_an_existing_preview(self):
        build_preview(self.root, self.artifacts, self.output)
        before = {path.relative_to(self.output): path.read_bytes()
                  for path in self.output.rglob('*') if path.is_file()}

        def change_before_capture(root):
            self.tokens.write_text(json.dumps(self.changed), encoding='utf-8')
            return source_files(root)

        with patch('preview.source_files', side_effect=change_before_capture):
            with self.assertRaisesRegex(ValueError, 'Source tokens'):
                build_preview(self.root, self.artifacts, self.output)
        after = {path.relative_to(self.output): path.read_bytes()
                 for path in self.output.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(list(self.base.glob('.preview-stage-*')))

    def test_equivalent_token_formatting_preserves_downloads_and_exact_source_bytes(self):
        formatted = (json.dumps(self.original, indent=4) + '\n').encode()

        def reformat_before_capture(root):
            self.tokens.write_bytes(formatted)
            return source_files(root)

        with patch('preview.source_files', side_effect=reformat_before_capture):
            files = preview_files(self.root, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files['source.zip'])) as archive:
            self.assertEqual(archive.read('tokens.json'), formatted)
        self.assertEqual(files['downloads/artifact-manifest.json'],
                         (self.artifacts / 'artifact-manifest.json').read_bytes())

    def test_captured_source_tokens_must_keep_the_loader_utf8_encoding(self):
        def change_encoding_before_capture(root):
            self.tokens.write_bytes(json.dumps(self.original).encode('utf-16'))
            return source_files(root)

        with patch('preview.source_files', side_effect=change_encoding_before_capture):
            with self.assertRaises(UnicodeDecodeError):
                build_preview(self.root, self.artifacts, self.output)
        self.assertFalse(self.output.exists())

    def test_license_download_and_source_archive_use_the_same_captured_bytes(self):
        license_path = self.root / 'LICENSE'
        captured = license_path.read_bytes()

        def change_after_capture(root):
            sources = source_files(root)
            license_path.write_bytes(captured.replace(b'2026 T92T1914', b'2027 Other author'))
            return sources

        with patch('preview.source_files', side_effect=change_after_capture):
            files = preview_files(self.root, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files['source.zip'])) as archive:
            self.assertEqual(archive.read('LICENSE'), captured)
        self.assertEqual(files['LICENSE'], captured)
        self.assertNotEqual(license_path.read_bytes(), captured)

    def test_source_license_change_after_artifact_verification_is_rejected(self):
        license_path = self.root / 'LICENSE'
        changed = license_path.read_bytes().replace(b'2026 T92T1914', b'2027 Other author')

        def change_before_capture(root):
            license_path.write_bytes(changed)
            return source_files(root)

        with patch('preview.source_files', side_effect=change_before_capture):
            with self.assertRaisesRegex(ValueError, 'Source license'):
                build_preview(self.root, self.artifacts, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob('.preview-stage-*')))

    def test_rejected_source_license_change_preserves_an_existing_preview(self):
        build_preview(self.root, self.artifacts, self.output)
        before = {path.relative_to(self.output): path.read_bytes()
                  for path in self.output.rglob('*') if path.is_file()}
        license_path = self.root / 'LICENSE'
        changed = license_path.read_bytes().replace(b'2026 T92T1914', b'2027 Other author')

        def change_before_capture(root):
            license_path.write_bytes(changed)
            return source_files(root)

        with patch('preview.source_files', side_effect=change_before_capture):
            with self.assertRaisesRegex(ValueError, 'Source license'):
                build_preview(self.root, self.artifacts, self.output)
        after = {path.relative_to(self.output): path.read_bytes()
                 for path in self.output.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(list(self.base.glob('.preview-stage-*')))

    def test_equivalent_license_line_endings_keep_exact_source_and_download_bytes(self):
        license_path = self.root / 'LICENSE'
        formatted = license_path.read_bytes().replace(b'\n', b'\r\n') + b'\r\n'

        def reformat_before_capture(root):
            license_path.write_bytes(formatted)
            return source_files(root)

        with patch('preview.source_files', side_effect=reformat_before_capture):
            files = preview_files(self.root, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files['source.zip'])) as archive:
            self.assertEqual(archive.read('LICENSE'), formatted)
        self.assertEqual(files['LICENSE'], formatted)
        self.assertEqual(files['downloads/artifact-manifest.json'],
                         (self.artifacts / 'artifact-manifest.json').read_bytes())

    def test_invalid_captured_license_is_rejected_before_preview_output(self):
        license_path = self.root / 'LICENSE'
        for payload in (b'not MIT text', b'MIT License\n/* grant */',
                        b'MIT License\n\x00', b'MIT License\nremaining\r',
                        b'MIT License\n' + b'x' * 65536, b'MIT License\n\xff'):
            with self.subTest(payload_length=len(payload)):
                license_path.write_bytes(payload)
                with self.assertRaises(ValueError):
                    build_preview(self.root, self.artifacts, self.output)
                self.assertFalse(self.output.exists())
                self.assertFalse(list(self.base.glob('.preview-stage-*')))


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
