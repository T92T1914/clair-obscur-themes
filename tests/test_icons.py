"""Original vector geometry, palette consumption and output-preservation checks."""

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from themeforge import icons


ROOT = Path(__file__).resolve().parents[1]
BASE_NAMES = (
    "phone messages contacts camera gallery settings calendar clock files notes mail "
    "browser maps music video store wallet calculator weather health fitness "
    "voice-recorder home search"
).split()
APP_NAMES = (
    "google-chrome youtube google-maps gmail google-photos google-messages google-calendar google-drive "
    "samsung-browser samsung-notes samsung-health garmin-connect whatsapp messenger instagram facebook "
    "snapchat tiktok discord reddit pinterest telegram spotify netflix amazon-shopping walmart temu uber "
    "doordash paypal outlook chatgpt firefox"
).split()
PREVIOUS_APP_NAMES = APP_NAMES[:]
PREVIOUS_NAMES = BASE_NAMES + PREVIOUS_APP_NAMES
NEW_APP_NAMES = (
    "x threads signal twitch capcut disney-plus prime-video microsoft-teams zoom google-meet "
    "google-docs google-sheets onedrive google-translate google-keep google-wallet cash-app venmo "
    "ebay mcdonalds starbucks duolingo waze canva"
).split()
APP_NAMES += NEW_APP_NAMES
SECOND_NAMES = BASE_NAMES + APP_NAMES
THIRD_APP_NAMES = (
    "linkedin github notion microsoft-edge brave microsoft-authenticator "
    "google-authenticator samsung-smartthings"
).split()
APP_NAMES += THIRD_APP_NAMES
THIRD_NAMES = BASE_NAMES + APP_NAMES
FOURTH_APP_NAMES = "good-lock connect-iq-store steam reuters home-depot patreon".split()
APP_NAMES += FOURTH_APP_NAMES
NAMES = BASE_NAMES + APP_NAMES
EXPECTED_APPS = {
    "google-chrome": ("Google Chrome", "com.android.chrome"),
    "youtube": ("YouTube", "com.google.android.youtube"),
    "google-maps": ("Google Maps", "com.google.android.apps.maps"),
    "gmail": ("Gmail", "com.google.android.gm"),
    "google-photos": ("Google Photos", "com.google.android.apps.photos"),
    "google-messages": ("Google Messages", "com.google.android.apps.messaging"),
    "google-calendar": ("Google Calendar", "com.google.android.calendar"),
    "google-drive": ("Google Drive", "com.google.android.apps.docs"),
    "samsung-browser": ("Samsung Browser", "com.sec.android.app.sbrowser"),
    "samsung-notes": ("Samsung Notes", "com.samsung.android.app.notes"),
    "samsung-health": ("Samsung Health", "com.sec.android.app.shealth"),
    "garmin-connect": ("Garmin Connect", "com.garmin.android.apps.connectmobile"),
    "whatsapp": ("WhatsApp", "com.whatsapp"),
    "messenger": ("Messenger", "com.facebook.orca"),
    "instagram": ("Instagram", "com.instagram.android"),
    "facebook": ("Facebook", "com.facebook.katana"),
    "snapchat": ("Snapchat", "com.snapchat.android"),
    "tiktok": ("TikTok", "com.zhiliaoapp.musically"),
    "discord": ("Discord", "com.discord"),
    "reddit": ("Reddit", "com.reddit.frontpage"),
    "pinterest": ("Pinterest", "com.pinterest"),
    "telegram": ("Telegram", "org.telegram.messenger"),
    "spotify": ("Spotify", "com.spotify.music"),
    "netflix": ("Netflix", "com.netflix.mediaclient"),
    "amazon-shopping": ("Amazon Shopping", "com.amazon.mShop.android.shopping"),
    "walmart": ("Walmart", "com.walmart.android"),
    "temu": ("Temu", "com.einnovation.temu"),
    "uber": ("Uber", "com.ubercab"),
    "doordash": ("DoorDash", "com.dd.doordash"),
    "paypal": ("PayPal", "com.paypal.android.p2pmobile"),
    "outlook": ("Microsoft Outlook", "com.microsoft.office.outlook"),
    "chatgpt": ("ChatGPT", "com.openai.chatgpt"),
    "firefox": ("Firefox", "org.mozilla.firefox"),
    "x": ("X", "com.twitter.android"),
    "threads": ("Threads", "com.instagram.barcelona"),
    "signal": ("Signal", "org.thoughtcrime.securesms"),
    "twitch": ("Twitch", "tv.twitch.android.app"),
    "capcut": ("CapCut", "com.lemon.lvoverseas"),
    "disney-plus": ("Disney+", "com.disney.disneyplus"),
    "prime-video": ("Prime Video", "com.amazon.avod.thirdpartyclient"),
    "microsoft-teams": ("Teams", "com.microsoft.teams"),
    "zoom": ("Zoom", "us.zoom.videomeetings"),
    "google-meet": ("Google Meet", "com.google.android.apps.tachyon"),
    "google-docs": ("Google Docs", "com.google.android.apps.docs.editors.docs"),
    "google-sheets": ("Google Sheets", "com.google.android.apps.docs.editors.sheets"),
    "onedrive": ("OneDrive", "com.microsoft.skydrive"),
    "google-translate": ("Google Translate", "com.google.android.apps.translate"),
    "google-keep": ("Google Keep", "com.google.android.keep"),
    "google-wallet": ("Google Wallet", "com.google.android.apps.walletnfcrel"),
    "cash-app": ("Cash App", "com.squareup.cash"),
    "venmo": ("Venmo", "com.venmo"),
    "ebay": ("eBay", "com.ebay.mobile"),
    "mcdonalds": ("McDonald's", "com.mcdonalds.app"),
    "starbucks": ("Starbucks", "com.starbucks.mobilecard"),
    "duolingo": ("Duolingo", "com.duolingo"),
    "waze": ("Waze", "com.waze"),
    "canva": ("Canva", "com.canva.editor"),
    "linkedin": ("LinkedIn", "com.linkedin.android"),
    "github": ("GitHub", "com.github.android"),
    "notion": ("Notion", "notion.id"),
    "microsoft-edge": ("Microsoft Edge", "com.microsoft.emmx"),
    "brave": ("Brave", "com.brave.browser"),
    "microsoft-authenticator": ("Microsoft Authenticator", "com.azure.authenticator"),
    "google-authenticator": ("Google Authenticator", "com.google.android.apps.authenticator2"),
    "samsung-smartthings": ("SmartThings", "com.samsung.android.oneconnect"),
    "good-lock": ("Good Lock", "com.samsung.android.goodlock"),
    "connect-iq-store": ("Connect IQ Store", "com.garmin.connectiq"),
    "steam": ("Steam", "com.valvesoftware.android.steam.community"),
    "reuters": ("Reuters", "com.thomsonreuters.reuters"),
    "home-depot": ("Home Depot", "com.thehomedepot"),
    "patreon": ("Patreon", "com.patreon.android"),
}
NS = "{http://www.w3.org/2000/svg}"


def tree_snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def geometry(svg):
    root = ET.fromstring(svg)
    root.attrib.pop("aria-label", None)
    for element in root.iter():
        for role in ("fill", "stroke"):
            if re.fullmatch(r"#[0-9a-fA-F]{6}", element.get(role, "")):
                element.attrib.pop(role)
    return ET.tostring(root)


def path_hull(data):
    """Conservatively bound absolute line/Bezier paths by endpoints and controls."""
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", data)
    points = []
    x = y = 0
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6}
        if command not in counts:
            raise AssertionError(f"Unqualified SVG path command {command}")
        count = counts[command]
        values = [float(value) for value in tokens[index:index + count]]
        if len(values) != count:
            raise AssertionError("Incomplete SVG path")
        index += count
        if command == "H":
            x = values[0]
            points.append((x, y))
        elif command == "V":
            y = values[0]
            points.append((x, y))
        else:
            points.extend(zip(values[::2], values[1::2]))
            x, y = values[-2:]
    return points


class FunctionalIconTests(unittest.TestCase):
    def setUp(self):
        self.legacy_document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))
        self.document = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))

    def test_exact_function_inventory_and_each_manifest_digest(self):
        files = icons.render_icons(self.document)
        expected = {f"{theme}/{name}.svg" for theme in ("Clair", "Obscur") for name in NAMES}
        self.assertEqual(set(files), expected | {"manifest.json"})
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["functions"], NAMES)
        self.assertEqual(manifest["version"], "0.7.0")
        self.assertEqual(manifest["token_schema"], 1)
        self.assertEqual(manifest["token_version"], "1.0.0")
        self.assertEqual(manifest["palette_variant"], "monochrome")
        self.assertEqual(len(manifest["files"]), 190)
        for record in manifest["files"]:
            self.assertEqual(record["path"], f'{record["appearance"]}/{record["function"]}.svg')
            payload = files[record["path"]]
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
        # Relabeling the same drawing must not count as new geometry.
        relabeled = files["Clair/phone.svg"].replace(b'aria-label="phone"', b'aria-label="messages"')
        self.assertEqual(geometry(relabeled), geometry(files["Clair/phone.svg"]))
        # Named choices must have different drawings, rather than relabeled aliases.
        self.assertEqual(len({geometry(files[f"Clair/{name}.svg"]) for name in NAMES}), 95)

    def test_palette_roles_and_geometry_are_shared_without_hardcoded_colors(self):
        files = icons.render_icons(self.document)
        for name in NAMES:
            self.assertEqual(geometry(files[f"Clair/{name}.svg"]), geometry(files[f"Obscur/{name}.svg"]))
            for theme in ("Clair", "Obscur"):
                root = ET.fromstring(files[f"{theme}/{name}.svg"])
                palette = self.document["themes"][theme]
                self.assertEqual(root.find(NS + "rect").get("fill"), palette["panel"])
                self.assertEqual(root.find(NS + "g").get("stroke"), palette["text"])
                colors = {value for element in root.iter() for key, value in element.attrib.items()
                          if key in ("stroke", "fill") and value != "none"}
                self.assertEqual(colors, {palette["panel"], palette["text"], palette["accent"]})
        # The explicit-document library API remains useful for controlled palette
        # experiments; the CLI and exporter admit the version's shared document.
        files = icons.render_icons(self.legacy_document, version="0.5.0")
        changed = copy.deepcopy(self.legacy_document)
        changed["themes"]["Clair"].update(panel="#fcfbf7", text="#252525", accent="#355e77")
        changed["version"] = "2.3.4"
        updated = icons.render_icons(changed, version="0.5.0")
        for name in THIRD_NAMES:
            self.assertNotEqual(updated[f"Clair/{name}.svg"], files[f"Clair/{name}.svg"])
            self.assertEqual(updated[f"Obscur/{name}.svg"], files[f"Obscur/{name}.svg"])
            self.assertEqual(geometry(updated[f"Clair/{name}.svg"]), geometry(files[f"Clair/{name}.svg"]))
        self.assertEqual(json.loads(updated["manifest.json"])["token_version"], "2.3.4")

    def test_output_is_deterministic_and_does_not_mutate_tokens(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {name: dict(reversed(list(values.items())))
                               for name, values in reversed(list(self.document["themes"].items()))}
        self.assertEqual(icons.render_icons(reordered), icons.render_icons(self.document))
        self.assertEqual(self.document, before)

    def test_current_monochrome_palette_rejects_color_and_impure_endpoints_before_output(self):
        for appearance, background, foreground in (("Clair", "#ffffff", "#000000"),
                                                    ("Obscur", "#000000", "#ffffff")):
            palette = self.document["themes"][appearance]
            self.assertEqual({palette[role].lower() for role in ("canvas", "panel")}, {background})
            self.assertEqual({palette[role].lower() for role in ("text", "accent")}, {foreground})
            self.assertTrue(all(len({color[index:index + 2].lower() for index in (1, 3, 5)}) == 1
                                for color in palette.values()))
        invalid = [self.legacy_document]
        for role, value in (("muted", "#555554"), ("panel", "#fefefe"), ("accent", "#111111")):
            document = copy.deepcopy(self.document)
            document["themes"]["Clair"][role] = value
            invalid.append(document)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaisesRegex(ValueError, "Monochrome"):
                    icons.build_icons(document, output)
                self.assertFalse(output.exists())

    def test_cli_selects_versioned_tokens_and_accepts_only_an_explicit_matching_copy(self):
        self.assertEqual(icons.token_path(), ROOT / "tokens-monochrome.json")
        for version in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"):
            self.assertEqual(icons.token_path(version), ROOT / "tokens.json")
        for version in ("0.6.0", "0.7.0"):
            self.assertEqual(icons.token_path(version), ROOT / "tokens-monochrome.json")
        for version, document in (("0.5.0", self.legacy_document), ("0.6.0", self.document),
                                  ("0.7.0", self.document)):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                explicit = base / "explicit.json"
                explicit.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
                output = base / "icons"
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(icons.main(["--version", version, "--tokens", str(explicit),
                                                "--output", str(output)]), 0)
                self.assertEqual(tree_snapshot(output), icons.render_icons(document, version=version))
                wrong = self.document if version == "0.5.0" else self.legacy_document
                explicit.write_text(json.dumps(wrong), encoding="utf-8")
                unchanged = tree_snapshot(output)
                refused = base / "never-created"
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    icons.main(["--version", version, "--tokens", str(explicit), "--output", str(refused)])
                self.assertEqual(error.exception.code, 1)
                self.assertFalse(refused.exists())
                self.assertEqual(tree_snapshot(output), unchanged)

    def test_svg_has_only_local_geometric_primitives_and_embedded_project_license(self):
        license_body = (ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
        allowed = {"svg", "rect", "g", "path", "line", "circle", "ellipse"}
        for path, payload in icons.render_icons(self.document).items():
            if not path.endswith(".svg"):
                continue
            self.assertIn(license_body, payload.decode())
            root = ET.fromstring(payload)
            labels = {entry["id"]: entry["label"] for entry in icons.icon_catalog()}
            name = Path(path).stem
            self.assertEqual(root.get("aria-label"), labels[name] if name in APP_NAMES else name)
            for element in root.iter():
                self.assertIn(element.tag.removeprefix(NS), allowed)
                for key, value in element.attrib.items():
                    self.assertNotIn("href", key.lower())
                    self.assertFalse(key.lower().startswith("on"))
                    self.assertNotIn("url(", value.lower())
                    self.assertNotIn("font", key.lower())
                self.assertFalse((element.text or "").strip())

    def test_glyph_control_hulls_and_strokes_stay_inside_safe_tile_inset(self):
        for name in NAMES:
            root = ET.fromstring(icons.render_icons(self.document)[f"Clair/{name}.svg"])
            self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")),
                             ("512", "512", "0 0 512 512"))
            tile = root.find(NS + "rect")
            self.assertEqual({key: tile.get(key) for key in ("x", "y", "width", "height", "rx")},
                             {"x": "32", "y": "32", "width": "448", "height": "448", "rx": "104"})
            group = root.find(NS + "g")
            self.assertEqual(group.get("stroke-width"), "16")
            self.assertEqual(group.get("stroke-linecap"), "round")
            self.assertEqual(group.get("stroke-linejoin"), "round")
            for element in group:
                tag = element.tag.removeprefix(NS)
                values = element.attrib
                if tag == "path":
                    points = path_hull(values["d"])
                elif tag == "line":
                    points = [(float(values["x1"]), float(values["y1"])),
                              (float(values["x2"]), float(values["y2"]))]
                elif tag == "rect":
                    x, y, width, height = (float(values[key]) for key in ("x", "y", "width", "height"))
                    points = [(x, y), (x + width, y + height)]
                elif tag in ("circle", "ellipse"):
                    x, y = float(values["cx"]), float(values["cy"])
                    rx, ry = ((float(values["r"]),) * 2 if tag == "circle"
                              else (float(values["rx"]), float(values["ry"])))
                    points = [(x - rx, y - ry), (x + rx, y + ry)]
                else:
                    self.fail(f"Unqualified geometric primitive {tag}")
                self.assertTrue(points)
                for x, y in points:
                    self.assertGreaterEqual(min(x, y), 112, (name, tag, x, y))
                    self.assertLessEqual(max(x, y), 400, (name, tag, x, y))
                    self.assertGreaterEqual(min(x - 8, y - 8), 104)
                    self.assertLessEqual(max(x + 8, y + 8), 408)

    def test_original_version_rebuilds_exact_accepted_archive_and_stays_separate(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        legacy = icons.render_icons(self.legacy_document, version="0.1.0")
        current = icons.render_icons(self.document)
        refined = icons.render_icons(self.legacy_document, version="0.2.0")
        first_apps = icons.render_icons(self.legacy_document, version="0.3.0")
        second_apps = icons.render_icons(self.legacy_document, version="0.4.0")
        third_apps = icons.render_icons(self.legacy_document, version="0.5.0")
        first_monochrome = icons.render_icons(self.document, version="0.6.0")
        archived = {**legacy, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(archived)).hexdigest(),
                         "040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34")
        self.assertEqual(json.loads(legacy["manifest.json"])["stroke_width"], 12)
        refined_archive = {**refined, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(refined_archive)).hexdigest(),
                         "6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312")
        first_archive = {**first_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(first_archive)).hexdigest(),
                         "d217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756")
        second_archive = {**second_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(second_archive)).hexdigest(),
                         "fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf")
        third_archive = {**third_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(third_archive)).hexdigest(),
                         "2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a")
        monochrome_archive = {**first_monochrome, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(monochrome_archive)).hexdigest(),
                         "241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb")
        self.assertEqual(hashlib.sha256(first_monochrome["manifest.json"]).hexdigest(),
                         "57537e0ad06dee704400160d30ae47f4cce8beba557c347ef5236ac8da32ee92")
        first_manifest = json.loads(first_apps["manifest.json"])
        current_manifest = json.loads(current["manifest.json"])
        self.assertEqual(first_manifest["functions"], PREVIOUS_NAMES)
        self.assertEqual(first_manifest["catalog_date"], "2026-10-18")
        self.assertEqual(first_manifest["catalog"], current_manifest["catalog"][:57])
        self.assertEqual(len(first_manifest["files"]), 114)
        for appearance in ("Clair", "Obscur"):
            for name in PREVIOUS_NAMES:
                path = f"{appearance}/{name}.svg"
                self.assertEqual(third_apps[path], first_apps[path])
        second_manifest = json.loads(second_apps["manifest.json"])
        self.assertEqual(second_manifest["functions"], SECOND_NAMES)
        self.assertEqual(second_manifest["catalog_date"], "2026-10-19")
        self.assertEqual(second_manifest["catalog"], current_manifest["catalog"][:81])
        self.assertEqual(len(second_manifest["files"]), 162)
        for appearance in ("Clair", "Obscur"):
            for name in SECOND_NAMES:
                path = f"{appearance}/{name}.svg"
                self.assertEqual(third_apps[path], second_apps[path])
        self.assertEqual(json.loads(third_apps["manifest.json"])["catalog"], current_manifest["catalog"][:89])
        monochrome_manifest = json.loads(first_monochrome["manifest.json"])
        self.assertEqual(monochrome_manifest["functions"], THIRD_NAMES)
        self.assertEqual(monochrome_manifest["catalog"], current_manifest["catalog"][:89])
        self.assertEqual(monochrome_manifest["token_version"], "1.0.0")
        self.assertEqual(monochrome_manifest["palette_variant"], "monochrome")
        self.assertEqual(len(monochrome_manifest["files"]), 178)
        for path, payload in first_monochrome.items():
            if path.endswith(".svg"):
                self.assertEqual(current[path], payload, path)
        self.assertNotIn("palette_variant", json.loads(third_apps["manifest.json"]))
        for path in third_apps:
            if path.endswith(".svg"):
                self.assertNotEqual(current[path], third_apps[path])
                self.assertEqual(geometry(current[path]), geometry(third_apps[path]), path)
        self.assertNotIn("catalog", json.loads(refined["manifest.json"]))
        self.assertNotIn("catalog", json.loads(legacy["manifest.json"]))
        self.assertEqual(json.loads(refined["manifest.json"])["functions"], BASE_NAMES)
        for name in BASE_NAMES:
            self.assertNotEqual(current[f"Clair/{name}.svg"], legacy[f"Clair/{name}.svg"])
            for appearance in ("Clair", "Obscur"):
                self.assertEqual(third_apps[f"{appearance}/{name}.svg"], refined[f"{appearance}/{name}.svg"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "legacy"
            icons.build_icons(self.legacy_document, output, version="0.1.0")
            before = tree_snapshot(output)
            icons.build_icons(self.legacy_document, output, version="0.1.0", check=True)
            with self.assertRaisesRegex(ValueError, "differs"):
                icons.build_icons(self.document, output, check=True)
            self.assertEqual(tree_snapshot(output), before)
        for unsupported in ("0.0.0", "0.8.0", None, [], {}):
            with self.subTest(version=unsupported), self.assertRaisesRegex(ValueError, "Unsupported"):
                icons.render_icons(self.document, version=unsupported)

    def test_named_catalog_has_explicit_unique_assignments_and_accessible_labels(self):
        files = icons.render_icons(self.document)
        manifest = json.loads(files["manifest.json"])
        catalog = manifest["catalog"]
        self.assertEqual([row["id"] for row in catalog], NAMES)
        self.assertEqual([row["kind"] for row in catalog], ["function"] * 24 + ["app"] * 71)
        apps = catalog[24:]
        self.assertEqual(len({row["android_package"] for row in apps}), 71)
        self.assertEqual({row["id"]: (row["label"], row["android_package"]) for row in apps}, EXPECTED_APPS)
        for row in apps:
            self.assertEqual(row["store_url"], "https://play.google.com/store/apps/details?id=" + row["android_package"])
            for appearance in ("Clair", "Obscur"):
                svg = ET.fromstring(files[f'{appearance}/{row["id"]}.svg'])
                self.assertEqual(svg.get("aria-label"), row["label"])
        self.assertIn("Not an ordered popularity chart", manifest["catalog_scope"])
        self.assertEqual(manifest["catalog_date"], "2026-10-19")

    def test_bad_named_catalog_fails_before_output_without_changing_existing_state(self):
        changes = (
            {"id": "../unsafe"}, {"id": "phone"}, {"label": " "},
            {"android_package": "not-a-package"},
            {"android_package": "com.google.android.youtube"},
            {"store_url": "https://example.com/store/apps/details?id=com.android.chrome"},
            {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"},
        )
        for change in changes:
            catalog = copy.deepcopy(icons.APP_CATALOG)
            catalog[0].update(change)
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with patch.object(icons, "APP_CATALOG", catalog), self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_new_catalog_refusals_do_not_change_the_accepted_first_collection(self):
        previous = icons.render_icons(self.legacy_document, version="0.3.0")
        for change in ({"id": "youtube"}, {"android_package": "com.android.chrome"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            invalid = copy.deepcopy(icons.NEW_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "NEW_APP_CATALOG", invalid):
                self.assertEqual(icons.render_icons(self.legacy_document, version="0.3.0"), previous)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())

    def test_third_catalog_refusals_preserve_both_accepted_named_collections(self):
        previous = {version: icons.render_icons(self.legacy_document, version=version)
                    for version in ("0.3.0", "0.4.0")}
        changes = ({"id": "x"}, {"android_package": "com.android.chrome"},
                   {"label": " "}, {"store_title": ""}, {"category": ""},
                   {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})
        for change in changes:
            invalid = copy.deepcopy(icons.THIRD_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "THIRD_APP_CATALOG", invalid):
                for version, files in previous.items():
                    self.assertEqual(icons.render_icons(self.legacy_document, version=version), files)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.THIRD_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("linkedin")
            else:
                drawings["x"] = drawings["linkedin"]
            with self.subTest(drawings=fault), patch.object(icons, "THIRD_APP_GLYPHS", drawings):
                self.assertEqual(icons.render_icons(self.legacy_document, version="0.4.0"), previous["0.4.0"])
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())

    def test_fourth_catalog_and_glyph_refusals_preserve_all_prior_named_collections(self):
        previous = {version: icons.render_icons(icons.load_icon_tokens(version), version=version)
                    for version in ("0.3.0", "0.4.0", "0.5.0", "0.6.0")}
        changes = ({"id": "linkedin"}, {"id": "phone"},
                   {"android_package": "com.garmin.android.apps.connectmobile"},
                   {"label": " "}, {"store_title": ""}, {"category": ""},
                   {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})
        def refuse_without_rewriting_history():
            for version, files in previous.items():
                self.assertEqual(icons.render_icons(icons.load_icon_tokens(version), version=version), files)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
        for change in changes:
            invalid = copy.deepcopy(icons.FOURTH_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "FOURTH_APP_CATALOG", invalid):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.FOURTH_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("good-lock")
            else:
                drawings["linkedin"] = drawings["good-lock"]
            with self.subTest(drawings=fault), patch.object(icons, "FOURTH_APP_GLYPHS", drawings):
                refuse_without_rewriting_history()

    def test_companion_store_titles_remain_distinct_from_short_assignment_labels(self):
        rows = {row["id"]: row for row in icons.icon_catalog()}
        expected = {"good-lock": "Good Lock", "connect-iq-store": "Connect IQ\u2122 Store",
                    "steam": "Steam", "reuters": "Reuters - Breaking World News",
                    "home-depot": "The Home Depot", "patreon": "Patreon"}
        self.assertEqual({name: rows[name]["store_title"] for name in FOURTH_APP_NAMES}, expected)

    def test_current_bubble_has_one_continuous_outline_and_calculator_has_open_equals(self):
        files = icons.render_icons(self.document)
        bubble = ET.fromstring(files["Obscur/messages.svg"]).find(NS + "g")
        self.assertEqual(len(bubble.findall(NS + "rect")), 0)
        outline = bubble.findall(NS + "path")[0].get("d")
        self.assertEqual(outline.count("M"), 1)
        self.assertTrue(outline.endswith("Z"))
        # The tail is part of the perimeter rather than a line over a closed rectangle.
        calculator = ET.fromstring(files["Clair/calculator.svg"]).find(NS + "g")
        operators = calculator.findall(NS + "path")[0].get("d")
        horizontal = re.findall(r"M(\d+) (\d+) H(\d+)", operators)
        # The final two horizontal marks form '='. Measure their real clear gap
        # so merely increasing stroke weight cannot close it again.
        first, second = horizontal[-2:]
        self.assertEqual((first[0], first[2]), (second[0], second[2]))
        width = float(calculator.get("stroke-width"))
        clear_gap = abs(float(second[1]) - float(first[1])) - width
        self.assertGreaterEqual(clear_gap, width)

    def test_fresh_build_and_check_preserve_bytes_and_refuse_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            result = icons.build_icons(self.document, output)
            self.assertEqual(len(result["files"]), 190)
            before = tree_snapshot(output)
            self.assertEqual(before, icons.render_icons(self.document))
            icons.build_icons(self.document, output, check=True)
            self.assertEqual(tree_snapshot(output), before)
            with self.assertRaisesRegex(ValueError, "new output"):
                icons.build_icons(self.document, output)
            self.assertEqual(tree_snapshot(output), before)

    def test_foreign_existing_file_folder_and_empty_folder_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("foreign", "empty"):
                output = base / name
                output.mkdir()
                if name == "foreign":
                    (output / "personal.txt").write_bytes(b"keep this exact file")
                before = tree_snapshot(output)
                for check in (False, True):
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output, check=check)
                    self.assertEqual(tree_snapshot(output), before)
            existing = base / "existing-file"
            existing.write_bytes(b"unchanged")
            with self.assertRaises(ValueError):
                icons.build_icons(self.document, existing)
            self.assertEqual(existing.read_bytes(), b"unchanged")

    def test_check_refuses_changed_missing_extra_file_and_extra_directory_without_repair(self):
        for mutation in ("changed", "missing", "extra-file", "extra-dir", "manifest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                icons.build_icons(self.document, output)
                item = output / "Clair/phone.svg"
                if mutation == "changed":
                    item.write_bytes(item.read_bytes() + b" ")
                elif mutation == "missing":
                    item.unlink()
                elif mutation == "extra-file":
                    (output / "extra.txt").write_bytes(b"preserve")
                elif mutation == "extra-dir":
                    (output / "extra").mkdir()
                else:
                    (output / "manifest.json").write_bytes(b"{}\n")
                before = tree_snapshot(output)
                with self.assertRaisesRegex(ValueError, "differs"):
                    icons.build_icons(self.document, output, check=True)
                self.assertEqual(tree_snapshot(output), before)
                if mutation == "extra-dir":
                    self.assertTrue((output / "extra").is_dir())

    def test_invalid_tokens_are_rejected_before_output_creation(self):
        invalid = [None, [], {**self.document, "schema_version": True},
                   {**self.document, "version": None}, {**self.document, "themes": None}]
        injection = copy.deepcopy(self.document)
        injection["themes"]["Clair"]["accent"] = '#355e77" onload="bad'
        invalid.append(injection)
        contrast = copy.deepcopy(self.document)
        contrast["themes"]["Obscur"]["text"] = contrast["themes"]["Obscur"]["panel"]
        invalid.append(contrast)
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                with self.assertRaises(ValueError):
                    icons.build_icons(document, output)
                self.assertFalse(output.exists())

    def test_managed_dist_and_filesystem_root_are_not_output_targets(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(icons, "ROOT", Path(temporary)):
            for output in (Path(temporary) / "dist", Path(temporary) / "dist/icons", Path(Path(temporary).anchor)):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
            self.assertFalse((Path(temporary) / "dist").exists())

    def test_linked_output_ancestor_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "target"
            target.mkdir()
            (target / "keep.txt").write_bytes(b"unchanged")
            link = base / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink fixture unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "links or reparse"):
                icons.build_icons(self.document, link / "icons")
            self.assertEqual(tree_snapshot(target), {"keep.txt": b"unchanged"})

    def test_cli_requires_output_and_check_does_not_create_missing_tree(self):
        with self.assertRaises(SystemExit) as error:
            icons.main([])
        self.assertEqual(error.exception.code, 2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            self.assertEqual(icons.main(["--output", str(output)]), 0)
            self.assertEqual(icons.main(["--output", str(output), "--check"]), 0)
            before = tree_snapshot(output)
            with self.assertRaises(SystemExit) as existing:
                icons.main(["--output", str(output)])
            self.assertEqual(existing.exception.code, 1)
            self.assertEqual(tree_snapshot(output), before)
            missing = Path(temporary) / "missing"
            with self.assertRaises(SystemExit) as check:
                icons.main(["--output", str(missing), "--check"])
            self.assertEqual(check.exception.code, 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
