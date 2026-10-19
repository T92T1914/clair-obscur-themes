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

from preview import ICON_ARCHIVE, ICON_CHECKSUMS, LEGACY_ICON_ARCHIVE, PREVIOUS_ICON_ARCHIVE, PORTABLE_ARCHIVE, ROOT, preview_files
from themeforge.build import build_release
from themeforge.icons import render_icons


FUNCTIONS = (
    'phone messages contacts camera gallery settings calendar clock files notes mail '
    'browser maps music video store wallet calculator weather health fitness '
    'voice-recorder home search'
).split()
APPS = (
    ('google-chrome', 'Google Chrome', 'com.android.chrome'),
    ('youtube', 'YouTube', 'com.google.android.youtube'),
    ('google-maps', 'Google Maps', 'com.google.android.apps.maps'),
    ('gmail', 'Gmail', 'com.google.android.gm'),
    ('google-photos', 'Google Photos', 'com.google.android.apps.photos'),
    ('google-messages', 'Google Messages', 'com.google.android.apps.messaging'),
    ('google-calendar', 'Google Calendar', 'com.google.android.calendar'),
    ('google-drive', 'Google Drive', 'com.google.android.apps.docs'),
    ('samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'),
    ('samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'),
    ('samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'),
    ('garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'),
    ('whatsapp', 'WhatsApp', 'com.whatsapp'),
    ('messenger', 'Messenger', 'com.facebook.orca'),
    ('instagram', 'Instagram', 'com.instagram.android'),
    ('facebook', 'Facebook', 'com.facebook.katana'),
    ('snapchat', 'Snapchat', 'com.snapchat.android'),
    ('tiktok', 'TikTok', 'com.zhiliaoapp.musically'),
    ('discord', 'Discord', 'com.discord'),
    ('reddit', 'Reddit', 'com.reddit.frontpage'),
    ('pinterest', 'Pinterest', 'com.pinterest'),
    ('telegram', 'Telegram', 'org.telegram.messenger'),
    ('spotify', 'Spotify', 'com.spotify.music'),
    ('netflix', 'Netflix', 'com.netflix.mediaclient'),
    ('amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'),
    ('walmart', 'Walmart', 'com.walmart.android'),
    ('temu', 'Temu', 'com.einnovation.temu'),
    ('uber', 'Uber', 'com.ubercab'),
    ('doordash', 'DoorDash', 'com.dd.doordash'),
    ('paypal', 'PayPal', 'com.paypal.android.p2pmobile'),
    ('outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'),
    ('chatgpt', 'ChatGPT', 'com.openai.chatgpt'),
    ('firefox', 'Firefox', 'org.mozilla.firefox'),
)
CURRENT_IDS = FUNCTIONS + [row[0] for row in APPS]
GALLERY_IDS = [row[0] for row in APPS] + FUNCTIONS
LABELS = {**{name: name.replace('-', ' ').title() for name in FUNCTIONS},
          **{name: label for name, label, _ in APPS}}


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
        elif tag == 'h4' and self.card is not None:
            self.heading = True
        if tag == 'a':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None
        if tag == 'h4':
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

    def test_current_artwork_archive_matches_gallery_and_preserves_original_archive(self):
        files = preview_files(ROOT, self.artifacts)
        document = json.loads((ROOT / 'tokens.json').read_bytes())
        expected = render_icons(document)
        manifest = json.loads(expected['manifest.json'])
        self.assertEqual(manifest['version'], '0.3.0')
        self.assertEqual(manifest['functions'], CURRENT_IDS)
        self.assertEqual(len(expected), len(CURRENT_IDS) * 2 + 1)
        expected['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        for name, payload in expected.items():
            self.assertEqual(files[f'icons/{name}'], payload)
        with zipfile.ZipFile(io.BytesIO(files[ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), len(CURRENT_IDS) * 2 + 2)
            self.assertEqual(set(archive.namelist()), set(expected))
            for name, payload in expected.items():
                self.assertEqual(archive.read(name), payload)
        legacy = render_icons(document, version='0.1.0')
        legacy['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[LEGACY_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 50)
            self.assertEqual(set(archive.namelist()), set(legacy))
            for name, payload in legacy.items():
                self.assertEqual(archive.read(name), payload)
        self.assertEqual(hashlib.sha256(files[LEGACY_ICON_ARCHIVE]).hexdigest(),
                         '040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34')
        previous = render_icons(document, version='0.2.0')
        previous['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[PREVIOUS_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 50)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous)
        self.assertEqual(hashlib.sha256(files[PREVIOUS_ICON_ARCHIVE]).hexdigest(),
                         '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312')
        self.assertNotEqual(files[ICON_ARCHIVE], files[LEGACY_ICON_ARCHIVE])
        self.assertEqual(files[ICON_CHECKSUMS],
                         ''.join(f'{hashlib.sha256(files[path]).hexdigest()}  {Path(path).name}\n'
                                 for path in (ICON_ARCHIVE, PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE)).encode())
        repeated = preview_files(ROOT, self.artifacts)
        for path in (ICON_ARCHIVE, PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE):
            self.assertEqual(repeated[path], files[path])

    def test_published_and_portable_pages_show_both_appearances_with_local_acquisition(self):
        files = preview_files(ROOT, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as archive:
            portable = {name: archive.read(name) for name in archive.namelist()}
        for delivery in (files, portable):
            with self.subTest(kind='published' if delivery is files else 'portable'):
                page = delivery['index.html'].decode()
                self.assertNotIn('{{', page)
                markup = IconMarkup(page)
                self.assertEqual([card['attrs']['data-icon-function'] for card in markup.cards], GALLERY_IDS)
                for function, card in zip(GALLERY_IDS, markup.cards):
                    label = LABELS[function]
                    self.assertEqual(card['heading'], label)
                    self.assertEqual(card['attrs']['data-icon-kind'], 'function' if function in FUNCTIONS else 'app')
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
                for identifier, _, package in APPS:
                    self.assertIn(f'https://play.google.com/store/apps/details?id={package}', page)
                    self.assertIn(f'<code>{package}</code>', page)
                for path in (ICON_ARCHIVE, PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE, ICON_CHECKSUMS):
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
        for changed_version in ('0.1.0', '0.2.0', '0.3.0'):
            with self.subTest(version=changed_version):
                def changed_grant(document, *, version='0.3.0'):
                    icons = render_icons(document, version=version)
                    if version == changed_version:
                        last = 'Obscur/search.svg'
                        icons[last] = icons[last].replace(b'MIT License', b'Changed grant', 1)
                    return icons

                with patch('preview.render_icons', side_effect=changed_grant):
                    with self.assertRaisesRegex(ValueError, 'Source license differs from the generated icon grant'):
                        preview_files(ROOT, self.artifacts)
                self.assertEqual(snapshot(self.artifacts), self.original)

    def test_current_catalog_cannot_silently_omit_an_app_or_its_visible_label(self):
        for mutation in ('missing-app', 'missing-label'):
            def changed_catalog(document, *, version='0.3.0'):
                files = render_icons(document, version=version)
                if version == '0.3.0':
                    manifest = json.loads(files['manifest.json'])
                    if mutation == 'missing-app':
                        manifest['catalog'] = [entry for entry in manifest['catalog'] if entry['id'] != 'youtube']
                    else:
                        next(entry for entry in manifest['catalog'] if entry['id'] == 'youtube')['label'] = ''
                    files['manifest.json'] = json.dumps(manifest).encode()
                return files
            with self.subTest(mutation=mutation), patch('preview.render_icons', side_effect=changed_catalog):
                with self.assertRaisesRegex(ValueError, 'Icon catalog differs'):
                    preview_files(ROOT, self.artifacts)
            self.assertEqual(snapshot(self.artifacts), self.original)

    def test_current_app_labels_are_escaped_in_headings_and_image_alternatives(self):
        def changed_label(document, *, version='0.3.0'):
            files = render_icons(document, version=version)
            if version == '0.3.0':
                manifest = json.loads(files['manifest.json'])
                next(entry for entry in manifest['catalog'] if entry['id'] == 'youtube')['label'] = '<App & "Name">'
                files['manifest.json'] = json.dumps(manifest).encode()
            return files
        with patch('preview.render_icons', side_effect=changed_label):
            page = preview_files(ROOT, self.artifacts)['index.html'].decode()
        self.assertIn('<h4>&lt;App &amp; &quot;Name&quot;&gt;</h4>', page)
        self.assertIn('alt="Clair &lt;App &amp; &quot;Name&quot;&gt; icon"', page)
        self.assertNotIn('<h4><App', page)


if __name__ == '__main__':
    unittest.main()
