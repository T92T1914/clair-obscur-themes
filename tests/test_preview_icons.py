"""Acquire the original icon artwork without changing desktop packages."""

import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from preview import ICON_ARCHIVE, ICON_CHECKSUMS, PORTABLE_ARCHIVE, ROOT, preview_files
from themeforge.build import build_release
from themeforge.icons import render_icons


FUNCTIONS = (
    'phone messages contacts camera gallery settings calendar clock files notes mail '
    'browser maps music video store wallet calculator weather health fitness '
    'voice-recorder home search'
).split()


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


class IconMarkup(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.cards, self.links = [], []
        self.card = None
        self.heading = False
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'icon-card' in attrs.get('class', '').split():
            self.card = {'attrs': attrs, 'images': [], 'heading': ''}
            self.cards.append(self.card)
        elif tag == 'img' and self.card is not None:
            self.card['images'].append(attrs)
        elif tag == 'h3' and self.card is not None:
            self.heading = True
        if tag == 'a':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None
        if tag == 'h3':
            self.heading = False

    def handle_data(self, data):
        if self.heading and self.card is not None:
            self.card['heading'] += data


class PreviewIconTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.artifacts = Path(self.temporary.name) / 'artifacts'
        build_release(ROOT / 'tokens.json', self.artifacts)
        self.original = snapshot(self.artifacts)

    def test_artwork_archive_preserves_every_original_svg_manifest_and_license(self):
        files = preview_files(ROOT, self.artifacts)
        document = json.loads((ROOT / 'tokens.json').read_bytes())
        expected = render_icons(document)
        manifest = json.loads(expected['manifest.json'])
        self.assertEqual(manifest['version'], '0.1.0')
        self.assertEqual(manifest['functions'], FUNCTIONS)
        self.assertEqual(len(expected), 49)
        expected['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        for name, payload in expected.items():
            self.assertEqual(files[f'icons/{name}'], payload)
        with zipfile.ZipFile(io.BytesIO(files[ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 50)
            self.assertEqual(set(archive.namelist()), set(expected))
            for name, payload in expected.items():
                self.assertEqual(archive.read(name), payload)
        digest = hashlib.sha256(files[ICON_ARCHIVE]).hexdigest()
        self.assertEqual(files[ICON_CHECKSUMS],
                         f'{digest}  Clair-Obscur-SVG-Icons-0.1.0.zip\n'.encode())
        self.assertEqual(preview_files(ROOT, self.artifacts)[ICON_ARCHIVE], files[ICON_ARCHIVE])

    def test_published_and_portable_pages_show_both_appearances_with_local_acquisition(self):
        files = preview_files(ROOT, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as archive:
            portable = {name: archive.read(name) for name in archive.namelist()}
        for delivery in (files, portable):
            with self.subTest(kind='published' if delivery is files else 'portable'):
                page = delivery['index.html'].decode()
                self.assertNotIn('{{', page)
                markup = IconMarkup(page)
                self.assertEqual([card['attrs']['data-icon-function'] for card in markup.cards], FUNCTIONS)
                for function, card in zip(FUNCTIONS, markup.cards):
                    label = function.replace('-', ' ')
                    self.assertEqual(card['heading'], label.title())
                    self.assertNotIn('hidden', card['attrs'])
                    self.assertEqual(len(card['images']), 2)
                    for appearance, image in zip(('Clair', 'Obscur'), card['images']):
                        path = f'icons/{appearance}/{function}.svg'
                        self.assertEqual(image['src'], path)
                        self.assertEqual(image['alt'], f'{appearance} {label} icon')
                        self.assertEqual((image['width'], image['height']), ('512', '512'))
                        self.assertEqual(image['decoding'], 'async')
                        self.assertNotIn('loading', image)
                        self.assertNotIn('hidden', image)
                        self.assertEqual(delivery[path], files[path])
                for path in (ICON_ARCHIVE, ICON_CHECKSUMS):
                    links = [link for link in markup.links if link.get('href') == path]
                    self.assertEqual(len(links), 1)
                    self.assertIn('download', links[0])
                    self.assertEqual(delivery[path], files[path])
                manifest = json.loads(delivery['site-manifest.json'])
                for path, payload in delivery.items():
                    if path.startswith('icons/'):
                        self.assertEqual(manifest['files'][path], hashlib.sha256(payload).hexdigest())

    def test_artwork_delivery_keeps_the_original_desktop_tree_and_release_inventory(self):
        files = preview_files(ROOT, self.artifacts)
        self.assertEqual(len(self.original), 32)
        self.assertEqual(snapshot(self.artifacts), self.original)
        downloads = {name.removeprefix('downloads/'): payload
                     for name, payload in files.items() if name.startswith('downloads/')}
        self.assertEqual(downloads, self.original)
        manifest = json.loads(files['downloads/artifact-manifest.json'])
        self.assertEqual(len(manifest['downloads']), 17)
        self.assertEqual(len({item['path'] for item in manifest['downloads']}), 13)
        self.assertFalse(any('icon' in item['path'] for item in manifest['downloads']))
        self.assertNotIn(b'icons/', files['release-SHA256SUMS'])
        self.assertEqual(files['index.html'].count(b'class="download-card"'), 17)

    def test_an_icon_license_read_after_source_capture_cannot_replace_the_captured_grant(self):
        icons = render_icons(json.loads((ROOT / 'tokens.json').read_bytes()))
        last = 'Obscur/search.svg'
        icons[last] = icons[last].replace(b'MIT License', b'Changed grant', 1)
        with patch('preview.render_icons', return_value=icons):
            with self.assertRaisesRegex(ValueError, 'Source license differs from the generated icon grant'):
                preview_files(ROOT, self.artifacts)
        self.assertEqual(snapshot(self.artifacts), self.original)


if __name__ == '__main__':
    unittest.main()
