"""Clone Hero skin packaging, not native play in the game."""

import colorsys
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

from themeforge import clonehero

ROOT = Path(__file__).resolve().parents[1]
# These values were taken from the installed skin and written down independently of the generator.
INI_SHA256 = {
    "Colors/Clair.ini": "6027f12788ca549111c7fadc06fd63dac53ea7b4a3af7b6213f0922fd4685d8e",
    "Colors/Clair Color.ini": "1af8ddca29aae33f5e7db32b112f808330e9bcf38294b1911788a0d98f01389c",
    "Colors/Obscur.ini": "ba2055f5928b85890b2ac12f65ee59b0e02e6ef0f3adf82b8b3fa699515ec9f6",
    "Colors/Obscur Color.ini": "63f7d3233877165ad2a15822142a6eebbe815e34394fe372fd5f74f5de8bfcaa",
}
STILL_PIXELS_SHA256 = {
    "Clair": "99f0cffe5c7144e6600a72036286b42775c347a88514f3eae808bd758c51d7f0",
    "Obscur": "3191f0fd1ab16fb7eb2965a2d80a190c9cf2d86af4b4fce404b4fe3f8831c783",
}
KEY_ORDER_SHA256 = "c39bcc33181408cbe3e90a68d500771759a723e5286ca0032e41dd75c34d6a10"
CONFIG_SHA256 = "f0cab5da6280a6fa041715a9c8236343a4678d846a4abd51874c209af69fa282"
EXPECTED_PATHS = {
    "LICENSE.txt", "manifest.json", "SHA256SUMS", clonehero.ARCHIVE,
    "Colors/Clair.ini", "Colors/Clair Color.ini", "Colors/Obscur.ini", "Colors/Obscur Color.ini",
    "Video Highways/Clair/highway.webm", "Video Highways/Clair/config.ini",
    "Video Highways/Obscur/highway.webm", "Video Highways/Obscur/config.ini",
    "Highways/Clair Still.png", "Highways/Obscur Still.png",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_profile(data: bytes):
    sections, current = {}, None
    for line in data.decode("utf-8").split("\r\n"):
        if line.startswith("["):
            current = line[1:-1]
            sections[current] = {}
        elif " = " in line:
            key, value = line.split(" = ")
            sections[current][key] = value
    return sections


def decode_png(data: bytes):
    """Read the generator's own RGB PNGs with no filters beyond type 0."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    position, idat, header = 8, b"", None
    while position < len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        body = data[position + 8:position + 8 + length]
        crc = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind not in (b"IEND",):
            raise AssertionError(f"Unexpected chunk {kind!r}")
        position += 12 + length
    width, height, depth, color, _compression, _filter, interlace = header
    raw = zlib.decompress(idat)
    stride = width * 3
    rows = []
    for y in range(height):
        row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        assert row[0] == 0
        rows.append(row[1:])
    return (width, height, depth, color, interlace), rows


class CloneHeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))
        cls.files = clonehero.render_clonehero(cls.document)

    def test_output_has_exactly_the_documented_paths(self):
        self.assertEqual(set(self.files), EXPECTED_PATHS)

    def test_rebuild_is_deterministic_and_matches_recorded_bytes(self):
        again = clonehero.render_clonehero(self.document)
        self.assertEqual(again, self.files)
        for path, digest in INI_SHA256.items():
            self.assertEqual(sha(self.files[path]), digest, path)
        for name in ("Clair", "Obscur"):
            self.assertEqual(sha(self.files[f"Video Highways/{name}/config.ini"]), CONFIG_SHA256)
            self.assertEqual(sha(self.files[f"Video Highways/{name}/highway.webm"]),
                             clonehero.HIGHWAY_SHA256[name])
            (width, height, depth, color, interlace), rows = decode_png(self.files[f"Highways/{name} Still.png"])
            self.assertEqual((width, height, depth, color, interlace), (512, 1024, 8, 2, 0))
            self.assertEqual(sha(b"".join(rows)), STILL_PIXELS_SHA256[name], name)

    def test_every_profile_has_the_183_keys_in_the_reference_order(self):
        order = clonehero.key_order()
        self.assertEqual(len(order), 183)
        self.assertEqual(sha("\n".join(order).encode()), KEY_ORDER_SHA256)
        for path in INI_SHA256:
            data = self.files[path]
            self.assertTrue(data.endswith(b"\r\n"))
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
            profile = parse_profile(data)
            self.assertEqual([f"{s}.{k}" for s, keys in profile.items() for k in keys], order, path)
            for value in (v for keys in profile.values() for v in keys.values()):
                self.assertRegex(value, r"^#[0-9A-F]{6}$")

    def test_black_and_white_profiles_keep_notes_neutral_and_star_power_red(self):
        expectations = {"Clair": ("#242424", "#595854"), "Obscur": ("#FFFFFF", "#BCBCBC")}
        for name, (ink, gray) in expectations.items():
            guitar = parse_profile(self.files[f"Colors/{name}.ini"])["guitar"]
            for lane in ("green", "red", "yellow", "blue", "orange"):
                self.assertEqual(guitar[f"note_{lane}"], ink)
            self.assertEqual(guitar["note_open"], gray)
            self.assertEqual(guitar["note_sp_active"], "#FF0000")
            self.assertEqual(parse_profile(self.files[f"Colors/{name}.ini"])["other"]["general_sp"], "#FF0000")

    def test_color_profiles_use_full_strength_distinct_lanes_and_ink_star_power(self):
        for name, ink in (("Clair", "#242424"), ("Obscur", "#FFFFFF")):
            profile = parse_profile(self.files[f"Colors/{name} Color.ini"])
            lanes = [profile["guitar"][f"note_{lane}"] for lane in ("green", "red", "yellow", "blue", "orange")]
            self.assertEqual(len(set(lanes)), 5)
            for color in lanes:
                r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
                _hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
                # A pale gem has little saturation or little value. Full strength has both at 1.
                self.assertEqual((round(saturation, 3), round(value, 3)), (1.0, 1.0), (name, color))
            self.assertEqual(profile["guitar"]["note_sp_active"], ink)
            self.assertEqual(profile["other"]["general_sp"], ink)

    def test_pinned_highway_videos_are_vp8_at_512_by_1024(self):
        for name in ("Clair", "Obscur"):
            data = self.files[f"Video Highways/{name}/highway.webm"]
            self.assertEqual(data[:4], b"\x1a\x45\xdf\xa3")
            self.assertIn(b"V_VP8", data)
            self.assertIn(b"\xb0\x82\x02\x00", data)   # PixelWidth 512
            self.assertIn(b"\xba\x82\x04\x00", data)   # PixelHeight 1024

    def test_a_tampered_pinned_video_is_refused(self):
        original = clonehero.HIGHWAY_SHA256["Clair"]
        clonehero.HIGHWAY_SHA256["Clair"] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                clonehero.render_clonehero(self.document)
        finally:
            clonehero.HIGHWAY_SHA256["Clair"] = original

    def test_loop_source_repeats_without_a_seam(self):
        theme = self.document["themes"]["Obscur"]
        first = clonehero.frame_rows("Obscur", theme, 0)
        wrapped = clonehero.frame_rows("Obscur", theme, clonehero.FRAMES)
        # The cosine is periodic, so only floating point rounding at an exact half level can differ.
        self.assertLessEqual(max(abs(x - y) for ra, rb in zip(first, wrapped) for x, y in zip(ra, rb)), 1)

        def step(a, b):
            return sum(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))
        steps = [step(clonehero.frame_rows("Obscur", theme, f), clonehero.frame_rows("Obscur", theme, f + 1))
                 for f in (0, 29, clonehero.FRAMES - 1)]
        self.assertLess(max(steps), 1.2 * min(steps))

    def test_still_rails_are_20_solid_pixels_with_a_glow_and_mirror(self):
        for name in ("Clair", "Obscur"):
            theme = self.document["themes"][name]
            _header, rows = decode_png(self.files[f"Highways/{name} Still.png"])
            canvas = bytes(int(theme["canvas"][i:i + 2], 16) for i in (1, 3, 5))
            for row in (rows[0], rows[512]):
                pixels = [row[i:i + 3] for i in range(0, len(row), 3)]
                self.assertEqual(pixels, pixels[::-1])
                self.assertEqual(len(set(pixels[:20])), 1)
                self.assertNotEqual(pixels[20], pixels[19])
                self.assertEqual(pixels[256], canvas)
                self.assertEqual(pixels[200], canvas)

    def test_archive_matches_the_tree_and_carries_no_unrequested_files(self):
        with zipfile.ZipFile(io.BytesIO(self.files[clonehero.ARCHIVE])) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            self.assertEqual(set(names), EXPECTED_PATHS - {"manifest.json", "SHA256SUMS", clonehero.ARCHIVE})
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(archive.read(info), self.files[info.filename])
        self.assertFalse(any(name.endswith((".mp4", ".js")) or "Clair Obscur 4K" in name for name in names))

    def test_manifest_records_identities_and_the_unverified_scope(self):
        manifest = json.loads(self.files["manifest.json"])
        self.assertEqual(manifest["native_acceptance"], "unverified")
        self.assertEqual(manifest["key_count"], 183)
        self.assertEqual(manifest["background_videos"]["in_package"], False)
        self.assertEqual(manifest["background_videos"]["sha256"], clonehero.BACKGROUND_SHA256)
        for record in manifest["files"]:
            self.assertEqual(sha(self.files[record["path"]]), record["sha256"])
            self.assertEqual(len(self.files[record["path"]]), record["bytes"])
        sums = self.files["SHA256SUMS"].decode("ascii")
        for path in EXPECTED_PATHS - {"SHA256SUMS"}:
            self.assertIn(f"{sha(self.files[path])}  {path}\n", sums)

    def test_build_writes_a_new_directory_and_check_compares_without_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "skin"
            clonehero.build_clonehero(self.document, output)
            clonehero.build_clonehero(self.document, output, check=True)
            with self.assertRaises(ValueError):
                clonehero.build_clonehero(self.document, output)
            edited = output / "Colors" / "Obscur.ini"
            edited.write_bytes(edited.read_bytes().replace(b"#FF0000", b"#FF0001"))
            with self.assertRaises(ValueError):
                clonehero.build_clonehero(self.document, output, check=True)
            self.assertIn(b"#FF0001", edited.read_bytes())

    def test_check_refuses_an_extra_empty_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "skin"
            clonehero.build_clonehero(self.document, output)
            (output / "Colors" / "extra").mkdir()
            with self.assertRaises(ValueError):
                clonehero.build_clonehero(self.document, output, check=True)

    def test_output_inside_managed_dist_is_refused(self):
        with self.assertRaises(ValueError):
            clonehero.build_clonehero(self.document, ROOT / "dist" / "clone-hero")

    def test_figure_receipt_agrees_with_its_source_and_outputs(self):
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "render_clonehero_figure.py"), "--check"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_tokens_are_refused(self):
        with self.assertRaises(ValueError):
            clonehero.render_clonehero({"schema_version": 1})


if __name__ == "__main__":
    unittest.main()
