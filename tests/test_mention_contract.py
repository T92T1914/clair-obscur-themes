import copy
import json
from pathlib import Path
import tempfile
import unittest

from themeforge.build import build_release
from themeforge.tokens import load


ROOT = Path(__file__).resolve().parents[1]


class MentionReleaseContractTests(unittest.TestCase):
    def test_invalid_mention_palette_cannot_replace_a_complete_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'release'
            build_release(ROOT / 'tokens.json', output)
            original = {p.relative_to(output).as_posix():p.read_bytes()
                        for p in output.rglob('*') if p.is_file()}
            for accent, surface in (('#878787', 'selected'), ('#9c9c9c', 'hover')):
                with self.subTest(accent=accent):
                    document = copy.deepcopy(load(ROOT / 'tokens.json'))
                    document['themes']['Obscur']['accent'] = accent
                    source = root / 'invalid-tokens.json'
                    source.write_text(json.dumps(document), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'accent on ' + surface):
                        build_release(source, output)
                    after = {p.relative_to(output).as_posix():p.read_bytes()
                             for p in output.rglob('*') if p.is_file()}
                    self.assertEqual(after, original)
                    self.assertEqual({p.name for p in root.iterdir()},
                                     {'release', 'invalid-tokens.json'})


if __name__ == '__main__':
    unittest.main()
