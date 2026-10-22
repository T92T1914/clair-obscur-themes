"""Versioned icon refinements retain old bytes and clear measured outline collisions."""

import copy
import hashlib
import json
import math
import re
import unittest
import xml.etree.ElementTree as ET

from themeforge import icons


NS = "{http://www.w3.org/2000/svg}"
REFINED_IDS = {
    "ace-hardware", "dollar-general", "fandom", "google-messages",
    "google-translate", "myfitnesspal", "wallpaper-engine", "webtoon",
}

# Canonical sorted path -> SHA256 maps captured from the accepted renderer before
# the refinement. These constants cover every SVG and manifest in each version.
# No machine-local review file is required to execute the preservation test.
HISTORICAL_TREE_DIGESTS = {
    "0.1.0": "72c06eba9b118e2312b150523b5ee2016c11c5d060f2a20ddff07dc736df83e4",
    "0.2.0": "801bd46be5348b7baa88da1a46a514af2312c2e9e04eafb0ec5c1f60e69c96ec",
    "0.3.0": "5a6562768e180d315223ce1588266f596a41c8d46f7e0ef8a69c7e683cae9e90",
    "0.4.0": "f8fc0a2988b946c1eb5b3cf358f556fa81df1ab6d58b4c50069ab280d974f016",
    "0.5.0": "fe5b88f5422aee6c2ab91fd87fe62650618a851e449333fc351eefd1a473e5ed",
    "0.6.0": "47b0f8f653700de375161122866ef9024ace600d688990dfe3393dc841dbe099",
    "0.7.0": "b88a14f7f37e6910e66ad82e81bdf7871158263e1999cdd0e7333989d88b3d17",
    "0.8.0": "56282859ef5a4f1c8346e1494b700a93df06367bd9ea4d0d123fe31ebe66591f",
    "0.9.0": "b8a7a9e7f62ac7aa945580cbeef5629cdbdcdcc40c10da6f82ceaeaa1afcb07b",
    "0.10.0": "afee5c70bf5146b3b86450befc011f701145e1e22ac5ee26679678fd9031752e",
    "0.11.0": "3f339b04c6095804dd733b247dfa4c90312e1cddfcae1b6addeee419644015ce",
    "0.12.0": "9a1eb90c388a9da13bfd5dbfb53d254ab02b21a75c0d73ef9299c5cd7a93be0b",
    "0.13.0": "6ac07e375a480994bb897784ecf9fc68a049945c4a8d89d28338bd749a0f661c",
    "0.14.0": "73ceefa9f86648b74d1c0b75276b08c95e71542744630f654354f783977ce2bb",
    "0.15.0": "c833741df8dba45f5fec21df3dd561b64eb7431c56ad61fc81de830c106015b1",
    "0.16.0": "9c739b1cc6848aace60d9ad978283755d03270d9f72eb4ef8fa71a91c870ae45",
    "0.17.0": "3bec6b354f1d35d8cfedfa8a2f6dfaafbca767de64bd327343f4909708516071",
    "0.18.0": "d814080b0a8892bb500cf2b31f11e9d8d494e7b40284c6d9b2bb26cc6b9598c8",
    "0.19.0": "8902e267b50219a22b68c1c60d448fd86058abe6e20e983bb6a8e41235429d96",
    "0.20.0": "0228d7b01764129bfa214f6e515f594cef016be92aefa7c9ea47b25d13c0957b",
}


# Accepted deterministic SVG archives captured before each refinement.
# The ZIP oracle is independent of the proposed drawing overlay.
HISTORICAL_TREE_DIGESTS["0.21.0"] = "87762a66e397951f3683a1d6c84838d794ae9581674c3181ac70f75f98ae0b4b"

HISTORICAL_ARCHIVE_DIGESTS = {'0.1.0': '040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34',
 '0.2.0': '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312',
 '0.3.0': 'd217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756',
 '0.4.0': 'fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf',
 '0.5.0': '2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a',
 '0.6.0': '241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb',
 '0.7.0': 'aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05',
 '0.8.0': 'fcdaec582be7508b3e62bd9168695ea1650e33c8e53c3de46f3614ae53d833cf',
 '0.9.0': '994ce1d819414b06062d5cd32a03eeb8891e9074b09491dfb2c774a55ae5a3b1',
 '0.10.0': 'a81ffb8c4fb3ef32f3c8391c53016e99246b755ce9079fdee84b5948790ab8e0',
 '0.11.0': '04cce2b812ad4f6ed7bcfda172a9bfe5a6d63d058b6899570a1dbe94f162884d',
 '0.12.0': 'db8ed7e2c62d36786b2c2d510fdf68f83649fda512f6bb018f5043491cb8f0cf',
 '0.13.0': 'e6f7c532d0c625666a0f3403ee27842ac8612e6368d49f64fb3e84b667a42ca1',
 '0.14.0': '4b3324d30b0b6e94a52e0d51a206e499e6e2b6be82052752963da9446c44e6c1',
 '0.15.0': 'df05503c0f1825d09e5b5fb96fcb87401490fef601518ca4e526a6e6d564197c',
 '0.16.0': '3fbf8b53e12ddae6ea354d6ed20a1464c4874192a24f5dee7f231baed0e7f3a0',
 '0.17.0': '0e638e99a265b7b3d5c04e77c3611c732e6b36fa3d26a674e255d89e0c1fd346',
 '0.18.0': '5bbf577f50b3dae894405e598d9ca7d8e6246cac9e7f2859c7b5f5ba0771e985',
 '0.19.0': '22ffaf915634a27adc9608e77d8c0d5bd885bc3bfae323a509f2f566a330334e',
 '0.20.0': 'db1e52859497c2d4852362c1bd5d365a2aab2b6473069bc6aa49c4895d3e0ffa'}

HISTORICAL_ARCHIVE_DIGESTS["0.21.0"] = "504402b2f2b93ea6315a92738487fd4545c949b7f28a10fcaa79f383e7db7caf"

# SVG hashes come from accepted 0.20.0 exports and the exact earlier private
# before/after drawings reviewed at small sizes, not from the new generator.
POLISH_SVG_DIGESTS = {'0.20.0': {'Clair/ai-dungeon.svg': 'c057cf5a944145b0955994a7768f4d56478d26ab2e5a557216cf93d600597709',
            'Obscur/ai-dungeon.svg': '8741fa2de8ecff1eb3098843bfe26ab496add967b12c76e84b1a588f1eb466a9',
            'Clair/usaa.svg': '16195523f6dcdf41d79d48d88a0ac9081babbbfc293f90c6e48324f86f9de232',
            'Obscur/usaa.svg': '9c7c1168d3f7178116c56af9ead2e4f1831ee0b7fcd22fe796846690516d5da0',
            'Clair/discord.svg': 'a9757f4473e1d42edaf0df8a6d55c1ac8778b588fc3137483e40fe945cf7acbd',
            'Obscur/discord.svg': '9705f90bbbf43c55ad92bf2a5ba53b07eb277a9693d4f997c645a72a214e7bd1',
            'Clair/link-to-windows.svg': '62d08622aef944f379cc3154d2b0ae58c7cfe0a776d835e4636647bed31762af',
            'Obscur/link-to-windows.svg': 'c9afb0a1d1687af554361f15523b4190700206f78553d34760bd095841383e00',
            'Clair/chatgpt.svg': 'bd49cd47733d49f21f62908da25901c06376f9647c79f65d01db41ec7ba41c81',
            'Obscur/chatgpt.svg': '21bdad25275b5053de8e1111c04eb28af55fa6018f558d5b0e313d432459445b',
            'Clair/prime-video.svg': 'fde7c193e99f29ce15f2838972c8488e55753e3f98444a42e466bbf382141651',
            'Obscur/prime-video.svg': 'a6b015e68725c0db4d4a93cadf10960c1c1be539d9da9a4c57345d877424b56a',
            'Clair/g2a.svg': 'e6c9065621e842a979d7caf1c5e550738f9798c4f50336d5e97fca76938a99ea',
            'Obscur/g2a.svg': 'f0d4ebacdfe36ef6b286b66219296e090b2fadefa7a2f47dbc99d31209926c49'},
 '0.21.0': {'Clair/ai-dungeon.svg': '770a4c0d6c9d23f52c6aa27bade3eb639ce10d5c3a55db0a8df7e335e9a01c12',
            'Obscur/ai-dungeon.svg': 'ac36a93a13252dfcd01d1be4e32bcc5426680e5c30c9f5c92336c3ce70da8170',
            'Clair/usaa.svg': '843a4746754ac7556f260436ddeb6cadf42f7a7836668446188e54f912253091',
            'Obscur/usaa.svg': 'b590a198c2601e45a6ef6c508e00bb09969c58326223cdecfe291e21f96a316e',
            'Clair/discord.svg': '7b5225a6542550e5807961ab8fd6cb309c81aa5d3402e21fee98b58c432d2fe1',
            'Obscur/discord.svg': '9c3786adc9b53a5978a5adea6bbc26a81baab632ce9257a7b8d1459f46f92a8f',
            'Clair/link-to-windows.svg': '48ddd31fc239bf7d7538c6935233b98d98ce0d17d764db68d898bdbad99b4456',
            'Obscur/link-to-windows.svg': '40e39c2454dc25d00163ce141052a198343cd331a7cd06206b08508d6500f0e1',
            'Clair/chatgpt.svg': '9f17b70deb929be9d319f3ea33c15cf454a59cbe748857d8c346242dbc26f645',
            'Obscur/chatgpt.svg': '9bbe5e5aa19238962fafdff5a0a050a864212d7e2bb29c50a70b1aab4beccce2',
            'Clair/prime-video.svg': '5054522954e82f1189eda56a67ff350b801c62eebad3707a342179294c082907',
            'Obscur/prime-video.svg': '9b0b237f6906047ac4842c8261ec12a5b64cfac1767a6a249b485fa806f440df',
            'Clair/g2a.svg': '56a189b4f25e73f3d1586c136e0835707d8e19f70eb1336370761aea2d204bd3',
            'Obscur/g2a.svg': '09906390e977aa57d0febd90b091900a95e4f89333841b42909072c132e9b7dc'}}
POLISHED_IDS = frozenset(('ai-dungeon', 'usaa', 'discord', 'link-to-windows', 'chatgpt', 'prime-video', 'g2a'))


def _geometry(payload):
    root = ET.fromstring(payload)
    root.attrib.pop("aria-label", None)
    for element in root.iter():
        for attribute in ("fill", "stroke"):
            if re.fullmatch(r"#[0-9a-fA-F]{6}", element.get(attribute, "")):
                element.attrib.pop(attribute)
    return ET.tostring(root)


def _group(files, identifier):
    return ET.fromstring(files[f"Obscur/{identifier}.svg"]).find(NS + "g")


def _path_segments(data):
    """Read the small absolute M/L/H/V/Q/C/Z vocabulary used by these drawings.

    Curves are flattened for outline clearance checks, not treated as their
    control hulls. Straight segments and closed subpaths retain exact endpoints.
    """
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", data)
    index = 0
    point = start = (0.0, 0.0)
    segments = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            segments.append((point, start))
            point = start
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6}
        if command not in counts:
            raise AssertionError(f"Unqualified refinement path command: {command}")
        count = counts[command]
        values = [float(value) for value in tokens[index:index + count]]
        if len(values) != count:
            raise AssertionError("Incomplete refinement SVG path")
        index += count
        if command in ("M", "L"):
            end = tuple(values)
        elif command == "H":
            end = (values[0], point[1])
        elif command == "V":
            end = (point[0], values[0])
        else:
            controls = [point, *zip(values[::2], values[1::2])]
            previous = point
            degree = len(controls) - 1
            for step in range(1, 129):
                t = step / 128
                following = tuple(sum(
                    math.comb(degree, k) * (1 - t) ** (degree - k) * t ** k * control[axis]
                    for k, control in enumerate(controls)) for axis in (0, 1))
                segments.append((previous, following))
                previous = following
            point = controls[-1]
            continue
        if command == "M":
            start = end
        else:
            segments.append((point, end))
        point = end
    return segments


def _point_segment_distance(point, segment):
    start, end = segment
    delta = (end[0] - start[0], end[1] - start[1])
    length_squared = delta[0] ** 2 + delta[1] ** 2
    if not length_squared:
        return math.dist(point, start)
    t = max(0, min(1, ((point[0] - start[0]) * delta[0]
                      + (point[1] - start[1]) * delta[1]) / length_squared))
    nearest = (start[0] + t * delta[0], start[1] + t * delta[1])
    return math.dist(point, nearest)


def _segment_distance(first, second):
    a, b = first
    c, d = second

    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if (cross(a, b, c) * cross(a, b, d) <= 0
            and cross(c, d, a) * cross(c, d, b) <= 0
            and max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
            and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))):
        return 0.0
    return min(_point_segment_distance(a, second), _point_segment_distance(b, second),
               _point_segment_distance(c, first), _point_segment_distance(d, first))


def _segments(element):
    if element.tag == NS + "path":
        return _path_segments(element.get("d"))
    if element.tag == NS + "rect":
        # Only the straight edges relevant to these regressions are needed.
        # Trimming rounded corners keeps the test from inventing square corners.
        x, y, width, height = (float(element.get(name)) for name in ("x", "y", "width", "height"))
        radius = float(element.get("rx", "0"))
        return [((x + radius, y), (x + width - radius, y)),
                ((x + width, y + radius), (x + width, y + height - radius)),
                ((x + radius, y + height), (x + width - radius, y + height)),
                ((x, y + radius), (x, y + height - radius))]
    raise AssertionError(f"Unexpected outline shape: {element.tag}")


def _outline_gap(first, second, stroke_width):
    return min(_segment_distance(a, b) for a in _segments(first)
               for b in _segments(second)) - stroke_width


class IconRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = icons.load_icon_tokens("0.18.0")
        cls.old = icons.render_icons(cls.document, version="0.17.0")
        cls.current = icons.render_icons(cls.document, version="0.18.0")

    def test_all_historical_versions_preserve_every_svg_manifest_and_archive_byte(self):
        from themeforge.build import _zip_bytes
        for version, expected in HISTORICAL_TREE_DIGESTS.items():
            with self.subTest(version=version):
                files = icons.render_icons(icons.load_icon_tokens(version), version=version)
                hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
                digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                self.assertEqual(digest, expected)
                archive = _zip_bytes({**files, "LICENSE.txt": icons.license_text().encode("utf-8")})
                self.assertEqual(hashlib.sha256(archive).hexdigest(),
                                 HISTORICAL_ARCHIVE_DIGESTS[version])

    def test_only_eight_drawings_change_in_both_appearances(self):
        old_manifest = json.loads(self.old["manifest.json"])
        current_manifest = json.loads(self.current["manifest.json"])
        self.assertEqual(current_manifest["version"], "0.18.0")
        self.assertEqual(current_manifest["catalog"], old_manifest["catalog"])
        self.assertEqual(current_manifest["functions"], old_manifest["functions"])
        self.assertEqual(len(current_manifest["catalog"]), 281)
        self.assertEqual(set(self.current), set(self.old))
        changed = {name for name in self.current if name.endswith(".svg")
                   and _geometry(self.current[name]) != _geometry(self.old[name])}
        self.assertEqual(changed, {f"{appearance}/{identifier}.svg"
                                  for appearance in ("Clair", "Obscur") for identifier in REFINED_IDS})
        for name in self.current:
            if name.endswith(".svg") and name not in changed:
                self.assertEqual(self.current[name], self.old[name], name)

    def test_refined_drawings_keep_black_white_palette_geometry_parity_and_stroke(self):
        for identifier in REFINED_IDS:
            with self.subTest(identifier=identifier):
                self.assertEqual(_geometry(self.current[f"Clair/{identifier}.svg"]),
                                 _geometry(self.current[f"Obscur/{identifier}.svg"]))
                for appearance in ("Clair", "Obscur"):
                    root = ET.fromstring(self.current[f"{appearance}/{identifier}.svg"])
                    group = root.find(NS + "g")
                    self.assertGreaterEqual(len(group), 1)
                    self.assertEqual(group.get("stroke-width"), "16")
                    self.assertEqual(group.get("stroke-linecap"), "round")
                    self.assertEqual(group.get("stroke-linejoin"), "round")
                    colors = {value for element in root.iter() for key, value in element.attrib.items()
                              if key in ("fill", "stroke") and value != "none"}
                    self.assertEqual(colors, {"#ffffff", "#000000"})

    def test_removed_tiny_rivets_leave_the_original_tool_and_storefront(self):
        for identifier in ("ace-hardware", "dollar-general"):
            with self.subTest(identifier=identifier):
                old = _group(self.old, identifier)
                current = _group(self.current, identifier)
                self.assertEqual(len(old.findall(NS + "circle")), 1)
                self.assertEqual(current.findall(NS + "circle"), [])
                old_without_rivet = copy.deepcopy(old)
                old_without_rivet.remove(old_without_rivet.find(NS + "circle"))
                # Compare geometry attributes; serialization indentation is irrelevant.
                self.assertEqual([(e.tag, e.attrib) for e in current],
                                 [(e.tag, e.attrib) for e in old_without_rivet])

    def test_messages_rear_outline_clears_the_front_bubble(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "google-messages")
            rear, front = list(group)
            gap = _outline_gap(rear, front, float(group.get("stroke-width")))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertLessEqual(gap, 0)

    def test_translate_rear_card_and_character_clear_the_front_card(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "google-translate")
            front, rear, latin_character, rear_character = list(group)
            self.assertGreater(len(_segments(latin_character)), 0)
            for name, outline in (("rear card", rear), ("rear character", rear_character)):
                gap = _outline_gap(front, outline, float(group.get("stroke-width")))
                with self.subTest(version=label, outline=name):
                    if should_clear:
                        self.assertGreaterEqual(gap, 8)
                    else:
                        self.assertLessEqual(gap, 0)

    def test_fandom_book_and_bubble_are_separate_outlines(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "fandom")
            book, bubble = list(group)
            gap = _outline_gap(book, bubble, float(group.get("stroke-width")))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertLessEqual(gap, 0)

    def test_wallpaper_frame_and_mountain_clear_the_settings_badge(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "wallpaper-engine")
            frame, sun, mountain, badge, ticks = list(group)
            self.assertEqual(sun.tag, NS + "circle")
            self.assertGreater(len(_segments(ticks)), 0)
            self.assertEqual(badge.tag, NS + "circle")
            center = (float(badge.get("cx")), float(badge.get("cy")))
            radius = float(badge.get("r"))
            width = float(group.get("stroke-width"))
            gaps = [min(_point_segment_distance(center, segment) for segment in _segments(outline))
                    - radius - width for outline in (frame, mountain)]
            with self.subTest(version=label):
                if should_clear:
                    self.assertTrue(all(gap >= 8 for gap in gaps), gaps)
                else:
                    self.assertLessEqual(min(gaps), 0, gaps)

    def test_myfitnesspal_plate_has_clear_space_from_both_utensils(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "myfitnesspal")
            plate = group.find(NS + "circle")
            center = (float(plate.get("cx")), float(plate.get("cy")))
            radius = float(plate.get("r"))
            width = float(group.get("stroke-width"))
            gaps = [min(_point_segment_distance(center, segment) for segment in _segments(utensil))
                    - radius - width for utensil in group.findall(NS + "path")]
            self.assertEqual(len(gaps), 2)
            with self.subTest(version=label):
                if should_clear:
                    self.assertTrue(all(gap >= 8 for gap in gaps), gaps)
                else:
                    self.assertLessEqual(min(gaps), 0, gaps)

    def test_webtoon_bubble_has_clear_space_above_the_first_panel_divider(self):
        for label, files, should_clear in (("old", self.old, False), ("current", self.current, True)):
            group = _group(files, "webtoon")
            paths = group.findall(NS + "path")
            horizontal = [segment for segment in _segments(paths[0])
                          if segment[0][1] == segment[1][1]]
            first_divider = min(horizontal, key=lambda segment: segment[0][1])
            bubble = paths[1]
            gap = min(_segment_distance(first_divider, segment) for segment in _segments(bubble))
            gap -= float(group.get("stroke-width"))
            with self.subTest(version=label):
                if should_clear:
                    self.assertGreaterEqual(gap, 8)
                else:
                    self.assertEqual(gap, 0)


class IndividualIconPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = icons.load_icon_tokens("0.21.0")
        cls.old = icons.render_icons(cls.document, version="0.20.0")
        cls.current = icons.render_icons(cls.document, version="0.21.0")

    def test_exact_reviewed_before_and_proposed_svg_identities(self):
        for version, files in (("0.20.0", self.old), ("0.21.0", self.current)):
            for name, expected in POLISH_SVG_DIGESTS[version].items():
                with self.subTest(version=version, name=name):
                    self.assertEqual(hashlib.sha256(files[name]).hexdigest(), expected)

    def test_only_seven_drawings_change_and_other_285_remain_byte_exact(self):
        old_manifest = json.loads(self.old["manifest.json"])
        current_manifest = json.loads(self.current["manifest.json"])
        self.assertEqual(current_manifest["version"], "0.21.0")
        self.assertEqual(set(icons.POLISHED_GLYPHS), POLISHED_IDS)
        self.assertEqual(set(self.current), set(self.old))
        self.assertEqual(len(current_manifest["catalog"]), 292)
        self.assertEqual({key: value for key, value in current_manifest.items()
                          if key not in {"version", "files"}},
                         {key: value for key, value in old_manifest.items()
                          if key not in {"version", "files"}})
        changed = {name for name in self.current if name.endswith(".svg")
                   and self.current[name] != self.old[name]}
        self.assertEqual(changed, {f"{appearance}/{identifier}.svg"
                                   for appearance in ("Clair", "Obscur") for identifier in POLISHED_IDS})
        unchanged = {name for name in self.current if name.endswith(".svg")} - changed
        self.assertEqual(len(unchanged), 2 * 285)
        for name in unchanged:
            self.assertEqual(self.current[name], self.old[name], name)
        for identifier in ("proton-pass", "samsung-notes"):
            for appearance in ("Clair", "Obscur"):
                name = f"{appearance}/{identifier}.svg"
                self.assertIn(name, unchanged)

    def test_polished_geometry_keeps_both_appearances_and_shared_stroke(self):
        for identifier in POLISHED_IDS:
            self.assertEqual(_geometry(self.current[f"Clair/{identifier}.svg"]),
                             _geometry(self.current[f"Obscur/{identifier}.svg"]))
            for appearance in ("Clair", "Obscur"):
                root = ET.fromstring(self.current[f"{appearance}/{identifier}.svg"])
                group = root.find(NS + "g")
                self.assertEqual(group.get("stroke-width"), "16")
                self.assertEqual(group.get("stroke-linecap"), "round")
                self.assertEqual(group.get("stroke-linejoin"), "round")
                colors = {value for element in root.iter() for key, value in element.attrib.items()
                          if key in ("fill", "stroke") and value != "none"}
                self.assertEqual(colors, {"#ffffff", "#000000"})

    def test_ai_dungeon_removes_only_the_decoration_touching_the_book(self):
        old, current = _group(self.old, "ai-dungeon"), _group(self.current, "ai-dungeon")
        self.assertEqual(len(old), 3)
        self.assertEqual(len(current), 2)
        self.assertLessEqual(_outline_gap(old[0], old[2], float(old.get("stroke-width"))), 0)
        self.assertEqual([(e.tag, e.attrib) for e in current],
                         [(e.tag, e.attrib) for e in list(old)[:2]])

    def test_usaa_posts_have_equal_baseline_clearance_instead_of_a_center_tangency(self):
        old, current = _group(self.old, "usaa"), _group(self.current, "usaa")
        self.assertEqual(old[0].attrib, current[0].attrib)
        width = float(current.get("stroke-width"))
        for files, expected_gap in ((self.old, 0), (self.current, 16)):
            segments = _segments(_group(files, "usaa")[1])
            posts = {start[0]: end for start, end in segments
                     if start[0] == end[0] and start[1] == 224}
            self.assertEqual(set(posts), {192, 256, 320})
            baseline = [segment for segment in segments
                        if segment[0][1] == segment[1][1] == 336]
            self.assertEqual(len(baseline), 1)
            self.assertEqual(_point_segment_distance(posts[256], baseline[0]) - width, expected_gap)
            if files is self.current:
                self.assertEqual({point[1] for point in posts.values()}, {304})

    def test_discord_removes_only_the_mouth_merging_into_the_outline(self):
        old, current = _group(self.old, "discord"), _group(self.current, "discord")
        self.assertEqual(len(old), 4)
        self.assertEqual(len(current), 3)
        self.assertLessEqual(_outline_gap(old[0], old[3], float(old.get("stroke-width"))), 0)
        self.assertEqual([(e.tag, e.attrib) for e in current],
                         [(e.tag, e.attrib) for e in list(old)[:3]])
        self.assertEqual(len(current.findall(NS + "circle")), 2)

    def test_link_to_windows_monitor_stops_before_the_foreground_phone(self):
        old, current = _group(self.old, "link-to-windows"), _group(self.current, "link-to-windows")
        self.assertEqual(len(old.findall(NS + "rect")), 2)
        self.assertEqual(len(current.findall(NS + "rect")), 1)
        self.assertEqual(current[2].attrib, old[2].attrib)
        self.assertEqual(current[1].attrib, old[1].attrib)
        self.assertEqual(current[3].attrib, old[3].attrib)
        width = float(current.get("stroke-width"))
        self.assertLessEqual(_outline_gap(old[0], old[2], width), 0)
        self.assertGreaterEqual(_outline_gap(current[0], current[2], width), 16)
        self.assertNotIn("Z", current[0].get("d"))
        self.assertEqual(current[0].get("d").count("M"), 1)

    def test_chatgpt_intact_sparkle_moves_up_to_equal_top_and_bottom_gaps(self):
        old, current = _group(self.old, "chatgpt"), _group(self.current, "chatgpt")
        self.assertEqual(current[0].attrib, old[0].attrib)
        old_star, star = _segments(old[1]), _segments(current[1])
        self.assertEqual(len(star), len(old_star))
        for original, proposed in zip(old_star, star):
            for (x, y), (new_x, new_y) in zip(original, proposed):
                self.assertEqual((new_x, new_y), (x, y - 16))
        width = float(current.get("stroke-width"))
        self.assertLessEqual(_outline_gap(old[0], old[1], width), 0)
        self.assertGreaterEqual(_outline_gap(current[0], current[1], width), 16)
        horizontal = [segment for segment in _segments(current[0])
                      if segment[0][1] == segment[1][1]]
        top, bottom = min(s[0][1] for s in horizontal), max(s[0][1] for s in horizontal)
        star_y = [point[1] for segment in star for point in segment]
        self.assertEqual(min(star_y) - top - width, 16)
        self.assertEqual(bottom - max(star_y) - width, 16)

    def test_prime_video_frame_opens_a_gap_above_the_unchanged_arrow(self):
        old, current = _group(self.old, "prime-video"), _group(self.current, "prime-video")
        self.assertEqual([(e.tag, e.attrib) for e in list(current)[1:]],
                         [(e.tag, e.attrib) for e in list(old)[1:]])
        self.assertEqual({key: value for key, value in current[0].attrib.items()
                          if key not in {"y", "height"}},
                         {key: value for key, value in old[0].attrib.items()
                          if key not in {"y", "height"}})
        width = float(current.get("stroke-width"))
        self.assertLessEqual(_outline_gap(old[0], old[2], width), 0)
        self.assertGreaterEqual(_outline_gap(current[0], current[2], width), 16)
        self.assertEqual((current[0].get("y"), current[0].get("height")), ("160", "176"))

    def test_g2a_intact_plus_moves_right_and_clears_the_ticket_notch(self):
        old, current = _group(self.old, "g2a"), _group(self.current, "g2a")
        self.assertEqual([(e.tag, e.attrib) for e in list(current)[:2]],
                         [(e.tag, e.attrib) for e in list(old)[:2]])
        before, after = _segments(old[2]), _segments(current[2])
        self.assertEqual(len(before), len(after))
        for original, proposed in zip(before, after):
            for (x, y), (new_x, new_y) in zip(original, proposed):
                self.assertEqual((new_x, new_y), (x + 16, y))
        width = float(current.get("stroke-width"))
        self.assertLess(_outline_gap(old[0], old[2], width), 8)
        self.assertGreaterEqual(_outline_gap(current[0], current[2], width), 16)


# Frozen private proposals were rendered and inspected before generator integration.
REVIEWED_SPACING_SVG_DIGESTS = {'Clair/threads.svg': '2b602ac58aedd05316e655f042d670df448f174606db38bc404ca29d1abc2510', 'Obscur/threads.svg': '3c0229df0f580119af1169f2043da8683cee5c26a7670d20fbf07611c5a8461b', 'Clair/evernote.svg': '3cb9e0835dd5c083b9c0b8d9cb1deef541408ed4554ff9af4c8ee38418a2b4d1', 'Obscur/evernote.svg': '624cad9b3ab18aa579acd34b86c473aad82dc182552a2a0dadae73bc1df7289d', 'Clair/myradar.svg': '428d04f7390404fb21e6a439d764eeb129fb970c9961ec4fe3c5a807a4de2e1b', 'Obscur/myradar.svg': '7c291554ce7ebd9d1a7a671f4ec5d1cecc85c7630541f94715fdcbfc3f0ac80d', 'Clair/goodreads.svg': '70a8be6a53fdbfbacfb262990923734a9cad6527c20976b71d39824c25c8b70e', 'Obscur/goodreads.svg': 'a0e6d28693f685e95eb9fc04f0cfe0d911f400cebd2ad1099ba9aa15f3210a03'}

class IconSpacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        document = icons.load_icon_tokens("0.22.0")
        cls.old = icons.render_icons(document, version="0.21.0")
        cls.current = icons.render_icons(document, version="0.22.0")

    def test_only_four_reviewed_drawings_change_and_288_remain_exact(self):
        expected = REVIEWED_SPACING_SVG_DIGESTS
        self.assertEqual(set(self.old), set(self.current))
        actual_changes = {name for name in self.current if name.endswith(".svg")
                          and self.current[name] != self.old[name]}
        self.assertEqual(actual_changes, set(expected))
        self.assertEqual(len(actual_changes), 8)
        self.assertEqual(sum(name.endswith(".svg") and name not in actual_changes
                             for name in self.current), 576)
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(self.current[name]).hexdigest(), digest, name)
        old, current = (json.loads(files["manifest.json"]) for files in (self.old, self.current))
        self.assertEqual(current["version"], "0.22.0")
        self.assertEqual({key: value for key, value in current.items() if key not in {"version", "files"}},
                         {key: value for key, value in old.items() if key not in {"version", "files"}})
        for name in expected:
            identifier = name.split('/')[1][:-4]
            self.assertEqual(_geometry(self.current[f"Clair/{identifier}.svg"]),
                             _geometry(self.current[f"Obscur/{identifier}.svg"]))
            group = _group(self.current, identifier)
            self.assertEqual(group.get("stroke-width"), "16")
            self.assertEqual(group.get("stroke-linecap"), "round")
            self.assertEqual(group.get("stroke-linejoin"), "round")

    def test_evernote_ear_clears_the_top_without_moving_its_bottom(self):
        old, current = _group(self.old, "evernote"), _group(self.current, "evernote")
        self.assertEqual(old[0].attrib, current[0].attrib)
        self.assertEqual(old[2].attrib, current[2].attrib)
        for label, group, expected_gap in (("old", old, 0), ("current", current, 16)):
            ear = group.find(NS + "ellipse")
            center_x = float(ear.get("cx"))
            horizontal = [segment for segment in _segments(group[0])
                          if segment[0][1] == segment[1][1]
                          and min(segment[0][0], segment[1][0]) <= center_x
                          <= max(segment[0][0], segment[1][0])]
            top = min(segment[0][1] for segment in horizontal)
            gap = float(ear.get("cy")) - float(ear.get("ry")) - top - float(group.get("stroke-width"))
            with self.subTest(version=label):
                self.assertEqual(gap, expected_gap)
                self.assertEqual(float(ear.get("cy")) + float(ear.get("ry")), 272)

    def test_goodreads_star_clears_the_unchanged_book_outline(self):
        old, current = _group(self.old, "goodreads"), _group(self.current, "goodreads")
        self.assertEqual([element.attrib for element in old[:2]],
                         [element.attrib for element in current[:2]])
        width = float(current.get("stroke-width"))
        self.assertEqual(_outline_gap(old[0], old[2], width), 0)
        self.assertGreaterEqual(_outline_gap(current[0], current[2], width), 16)

    def test_myradar_filled_blip_clears_both_unchanged_arcs(self):
        old, current = _group(self.old, "myradar"), _group(self.current, "myradar")
        self.assertEqual([element.attrib for element in old[:2]],
                         [element.attrib for element in current[:2]])
        for label, group, should_clear in (("old", old, False), ("current", current, True)):
            dot = group.find(NS + "circle")
            center = float(dot.get("cx")), float(dot.get("cy"))
            gaps = [min(_point_segment_distance(center, segment) for segment in _segments(arc))
                    - float(dot.get("r")) - float(group.get("stroke-width")) for arc in group[:2]]
            with self.subTest(version=label):
                self.assertEqual(dot.get("fill"), "#ffffff")
                if should_clear:
                    self.assertTrue(all(gap >= 12 for gap in gaps), gaps)
                else:
                    self.assertLess(gaps[0], 0)


if __name__ == "__main__":
    unittest.main()
