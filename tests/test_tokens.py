import copy
import unittest
from pathlib import Path
from themeforge.tokens import load, validate, contrast, rgb

ROOT=Path(__file__).resolve().parents[1]

class TokenTests(unittest.TestCase):
    def test_wcag_known_black_white_ratio(self):
        self.assertEqual(contrast('#000000','#ffffff'),21)
        self.assertEqual(contrast('#ffffff','#000000'),21)

    def test_both_palettes_pass_actual_role_pairs(self):
        self.assertEqual({x['theme'] for x in validate(load(ROOT/'tokens.json'))},{'Clair','Obscur'})

    def test_low_contrast_secondary_text_is_rejected(self):
        document=copy.deepcopy(load(ROOT/'tokens.json'))
        document['themes']['Clair']['muted']='#dddddd'
        with self.assertRaisesRegex(ValueError,'muted on canvas'):
            validate(document)

    def test_transparency_and_css_expressions_are_not_portable_tokens(self):
        for value in ('#fff','#ffffff00','red','var(--secret)',None):
            with self.subTest(value=value), self.assertRaises(ValueError): rgb(value)

    def test_hovered_control_border_cannot_inherit_a_low_contrast_color(self):
        document=load(ROOT/'tokens.json')
        document['themes']['Clair']['border']='#85837c'
        with self.assertRaisesRegex(ValueError,'border on hover'):
            validate(document)

    def test_incomplete_palette_is_rejected(self):
        document=load(ROOT/'tokens.json'); del document['themes']['Obscur']['error']
        with self.assertRaisesRegex(ValueError,'token roles'): validate(document)
