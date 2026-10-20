"""Inspect the shipped clock resource without requiring an installed font or GUI."""
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib

from garmin import generate_clock_font as producer


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "garmin/watchface/resources/fonts"
CHARACTERS = "-0123456789:"


def descriptor(data):
    records = {}
    for line in data.decode("utf-8").splitlines():
        kind, *fields = shlex.split(line)
        row = dict(field.split("=", 1) for field in fields)
        records.setdefault(kind, []).append(row)
    return records


def rgba_png(data):
    """Independent standard-library PNG reader for the bounded RGBA resource."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Invalid PNG signature")
    position, compressed, chunks = 8, bytearray(), []
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        crc = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise AssertionError("PNG CRC mismatch")
        chunks.append(kind)
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise AssertionError("Expected noninterlaced 8-bit RGBA")
            if not 0 < width * height <= 131072:
                raise AssertionError("Unbounded atlas")
        elif kind == b"IDAT":
            compressed.extend(body)
        position += length + 12
        if kind == b"IEND":
            break
    if position != len(data) or chunks[0] != b"IHDR" or chunks[-1] != b"IEND":
        raise AssertionError("Unexpected PNG structure")
    raw = zlib.decompress(compressed)
    stride = width * 4
    if len(raw) != height * (stride + 1):
        raise AssertionError("Wrong decoded PNG length")
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(height):
        offset = y * (stride + 1)
        method = raw[offset]
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        for i in range(stride):
            left = row[i - 4] if i >= 4 else 0
            up = previous[i]
            upper_left = previous[i - 4] if i >= 4 else 0
            if method == 1:
                prediction = left
            elif method == 2:
                prediction = up
            elif method == 3:
                prediction = (left + up) // 2
            elif method == 4:
                estimate = left + up - upper_left
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
                prediction = (left, up, upper_left)[distances.index(min(distances))]
            elif method == 0:
                prediction = 0
            else:
                raise AssertionError("Invalid PNG row filter")
            row[i] = (row[i] + prediction) & 255
        pixels.extend(row)
        previous = row
    return width, height, pixels


class GarminClockResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {path.name: path.read_bytes() for path in ASSETS.iterdir()}
        cls.fnt = descriptor(cls.files[producer.FONT_FILE])
        cls.common = {key: int(value) for key, value in cls.fnt["common"][0].items()}
        cls.glyphs = {int(row["id"]): {key: int(value) for key, value in row.items()}
                      for row in cls.fnt["char"]}

    def test_exact_subset_resource_and_license_identities(self):
        self.assertEqual(set(self.files), {producer.FONT_FILE, producer.ATLAS_FILE,
                                          "fonts.xml", "LICENSE.txt", "provenance.json"})
        self.assertEqual(set(self.glyphs), set(map(ord, CHARACTERS)))
        self.assertEqual(self.fnt["chars"], [{"count": "12"}])
        self.assertEqual(self.fnt["kernings"], [{"count": "0"}])
        self.assertEqual(self.fnt["page"], [{"id": "0", "file": producer.ATLAS_FILE}])
        self.assertEqual(self.fnt["info"][0]["face"], "Clair Obscur Clock")
        self.assertEqual(self.fnt["info"][0]["size"], "108")
        self.assertEqual(self.common["pages"], 1)
        self.assertEqual(self.common["packed"], 0)
        self.assertEqual(self.common["alphaChnl"], 0)
        for name in ("redChnl", "greenChnl", "blueChnl"):
            self.assertEqual(self.common[name], 4)
        resource = ET.fromstring(self.files["fonts.xml"])
        self.assertEqual(resource.tag, "fonts")
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0].attrib, {"id": "InterClock", "filename": producer.FONT_FILE,
                                            "antialias": "true", "filter": CHARACTERS})
        self.assertEqual(hashlib.sha256(self.files["LICENSE.txt"]).hexdigest(),
                         "262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a")
        self.assertIn(b"Copyright (c) 2016 The Inter Project Authors", self.files["LICENSE.txt"])
        provenance = json.loads(self.files["provenance.json"])
        self.assertEqual(provenance["source"]["sha256"],
                         "288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f")
        self.assertEqual(provenance["source"]["embedded_version"], "Version 4.001;git-9221beed3")
        self.assertEqual(provenance["generation"]["producer_sha256"],
                         hashlib.sha256((ROOT / "garmin/generate_clock_font.py").read_bytes()).hexdigest())
        for name, identity in provenance["files"].items():
            self.assertEqual(len(self.files[name]), identity["bytes"])
            self.assertEqual(hashlib.sha256(self.files[name]).hexdigest(), identity["sha256"])
        self.assertNotIn(b"C:\\", self.files["provenance.json"])
        self.assertNotIn(b"/Users/", self.files["provenance.json"])
        self.assertFalse(any(name.endswith((".ttf", ".otf")) for name in self.files))

    def test_independent_png_decode_glyph_ink_and_nonoverlapping_alpha_rectangles(self):
        width, height, pixels = rgba_png(self.files[producer.ATLAS_FILE])
        self.assertEqual((width, height), (self.common["scaleW"], self.common["scaleH"]))
        covered = bytearray(width * height)
        for glyph in self.glyphs.values():
            x, y, w, h = (glyph[key] for key in ("x", "y", "width", "height"))
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
            self.assertTrue(0 < x < x + w < width and 0 < y < y + h < height)
            self.assertEqual((glyph["page"], glyph["chnl"]), (0, 8))
            ink = []
            for row in range(y, y + h):
                for col in range(x, x + w):
                    index = row * width + col
                    self.assertEqual(covered[index], 0, "Glyph rectangles overlap")
                    covered[index] = 1
                    if pixels[index * 4 + 3]:
                        ink.append((col - x, row - y))
            self.assertTrue(ink)
            self.assertEqual((min(x for x, _ in ink), min(y for _, y in ink)), (0, 0))
            self.assertEqual((max(x for x, _ in ink), max(y for _, y in ink)), (w - 1, h - 1))
        alpha = pixels[3::4]
        self.assertIn(0, alpha)
        self.assertIn(255, alpha)
        self.assertTrue(any(0 < value < 255 for value in alpha), "Antialias coverage is absent")
        for index, value in enumerate(alpha):
            self.assertEqual(pixels[index * 4:index * 4 + 3], b"\xff\xff\xff")
            if not covered[index]:
                self.assertEqual(value, 0, "Unassigned atlas ink")

    def test_all_minutes_in_both_clock_formats_and_invalid_time_fit_the_actual_metrics(self):
        self.assertEqual((self.common["lineHeight"], self.common["base"]), (132, 105))
        self.assertLessEqual(self.common["lineHeight"], 154)
        maximum = {False: 0, True: 0}
        for is24 in (False, True):
            for minute_of_day in range(1440):
                hour, minute = divmod(minute_of_day, 60)
                value = f"{hour:02}:{minute:02}" if is24 else f"{hour % 12 or 12}:{minute:02}"
                cursor = 0
                for character in value:
                    glyph = self.glyphs[ord(character)]
                    self.assertGreater(glyph["xadvance"], 0)
                    self.assertGreaterEqual(cursor + glyph["xoffset"], 0)
                    self.assertLessEqual(cursor + glyph["xoffset"] + glyph["width"],
                                         cursor + glyph["xadvance"])
                    self.assertGreaterEqual(glyph["yoffset"], 0)
                    self.assertLessEqual(glyph["yoffset"] + glyph["height"], self.common["lineHeight"])
                    cursor += glyph["xadvance"]
                self.assertLessEqual(cursor, 380, value)
                maximum[is24] = max(maximum[is24], cursor)
        self.assertEqual(maximum, {False: 302, True: 328})
        self.assertEqual(sum(self.glyphs[ord(c)]["xadvance"] for c in "--:--"), 240)
        self.assertNotEqual(self.glyphs[ord("1")]["xadvance"], self.glyphs[ord("0")]["xadvance"],
                            "This subset makes no tabular-digit feature claim")

    def test_foreign_output_and_changed_missing_extra_resources_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "reserved"
            producer.publish_new(output, self.files)
            producer.verify_existing(output, self.files)
            before = {path.name: path.read_bytes() for path in output.iterdir()}
            with self.assertRaisesRegex(ValueError, "new output directory"):
                producer.publish_new(output, self.files)
            self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)
            for mutation in ("changed", "missing", "extra"):
                fixture = base / mutation
                shutil.copytree(output, fixture)
                if mutation == "changed":
                    (fixture / producer.FONT_FILE).write_bytes(b"owned changed descriptor")
                elif mutation == "missing":
                    (fixture / producer.ATLAS_FILE).unlink()
                else:
                    (fixture / "foreign.txt").write_bytes(b"preserve foreign output")
                expected = {path.name: path.read_bytes() for path in fixture.iterdir()}
                with self.assertRaisesRegex(ValueError, "Font output differs"):
                    producer.verify_existing(fixture, self.files)
                self.assertEqual({path.name: path.read_bytes() for path in fixture.iterdir()}, expected)

    def test_unidentified_font_and_license_fail_without_reserving_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            font = Path(temporary) / "unknown.ttf"
            font.write_bytes(b"unidentified private input")
            with self.assertRaisesRegex(ValueError, "identified Inter Bold"):
                producer.render(font, ASSETS / "LICENSE.txt")
            with self.assertRaisesRegex(ValueError, "filesystem root"):
                producer.publish_new(Path(temporary).anchor, self.files)


@unittest.skipUnless(os.environ.get("THEME_INTER_BOLD_TTF"),
                     "Independent original-font checks need an explicitly supplied THEME_INTER_BOLD_TTF")
class ExplicitInterSourceTests(unittest.TestCase):
    def test_regeneration_matches_every_shipped_byte(self):
        actual = producer.render(Path(os.environ["THEME_INTER_BOLD_TTF"]), ASSETS / "LICENSE.txt")
        self.assertEqual(actual, {path.name: path.read_bytes() for path in ASSETS.iterdir()})

    def test_original_hmetrics_and_independently_rasterized_glyphs_match_the_resource(self):
        from fontTools.ttLib import TTFont
        from PIL import Image, ImageFont
        source = Path(os.environ["THEME_INTER_BOLD_TTF"])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), producer.SOURCE_SHA256)
        font = ImageFont.truetype(str(source), 108, layout_engine=ImageFont.Layout.BASIC)
        records = descriptor((ASSETS / producer.FONT_FILE).read_bytes())
        glyphs = {int(row["id"]): {key: int(value) for key, value in row.items()} for row in records["char"]}
        width, _, pixels = rgba_png((ASSETS / producer.ATLAS_FILE).read_bytes())
        with TTFont(source) as original:
            cmap = original.getBestCmap()
            for character in CHARACTERS:
                glyph = glyphs[ord(character)]
                advance, _ = original["hmtx"][cmap[ord(character)]]
                expected_advance = math.floor(advance * 108 / original["head"].unitsPerEm + 0.5)
                self.assertEqual(glyph["xadvance"], expected_advance)
                mask = font.getmask(character, mode="L")
                independent = Image.frombytes("L", mask.size, bytes(mask))
                independent = independent.crop(independent.getbbox())
                actual = bytes(pixels[((glyph["y"] + y) * width + glyph["x"] + x) * 4 + 3]
                               for y in range(glyph["height"]) for x in range(glyph["width"]))
                self.assertEqual(independent.size, (glyph["width"], glyph["height"]))
                self.assertEqual(actual, independent.tobytes(), character)


if __name__ == "__main__":
    unittest.main()
