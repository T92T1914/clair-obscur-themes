import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
import zipfile

from themeforge.keyboard import ARCHIVE, keyboard_section, render_keyboard
from themeforge.tokens import contrast, load

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'Clair': ('Clair-Gboard-Background.png', 7973, 'da5f4f92115ed5453a57c61d30221782246cec7de9ba70cdf8efeaa5da05f347'),
    'Obscur': ('Obscur-Gboard-Background.png', 6177, '633b9b88e1d2967c755519a84b1845f0d0ba8f392a4cca0715ac77df773b19d6'),
}


class KeyboardTests(unittest.TestCase):
    def setUp(self):
        self.tokens = load(ROOT / 'tokens-monochrome.json')
        self.backgrounds = {name: (ROOT / 'assets/keyboard' / spec[0]).read_bytes() for name, spec in PINS.items()}
        self.guide = (ROOT / 'docs/keyboard-companion.md').read_bytes()
        self.license = (ROOT / 'LICENSE').read_bytes().replace(b'\r\n', b'\n')

    def render(self, backgrounds=None, tokens=None):
        return render_keyboard(tokens or self.tokens, self.backgrounds if backgrounds is None else backgrounds,
                               self.guide, self.license)

    def test_original_backgrounds_and_png_headers_are_pinned_independently(self):
        files = self.render()
        for name, (filename, size, digest) in PINS.items():
            payload = files['backgrounds/' + filename]
            self.assertEqual(len(payload), size)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
            self.assertEqual(payload[:16], b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
            self.assertEqual(struct.unpack('>IIBBBBB', payload[16:29]), (2048, 1024, 8, 2, 0, 0, 0))

    def test_cross_appearance_changed_missing_and_extra_inputs_are_refused(self):
        variants = [dict(reversed(list(self.backgrounds.items())))]
        variants[0]['Clair'], variants[0]['Obscur'] = self.backgrounds['Obscur'], self.backgrounds['Clair']
        variants += [{**self.backgrounds, 'Clair': self.backgrounds['Clair'][:-1]},
                     {'Clair': self.backgrounds['Clair']}, {**self.backgrounds, 'Unknown': b'no'}]
        for background in variants:
            with self.subTest(keys=list(background)):
                with self.assertRaisesRegex(ValueError, 'background'):
                    self.render(background)
        tokens = copy.deepcopy(self.tokens)
        tokens['themes']['Clair']['canvas'] = '#fafafa'
        with self.assertRaisesRegex(ValueError, 'pure monochrome'):
            self.render(tokens=tokens)

    def test_bundle_inventory_hashes_and_external_checksum_are_exact(self):
        files = self.render()
        expected = {'backgrounds/Clair-Gboard-Background.png', 'backgrounds/Obscur-Gboard-Background.png',
                    'installation.md', 'LICENSE.txt', 'palette-reference.json', 'manifest.json', 'SHA256SUMS'}
        self.assertEqual(set(files), expected | {ARCHIVE, 'bundle-SHA256SUMS'})
        self.assertEqual(files, self.render())
        self.assertEqual(files['bundle-SHA256SUMS'],
                         f'{hashlib.sha256(files[ARCHIVE]).hexdigest()}  {ARCHIVE}\n'.encode())
        with zipfile.ZipFile(io.BytesIO(files[ARCHIVE])) as archive:
            self.assertEqual(archive.namelist(), sorted(expected))
            self.assertIsNone(archive.testzip())
            for name in expected:
                self.assertEqual(archive.read(name), files[name])
            checks = archive.read('SHA256SUMS').decode().splitlines()
            self.assertEqual(len(checks), 6)
            for line in checks:
                digest, name = line.split('  ')
                self.assertIn(name, expected - {'SHA256SUMS'})
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
        manifest = json.loads(files['manifest.json'])
        self.assertFalse(manifest['font_binaries_included'])
        self.assertFalse(manifest['native_import_included'])
        for name, record in manifest['files'].items():
            self.assertEqual(record, {'bytes': len(files[name]), 'sha256': hashlib.sha256(files[name]).hexdigest()})

    def test_art_direction_reference_preserves_all_nine_accepted_companion_outputs(self):
        # Captured from the accepted 0.1.0 files, independently of this renderer.
        expected = {
            'Clair-Obscur-Keyboard-Companion-0.1.0.zip': (29085, 'b30d65e2e72d5b077b182193861c16ea92ed6aa0b0d827bdc6c01087fb90b735'),
            'LICENSE.txt': (1065, '4a0c167c3e57f46605c607890e29afd8f26d6f3e5a6915f4163b53710d5fadbd'),
            'SHA256SUMS': (542, '09cf91e6bb18eee19fffc9a277db80cee051d4e2789135da3829b8f884607e5f'),
            'backgrounds/Clair-Gboard-Background.png': PINS['Clair'][1:],
            'backgrounds/Obscur-Gboard-Background.png': PINS['Obscur'][1:],
            'installation.md': (9277, 'e4568243ecae3ee099370d5d71c568ac124435f87a2a364aa2bdcbe18699b8f4'),
            'bundle-SHA256SUMS': (108, '65358d3d78657438da7e3c6e6123d766e04a620decca98ee413b1fe448ddea5d'),
            'manifest.json': (1914, 'c0eea53d1b77222a32e4b460e996e229e7107ac3899ebbbf8e1b58a3dde44d42'),
            'palette-reference.json': (1283, '6841298b234acdd2bf3033c7071a306223323c7be331332691dc078dcd7777ad'),
        }
        files = self.render()
        self.assertEqual(set(files), set(expected))
        for name, (size, digest) in expected.items():
            with self.subTest(path=name):
                self.assertEqual((len(files[name]), hashlib.sha256(files[name]).hexdigest()), (size, digest))

    def test_monochrome_role_map_has_readable_legends_and_boundaries(self):
        palette = json.loads(self.render()['palette-reference.json'])
        for name, field, legend in [('Clair', '#ffffff', '#000000'), ('Obscur', '#000000', '#ffffff')]:
            roles = palette['themes'][name]
            self.assertEqual(roles['keyboard_field'], field)
            self.assertEqual(roles['legend'], legend)
            self.assertGreaterEqual(contrast(roles['legend'], roles['ordinary_key']), 4.5)
            self.assertGreaterEqual(contrast(roles['secondary_legend'], field), 4.5)
            self.assertGreaterEqual(contrast(roles['enter_search_legend'], roles['enter_search']), 4.5)
            self.assertGreaterEqual(contrast(roles['boundary'], field), 3)
        self.assertIn('not a native import', palette['kind'])

    def test_static_platform_routes_distinguish_assets_from_illustrations_and_recipes(self):
        page = keyboard_section(self.tokens)
        self.assertEqual(page.count('class="keyboard-card"'), 4)
        self.assertIn('id="keyboard-chooser" class="paper" hidden', page)
        self.assertNotIn('class="keyboard-card" hidden', page)
        for name, spec in PINS.items():
            self.assertIn(f'href="keyboard/backgrounds/{spec[0]}" download>Download {name}', page)
        self.assertIn('Individual editors not established', page)
        self.assertIn('No Samsung theme file or importer', page)
        self.assertIn('href="#current-source"', page)
        self.assertIn('Illustrations, not native screenshots', page)
        self.assertIn('number row, an example selected suggestion, Shift, Backspace, numeric/symbol mode, Space, punctuation and Enter', page)
        self.assertIn('data-keyboard-modifier="enter">↵</span>', page)
        self.assertNotIn('<button', page)
        self.assertNotIn('C:/', page)

    def test_selected_suggestion_and_number_row_are_explicit_illustrations(self):
        page = keyboard_section(self.tokens)
        self.assertEqual(page.count('class="keyboard-row keyboard-row-numbers"'), 4)
        self.assertEqual(page.count('class="keyboard-suggestion-current">clear</span>'), 4)
        self.assertEqual(page.count('Illustrative selected suggestion, with no automatic correction implied.'), 4)
        self.assertEqual(page.count('Not a native screenshot or typing control.'), 4)
        self.assertIn('background pixels only', page)
        self.assertIn('Preserve native states. Independent editors not promised.', page)
