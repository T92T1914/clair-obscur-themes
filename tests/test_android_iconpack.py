"""Owned encoded-image fixtures qualify resource preparation, not phone behavior."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zlib

from themeforge import android_iconpack as pack
from themeforge.icons import load_icon_tokens, render_icons


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def image(size, color_type=6, *, level=0):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    # Synthetic, compressible RGBA bytes. No renderer or installed font is used.
    scanline = b"\0" + (bytes([level, level, level]) + b"\xff") * size
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, color_type, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanline * size)) + chunk(b"IEND", b""))


def mapping(identifier, package, activity):
    return {"icon_id": identifier, "android_package": package, "activity": activity,
            "component": f"ComponentInfo{{{package}/{activity}}}",
            "source_lines": [12], "source_components": [f"ComponentInfo{{{package}/{activity}}}"],
            "source_types": ["item"]}


VIDEO_EDITOR_ALIASES = (
    ("inshot", "com.camerasideas.instashot", (
        (8904, "com.camerasideas.instashot.DummyActivity"),
        (8905, "com.camerasideas.instashot.MainActivity"),
        (8906, "com.min.n.MainActivity"))),
    ("youcut", "com.camerasideas.trimmer", (
        (21664, "com.camerasideas.instashot.DummyActivity"),
        (21665, "com.camerasideas.instashot.MainActivity"))),
    ("vn-video-editor", "com.frontrow.vlog", (
        (20623, "com.frontrow.vlog.ui.splash.SplashActivity"),)),
    ("kinemaster", "com.nexstreaming.app.kinemasterfree", (
        (9618, "com.kinemaster.app.screen.splash.SplashActivity"),
        (9619, "com.duapps.ad.DuAd"),
        (9620, "com.nexstreaming.kinemaster.ui.splash.SplashActivity"),
        (9621, "com.nextreaming.nexeditorui.MainActivity"))),
    ("powerdirector", "com.cyberlink.powerdirector.DRA140225_01", (
        (14930, "com.cyberlink.powerdirector.splash.SplashActivity"),)),
    ("filmora", "com.wondershare.filmorago", (
        (6058, "com.filmorago.phone.ui.homepage.HomePageActivityNewSinceV570"),
        (6059, "com.wondershare.filmorago.activity.WelcomeActivity"),
        (6060, "com.filmorago.phone.ui.SplashActivity"))),
    ("vivavideo", "com.quvideo.xiaoying", (
        (20530, "com.quvideo.xiaoying.app.splash.SplashActivity"),)),
    ("gopro-quik", "com.gopro.smarty", (
        (15329, "com.gopro.smarty.activity.HomeActivity"),)),
    ("videoshow", "com.xvideostudio.videoeditor", (
        (20360, "com.xvideostudio.videoeditor.activity.SplashRCActivity"),
        (20361, "com.xvideostudio.videoeditor.activity.SplashSubActivity"))),
    ("alight-motion", "com.alightcreative.motion", (
        (604, "com.alightcreative.app.motion.activities.main.SetupActivity"),
        (605, "com.jojoy.delegate.JojoyInstallerActivity"),
        (606, "com.alightcreative.app.motion.activities.ProjectListActivity"),
        (607, "com.alightcreative.app.motion.activities.main.MainActivity"))),
)


def video_editor_mappings():
    rows = []
    for identifier, package, aliases in VIDEO_EDITOR_ALIASES:
        for line, activity in aliases:
            component = f"ComponentInfo{{{package}/{activity}}}"
            rows.append({"icon_id": identifier, "android_package": package, "activity": activity,
                         "component": component, "source_lines": [line],
                         "source_components": [component], "source_types": ["item"]})
    return rows


MESSAGING_ALIASES = (('kakaotalk', 'com.kakao.talk', 9403, 'com.kakao.talk.activity.SplashActivity'), ('line', 'jp.naver.line.android', 10150, 'jp.naver.line.android.activity.SplashActivity'), ('line', 'jp.naver.line.android', 10151, 'jp.naver.line.android.basic_1'), ('line', 'jp.naver.line.android', 10152, 'jp.naver.line.android.design_cherry_blossom'), ('viber', 'com.viber.voip', 20305, 'com.viber.voip.WelcomeActivity.Night'), ('viber', 'com.viber.voip', 20306, 'com.viber.voip.HomeActivity'), ('viber', 'com.viber.voip', 20307, 'com.viber.voip.IdleActivity'), ('viber', 'com.viber.voip', 20308, 'com.viber.voip.LaunchActivity'), ('viber', 'com.viber.voip', 20309, 'com.viber.voip.registration.RegistrationActivity'), ('viber', 'com.viber.voip', 20310, 'com.viber.voip.SplashActivity'), ('viber', 'com.viber.voip', 20311, 'com.viber.voip.ViberApplication'), ('viber', 'com.viber.voip', 20312, 'com.viber.voip.WelcomeActivity'), ('wechat', 'com.tencent.mm', 20967, 'com.tencent.mm.ui.LauncherUI'), ('wechat', 'com.tencent.mm', 20968, 'com.tencent.mm.WeChatActivity'))

def messaging_mappings():
    rows = []
    for identifier, package, line, activity in MESSAGING_ALIASES:
        component = f"ComponentInfo{{{package}/{activity}}}"
        rows.append({"icon_id": identifier, "android_package": package, "activity": activity,
                     "component": component, "source_lines": [line],
                     "source_components": [component], "source_types": ["item"]})
    return rows


ADDED_COMMUNICATION_ALIASES = (
    ("bip", "com.turkcell.bip", 2053, "com.turkcell.bip.ui.main.BipActivity"),
    ("bip", "com.turkcell.bip", 2054, "com.turkcell.bip.ui.main.BipActivityAliasDefault"),
    ("google-chat", "com.google.android.apps.dynamite", 7490, "com.google.android.archive.ReactivateActivity"),
    ("google-chat", "com.google.android.apps.dynamite", 7491, "com.google.android.apps.dynamite.startup.StartUpActivity"),
    ("imo", "com.imo.android.imoim", 8777, "com.google.android.archive.ReactivateActivity"),
    ("imo", "com.imo.android.imoim", 8778, "com.imo.android.imoim.home.Home"),
    ("imo", "com.imo.android.imoim", 8779, "com.imo.android.imoim.activities.Home"),
    ("zalo", "com.zing.zalo", 21844, "com.zing.zalo.ui.SplashActivity"),
)


def added_communication_mappings():
    rows = []
    for identifier, package, line, activity in ADDED_COMMUNICATION_ALIASES:
        component = f"ComponentInfo{{{package}/{activity}}}"
        rows.append({"icon_id": identifier, "android_package": package, "activity": activity,
                     "component": component, "source_lines": [line],
                     "source_components": [component], "source_types": ["item"]})
    return rows


class AndroidIconPackIdentityTests(unittest.TestCase):
    def test_current_pack_configuration_and_qualified_export_pin(self):
        self.assertEqual(pack.ARTWORK_VERSION, "0.32.0")
        self.assertEqual(pack.PNG_MANIFEST_SHA256,
                         "dac3e666c6d9f3f7f09b2175ecafe5b996c15309c42f7e660a5319300da24af2")
        for appearance, package, version, code in (
                ("Clair", "io.github.t92t1914.clairicons", "0.1.5", 6),
                ("Obscur", "io.github.t92t1914.obscuricons", "0.1.16", 17)):
            selected = pack.configuration(appearance)
            self.assertEqual((selected.appearance, selected.package, selected.version, selected.version_code),
                             (appearance, package, version, code))


class AndroidIconPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(prefix="themes-android-export-fixture-")
        cls.export = Path(cls.shared.name) / "png"
        cls.export.mkdir()
        cls.svg = json.loads(render_icons(load_icon_tokens(pack.ARTWORK_VERSION),
                                          version=pack.ARTWORK_VERSION)["manifest.json"])
        canonical_svg = render_icons(load_icon_tokens(pack.ARTWORK_VERSION),
                                     version=pack.ARTWORK_VERSION)["manifest.json"]
        svg_hashes = {row["path"]: row["sha256"] for row in cls.svg["files"]}
        cls.payloads = {size: image(size) for size in (512, 1024)}
        cls.clair_payloads = {size: image(size, level=255) for size in (512, 1024)}
        records = []
        for appearance in ("Clair", "Obscur"):
            for size in (512, 1024):
                directory = cls.export / appearance / str(size)
                directory.mkdir(parents=True)
                for identifier in cls.svg["functions"]:
                    relative = f"{appearance}/{size}/{identifier}.png"
                    raw = (cls.clair_payloads if appearance == "Clair" else cls.payloads)[size]
                    (cls.export / relative).write_bytes(raw)
                    records.append({"path": relative, "appearance": appearance, "function": identifier,
                                    "width": size, "height": size, "bytes": len(raw), "sha256": digest(raw),
                                    "source_svg_sha256": svg_hashes[f"{appearance}/{identifier}.svg"]})
        license_payload = (pack.ROOT / "LICENSE").read_bytes()
        (cls.export / "LICENSE").write_bytes(license_payload)
        cls.document = {"schema_version": 1, "version": "0.32.0", "generator": "clair-obscur-png-export",
                        "exporter_version": "0.11.0", "token_version": "1.0.0", "palette_variant": "monochrome",
                        "tokens_file": "tokens-monochrome.json",
                        "source_manifest_sha256": digest(canonical_svg), "appearances": ["Clair", "Obscur"],
                        "sizes": [512, 1024], "files": records,
                        "license": {"path": "LICENSE", "bytes": len(license_payload), "sha256": digest(license_payload)}}
        cls.document.update({key: cls.svg[key] for key in ("catalog", "functions", "catalog_date", "catalog_scope")})
        for key, name in (("tokens_sha256", "tokens-monochrome.json"), ("svg_generator_sha256", "themeforge/icons.py"),
                          ("svg_craft_sha256", "themeforge/icon_craft.py"),
                          ("svg_catalog_sha256", "themeforge/icon_apps.py"), ("exporter_sha256", "tools/export-icons.mjs")):
            cls.document[key] = digest((pack.ROOT / name).read_bytes())
        (cls.export / "manifest.json").write_bytes(encoded(cls.document))
        cls.fixture_manifest_sha = digest(encoded(cls.document))

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="themes-android-pack-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.components = self.base / "components.json"
        self.output = self.base / "prepared"
        self.table = {"schema_version": 1, "source": copy.deepcopy(pack.COMPONENT_SOURCE),
                      "generic_packages": {"phone": ["com.samsung.android.dialer"],
                                           "browser": ["com.sec.android.app.sbrowser"]},
                      "mappings": [mapping("google-chrome", "com.android.chrome", "com.google.android.apps.chrome.Main"),
                                   mapping("steam", "com.valvesoftware.android.steam.community", "com.valvesoftware.android.steam.MainActivity-default-name"),
                                   mapping("phone", "com.samsung.android.dialer", "com.samsung.android.dialer.DialtactsActivity")]}
        self.write_table()
        self.pin = patch.object(pack, "PNG_MANIFEST_SHA256", self.fixture_manifest_sha)
        self.canonical = patch.object(pack, "COMPONENTS", self.components)
        self.pin.start()
        self.canonical.start()
        self.addCleanup(self.pin.stop)
        self.addCleanup(self.canonical.stop)

    def write_table(self):
        self.components.write_bytes(encoded(self.table))

    def copy_export(self):
        return Path(shutil.copytree(self.export, self.base / "copy"))

    def changed_manifest(self, source, document):
        payload = encoded(document)
        (source / "manifest.json").write_bytes(payload)
        return patch.object(pack, "PNG_MANIFEST_SHA256", digest(payload))

    def refused(self, *, source=None, components=None, output=None, message=None):
        with self.assertRaisesRegex((ValueError, OSError), message or ".+"):
            pack.prepare_iconpack(source or self.export, components or self.components, output or self.output)
        self.assertFalse(self.output.exists())

    def test_exact_resource_bytes_full_components_and_public_catalog(self):
        manifest = pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertEqual(manifest["version"], "0.1.16")
        self.assertEqual(manifest["version_code"], 17)
        self.assertEqual(manifest["counts"]["drawables"], 300)
        self.assertEqual(manifest["counts"]["component_mappings"], 3)
        self.assertEqual(manifest["counts"]["upstream_component_mappings"], 3)
        self.assertEqual(manifest["counts"]["observed_launcher_mappings"], 0)
        self.assertEqual(manifest["counts"]["named_package_hints"], 276)
        appfilter = (self.output / "res/xml/appfilter.xml").read_bytes()
        self.assertEqual(appfilter, (self.output / "assets/appfilter.xml").read_bytes())
        entries = {row.attrib["component"]: row.attrib["drawable"] for row in ET.fromstring(appfilter)}
        self.assertEqual(entries, {
            "ComponentInfo{com.android.chrome/com.google.android.apps.chrome.Main}": "co_google_chrome",
            "ComponentInfo{com.valvesoftware.android.steam.community/com.valvesoftware.android.steam.MainActivity-default-name}": "co_steam",
            "ComponentInfo{com.samsung.android.dialer/com.samsung.android.dialer.DialtactsActivity}": "co_phone",
        })
        self.assertNotIn('component="com.android.chrome"', appfilter.decode())
        manual = ET.parse(self.output / "res/xml/drawable.xml").getroot()
        self.assertEqual(len(manual.findall("item")), 300)
        self.assertEqual(manual.findall("item")[0].attrib, {"drawable": "co_phone"})
        for identifier in self.svg["functions"]:
            self.assertEqual((self.output / f"res/drawable-nodpi/co_{identifier.replace('-', '_')}.png").read_bytes(),
                             (self.export / f"Obscur/512/{identifier}.png").read_bytes())
        catalog = json.loads((self.output / "assets/catalog.json").read_bytes())
        self.assertEqual(set(catalog), {"schema_version", "artwork_version", "pack_version", "packages"})
        self.assertEqual(catalog["pack_version"], "0.1.16")
        self.assertEqual(catalog["artwork_version"], "0.32.0")
        self.assertEqual(next(row for row in catalog["packages"]
                              if row["package"] == "com.google.android.inputmethod.latin"),
                         {"package": "com.google.android.inputmethod.latin", "label": "Gboard", "id": "gboard"})
        self.assertEqual(len(catalog["packages"]), 277)
        self.assertEqual(len({row["package"] for row in catalog["packages"]}), 277)
        self.assertEqual(next(row["id"] for row in catalog["packages"] if row["package"] == "com.sec.android.app.sbrowser"), "samsung-browser")
        self.assertEqual(catalog["packages"][-1], {"package": "com.samsung.android.dialer", "label": "Phone", "id": "phone"})
        for row in manifest["files"]:
            raw = (self.output / row["path"]).read_bytes()
            self.assertEqual((len(raw), digest(raw)), (row["bytes"], row["sha256"]))
        self.assertEqual(json.loads((self.output / "iconpack-manifest.json").read_bytes()), manifest)
        self.assertNotIn(str(self.base), json.dumps(manifest))

    def test_clair_selects_all_light_images_and_a_distinct_literal_identity(self):
        manifest = pack.prepare_iconpack(self.export, self.components, self.output,
                                         appearance="Clair")
        self.assertEqual((manifest["appearance"], manifest["application_id"],
                          manifest["app_label"], manifest["version"], manifest["version_code"]),
                         ("Clair", "io.github.t92t1914.clairicons", "Clair Icons", "0.1.5", 6))
        self.assertEqual(manifest["artwork_version"], "0.32.0")
        self.assertEqual(manifest["counts"]["drawables"], 300)
        self.assertEqual(manifest["counts"]["component_mappings"], 3)
        self.assertEqual(ET.parse(self.output / "res/xml/drawable.xml").find(
            "category").attrib, {"title": "Clair"})
        drawables = list((self.output / "res/drawable-nodpi").glob("*.png"))
        self.assertEqual(len(drawables), 300)
        for target in drawables:
            self.assertEqual(target.read_bytes(), self.clair_payloads[512])
            self.assertNotEqual(target.read_bytes(), self.payloads[512])
        catalog = json.loads((self.output / "assets/catalog.json").read_bytes())
        self.assertEqual(set(catalog), {"schema_version", "artwork_version", "pack_version", "packages"})
        self.assertEqual((catalog["pack_version"], catalog["artwork_version"]), ("0.1.5", "0.32.0"))
        self.assertEqual((self.output / "assets/appfilter.xml").read_bytes(),
                         (self.output / "res/xml/appfilter.xml").read_bytes())

    def test_cross_appearance_image_and_record_are_refused_for_clair(self):
        source = self.copy_export()
        target = source / "Clair/512/phone.png"
        target.write_bytes(self.payloads[512])
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            pack.prepare_iconpack(source, self.components, self.output, appearance="Clair")
        self.assertFalse(self.output.exists())
        target.write_bytes(self.clair_payloads[512])
        document = copy.deepcopy(self.document)
        document["files"][0]["appearance"] = "Obscur"
        with self.changed_manifest(source, document), self.assertRaisesRegex(ValueError, "canonical SVG"):
            pack.prepare_iconpack(source, self.components, self.output, appearance="Clair")
        self.assertFalse(self.output.exists())

    def test_unsupported_appearance_is_refused_before_input_or_output_access(self):
        for appearance in (None, "", "clair", "Both", "Obscur/../Clair", True, {"appearance": "Clair"}):
            with self.subTest(appearance=appearance), self.assertRaisesRegex(ValueError, "Unsupported icon-pack appearance"):
                pack.prepare_iconpack(self.base / "missing-input", self.components,
                                      self.output, appearance=appearance)
            self.assertFalse(self.output.exists())

    def test_default_pin_rejects_an_unqualified_export_before_output(self):
        for previous_pin in ("0731e00b9922ada5537f5258fa9d24ea9f50b7eec6a43098fdc911a4c4bc23aa",
                             "8c7a1f9b76413ecc8886b8cc66244096b42ccba0ad116d40ef626a50a23cf47a",
                             "9851eb483c8588db4712bdabbe73248f43ba8749fd59193da96680c99ce7c636",
                             "9b2fcc10732f4af1489bb20300a08702575d09f92b40f86d3956bb27dc97b303",
                             "2a773020fed10ddb2cd7c47d1c462cedfa6071240d2b0e94565cd599428cb8e8",
                             "40fe3a771b39d9e73adf583dd060f660ef85c88ff961f80a3e3b3635e0f11cb2",
                             "4c955dbac362d37ba35477b623ec79abcb2271ea32b75ed4bf78397f6ac3775a",
                             "a88655c9fa5f5d8e3709c1ef700b4139cb15477a4bbae09c0d46699deb9161e8",
                             "c16df5b56cf8e1c3b9d23017c20250e008c0a2c8866a20a41e16afd5695068b0",
                             "37f462e9d74707802c1b43f242f2604546f04e5b896f5eea7f77afe24c1de643",
                             "4ee13855c06da9b51a57b4559e79ac914b676300800099225aa2d77f9b7b5006",
                             "0a42224b3c9608db506693bd0a6c01f26ee2ee78ebcd2f3eeee54cf5540f4931"):
            with self.subTest(pin=previous_pin), patch.object(pack, "PNG_MANIFEST_SHA256", previous_pin):
                self.refused(message="qualified current artwork manifest")

    def test_previous_artwork_is_not_admitted_by_a_matching_manifest_checksum(self):
        source = self.copy_export()
        for previous_version in ("0.17.0", "0.18.0", "0.19.0", "0.20.0", "0.21.0", "0.22.0", "0.23.0", "0.24.0", "0.25.0", "0.26.0", "0.27.0", "0.28.0", "0.29.0", "0.30.0", "0.31.0"):
            document = copy.deepcopy(self.document)
            document["version"] = previous_version
            with self.subTest(version=previous_version), self.changed_manifest(source, document):
                self.refused(source=source, message="wrong artwork identity")

    def test_existing_output_is_preserved_byte_exact(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_bytes(b"user output")
        with self.assertRaisesRegex(ValueError, "new output"):
            pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"keep.txt"})
        self.assertEqual((self.output / "keep.txt").read_bytes(), b"user output")

    def test_managed_and_traversing_destinations_are_refused(self):
        for output in (pack.ROOT, pack.ROOT / "dist/android-pack", pack.ROOT / "outputs/android-pack",
                       self.base / "child/../escape", self.export / "nested"):
            with self.subTest(output=str(output)):
                self.refused(output=output)

    def test_missing_changed_and_extra_export_files_are_refused(self):
        source = self.copy_export()
        image_path = source / "Obscur/512/phone.png"
        original = image_path.read_bytes()
        image_path.unlink()
        self.refused(source=source)
        image_path.write_bytes(original[:-1] + b"x")
        self.refused(source=source, message="bytes differ")
        image_path.write_bytes(original)
        (source / "foreign.txt").write_bytes(b"do not ingest")
        self.refused(source=source, message="extra entries")

    def test_svg_catalog_and_file_source_identity_are_independent_of_image_hash(self):
        source = self.copy_export()
        for fault in ("catalog", "svg", "source"):
            document = copy.deepcopy(self.document)
            if fault == "catalog":
                document["catalog"][0]["label"] = "Changed label"
            elif fault == "svg":
                document["files"][0]["source_svg_sha256"] = "0" * 64
            else:
                document["exporter_sha256"] = "0" * 64
            with self.subTest(fault=fault), self.changed_manifest(source, document):
                self.refused(source=source)

    def test_traversing_or_duplicate_manifest_record_is_refused_without_reading_target(self):
        source = self.copy_export()
        for relative in ("../../outside.png", self.document["files"][1]["path"]):
            document = copy.deepcopy(self.document)
            if relative.startswith("../"):
                document["files"][0]["path"] = relative
            else:
                document["files"][0] = copy.deepcopy(document["files"][1])
            with self.subTest(relative=relative), self.changed_manifest(source, document):
                self.refused(source=source, message="unsafe PNG path")

    def test_craft_source_identity_is_required_even_with_a_matching_export_pin(self):
        source = self.copy_export()
        for value in (None, "0" * 64):
            document = copy.deepcopy(self.document)
            if value is None:
                document.pop("svg_craft_sha256")
            else:
                document["svg_craft_sha256"] = value
            with self.subTest(value=value), self.changed_manifest(source, document):
                self.refused(source=source, message="PNG export source identity differs")

    def test_RGBA_size_and_chunk_integrity_checks_are_not_hash_only(self):
        source = self.copy_export()
        for raw in (image(512, color_type=2), image(1024), self.payloads[512][:-1] + b"x"):
            document = copy.deepcopy(self.document)
            row = next(x for x in document["files"] if x["path"] == "Obscur/512/phone.png")
            row.update(bytes=len(raw), sha256=digest(raw))
            (source / row["path"]).write_bytes(raw)
            with self.subTest(digest=digest(raw)), self.changed_manifest(source, document):
                self.refused(source=source, message="RGBA|checksum")

    def test_components_must_match_canonical_copy_and_pinned_upstream(self):
        alternate = self.base / "alternate.json"
        changed = copy.deepcopy(self.table)
        changed["mappings"][0]["activity"] += "Guessed"
        alternate.write_bytes(encoded(changed))
        self.refused(components=alternate, message="canonical table")
        self.table["source"]["revision"] = "0" * 40
        self.write_table()
        self.refused(message="source or table schema")

    def test_same_component_file_cannot_change_between_explicit_and_canonical_reads(self):
        first = encoded(self.table)
        second = json.dumps(self.table).encode()
        self.assertNotEqual(first, second)
        with patch.object(pack, "_read", side_effect=[first, second]):
            with self.assertRaisesRegex(ValueError, "changed during admission"):
                pack._components(self.components, self.svg["catalog"])

    def test_observed_launcher_alias_is_exact_and_separate_from_upstream_evidence(self):
        observed = {"icon_id": "credit-one", "android_package": "com.creditonebank.mobile",
                    "activity": "yFqmd7.jD9Zj6.ePOZ69.xSZja1.kgEjG0.aPkpo8.xqV1b4",
                    "source_kind": "observed-launcher", "observed_on": "2026-10-21"}
        observed["component"] = f'ComponentInfo{{{observed["android_package"]}/{observed["activity"]}}}'
        self.table["mappings"].append(observed)
        self.write_table()
        manifest = pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertEqual(manifest["counts"]["upstream_component_mappings"], 3)
        self.assertEqual(manifest["counts"]["observed_launcher_mappings"], 1)
        self.assertEqual(manifest["source"]["component_source"], pack.COMPONENT_SOURCE)
        item = next(row for row in ET.parse(self.output / "assets/appfilter.xml").getroot()
                    if row.attrib["component"] == observed["component"])
        self.assertEqual(item.attrib, {"component": observed["component"], "drawable": "co_credit_one"})

    def test_observation_metadata_is_bounded_and_cannot_claim_upstream_provenance(self):
        observed = {"icon_id": "ace-hardware", "android_package": "com.acehardware.rewards",
                    "activity": "com.acehardware.MainActivity",
                    "component": "ComponentInfo{com.acehardware.rewards/com.acehardware.MainActivity}",
                    "source_kind": "observed-launcher", "observed_on": "2026-10-21"}
        faults = [({"source_kind": "upstream"}, ()), ({}, ("source_kind",)),
                  ({}, ("observed_on",)), ({"observed_on": "2026-02-30"}, ()),
                  ({"observed_on": "20261021"}, ()), ({"observed_on": "2026-10-21T12:00:00"}, ()),
                  ({"observed_on": True}, ()), ({"private_path": "not public evidence"}, ())]
        faults += [({field: []}, ()) for field in ("source_lines", "source_components", "source_types")]
        for changes, removed in faults:
            row = {**observed, **changes}
            for field in removed:
                del row[field]
            self.table["mappings"] = [row]
            self.write_table()
            with self.subTest(changes=changes, removed=removed), self.assertRaises(ValueError):
                pack._components(self.components, self.svg["catalog"])

    def test_canonical_observations_keep_upstream_rows_and_public_package_scope(self):
        table = json.loads((pack.ROOT / "android/iconpack/components.json").read_bytes())
        observed = [row for row in table["mappings"] if "source_kind" in row]
        upstream = [row for row in table["mappings"] if "source_kind" not in row]
        self.assertEqual(len(upstream), 1343)
        self.assertEqual(len(observed), 12)
        self.assertEqual(table["source"], pack.COMPONENT_SOURCE)
        self.assertEqual(digest(json.dumps(table["mappings"][:1354], sort_keys=True, separators=(",", ":")).encode()),
                         "af2fe774168d48ab21634202263d37662947df861fa24e2e675b2c7bd13f913e")
        self.assertEqual(observed[-1], {"icon_id": "dominos", "android_package": "com.dominospizza",
                                      "activity": "com.dominospizza.SplashScreenActivity",
                                      "component": "ComponentInfo{com.dominospizza/com.dominospizza.SplashScreenActivity}",
                                      "source_kind": "observed-launcher", "observed_on": "2026-10-29"})
        # New aliases are appended after the exact 0.1.1 mapping sequence.
        self.assertEqual(digest(json.dumps(table["mappings"][:1306], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "e5d74a6eebc2f464fa358e4eb03f9da4ca270e4a1abcc34a829a795a383a0cdf")
        # Fixed pre-update data identities preserve every original upstream row and generic package.
        self.assertEqual(digest(json.dumps(upstream[:1295], sort_keys=True, separators=(",", ":")).encode()),
                         "2e7fa952aaa72670293903b543368f43784011ff79b1e0cd038a47c1b11455ec")
        self.assertEqual(digest(json.dumps(table["generic_packages"], sort_keys=True, separators=(",", ":")).encode()),
                         "b05c80373bcfad970ba6442160bcbb1dfc2bd75d857f2d4790660f16a7e0d3cd")
        expected = {
            "ace-hardware": ("com.acehardware.rewards", "com.acehardware.MainActivity"),
            "chick-fil-a": ("com.chickfila.cfaflagship", "com.chickfila.cfaflagship.RetroTheme"),
            "credit-one": ("com.creditonebank.mobile", "yFqmd7.jD9Zj6.ePOZ69.xSZja1.kgEjG0.aPkpo8.xqV1b4"),
            "dollar-general": ("com.dollargeneral.android", "dgapp2.dollargeneral.com.dgapp2_android.SplashActivity"),
            "g2a": ("com.g2a.marketplace", "com.g2a.marketplace.MainActivity"),
            "home-depot": ("com.thehomedepot", "com.thehomedepot.startup.activities.StartupActivity"),
            "mcdonalds": ("com.mcdonalds.app", "com.mcdonalds.app.LauncherMonopoly"),
            "mochi-health": ("com.mochihealth.mochihealth", "com.mochihealth.mochihealth.MainActivity"),
            "shonen-jump": ("com.viz.wsj.android", "com.vizmanga.android.vizmangalib.splash.SplashActivity"),
            "sonic": ("com.sonic.sonicdrivein", "com.idpwhitelabel.MainActivity"),
            "wendys": ("com.wendys.nutritiontool", "com.wendys.nutritiontool.AppIconPrimary"),
        }
        self.assertEqual({row["icon_id"]: (row["android_package"], row["activity"]) for row in observed if row["observed_on"] == "2026-10-21"}, expected)
        catalog = {row["id"]: row for row in self.svg["catalog"] if row["kind"] == "app"}
        for row in observed:
            self.assertEqual(set(row), {"icon_id", "android_package", "activity", "component", "source_kind", "observed_on"})
            self.assertEqual(row["source_kind"], "observed-launcher")
            self.assertIn(row["observed_on"], ("2026-10-21", "2026-10-29"))
            self.assertEqual(row["android_package"], catalog[row["icon_id"]]["android_package"])
            self.assertEqual(row["component"], f'ComponentInfo{{{row["android_package"]}/{row["activity"]}}}')
        self.assertEqual(len({row["android_package"] for row in table["mappings"] if row["icon_id"] in catalog}), 264)

    def test_canonical_gboard_mappings_keep_exact_upstream_aliases_and_line_evidence(self):
        table = json.loads((pack.ROOT / "android/iconpack/components.json").read_bytes())
        gboard = [row for row in table["mappings"] if row["icon_id"] == "gboard"]
        expected = (
            (7121, "com.android.inputmethod.latin.setup.SetupActivity"),
            (7122, "com.google.android.apps.inputmethod.libs.framework.core.LauncherActivity"),
            (7123, "com.google.android.libraries.inputmethod.launcher.LauncherActivity"),
            (7126, "com.google.android.archive.ReactivateActivity"),
        )
        self.assertEqual(len(table["mappings"]), 1355)
        self.assertEqual(len(gboard), 4)
        for row, (line, activity) in zip(gboard, expected):
            component = f"ComponentInfo{{com.google.android.inputmethod.latin/{activity}}}"
            self.assertEqual(row, {"icon_id": "gboard", "android_package": "com.google.android.inputmethod.latin",
                                   "activity": activity, "component": component,
                                   "source_lines": [line], "source_components": [component], "source_types": ["item"]})
        self.assertEqual(table["mappings"][1306:1310], gboard)

    def test_canonical_video_editor_aliases_append_only_exact_pinned_declarations(self):
        table = json.loads((pack.ROOT / "android/iconpack/components.json").read_bytes())
        self.assertEqual(digest(json.dumps(table["mappings"][:1310], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "850bacf5285bd69a61c4b672fcec603010c594af13d10cc7a13e2c78123688a9")
        expected = video_editor_mappings()
        self.assertEqual(len(expected), 22)
        self.assertEqual(table["mappings"][1310:1332], expected)
        self.assertEqual(len(table["mappings"]), 1355)
        catalog = {row["id"]: row for row in self.svg["catalog"] if row["kind"] == "app"}
        for identifier, package, aliases in VIDEO_EDITOR_ALIASES:
            self.assertEqual(catalog[identifier]["android_package"], package)
            self.assertEqual(sum(row["icon_id"] == identifier for row in expected), len(aliases))
        # These are pinned declarations, including opaque historical names, not observations.
        self.assertTrue(all("source_kind" not in row and "observed_on" not in row for row in expected))

    def test_video_editor_components_emit_their_named_drawables_without_package_fallback(self):
        expected = video_editor_mappings()
        self.table["mappings"].extend(expected)
        self.write_table()
        manifest = pack.prepare_iconpack(self.export, self.components, self.output)
        entries = {row.attrib["component"]: row.attrib["drawable"]
                   for row in ET.parse(self.output / "assets/appfilter.xml").getroot()}
        self.assertEqual(manifest["counts"]["component_mappings"], 25)
        self.assertEqual(manifest["counts"]["observed_launcher_mappings"], 0)
        for row in expected:
            self.assertEqual(entries[row["component"]], "co_" + row["icon_id"].replace("-", "_"))
            self.assertNotIn(row["android_package"], entries)

    def test_messaging_aliases_append_only_exact_pinned_source_declarations(self):
        table = json.loads((pack.ROOT / "android/iconpack/components.json").read_bytes())
        self.assertEqual(digest(json.dumps(table["mappings"][:1332], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "56d1b25a1114ad578b96005816a818f226f0985386b161318f1c731f53a875fc")
        expected = messaging_mappings()
        self.assertEqual(len(expected), 14)
        self.assertEqual(table["mappings"][1332:1346], expected)
        self.assertEqual(len(table["mappings"]), 1355)
        self.assertEqual({identifier: sum(row["icon_id"] == identifier for row in expected)
                          for identifier in ("line", "viber", "wechat", "kakaotalk")},
                         {"line": 3, "viber": 8, "wechat": 2, "kakaotalk": 1})
        self.assertTrue(all("source_kind" not in row and "observed_on" not in row for row in expected))

    def test_messaging_components_emit_distinct_named_resources_without_fallback(self):
        expected = messaging_mappings()
        self.table["mappings"].extend(expected)
        self.write_table()
        manifest = pack.prepare_iconpack(self.export, self.components, self.output)
        entries = {row.attrib["component"]: row.attrib["drawable"]
                   for row in ET.parse(self.output / "assets/appfilter.xml").getroot()}
        self.assertEqual(manifest["counts"]["component_mappings"], 17)
        for row in expected:
            self.assertEqual(entries[row["component"]], "co_" + row["icon_id"])
            self.assertNotIn(row["android_package"], entries)


    def test_added_communication_aliases_preserve_the_full_prior_sequence(self):
        table = json.loads((pack.ROOT / "android/iconpack/components.json").read_bytes())
        self.assertEqual(digest(json.dumps(table["mappings"][:1346], sort_keys=True,
                                          separators=(",", ":")).encode()),
                         "4920709f697a2d8ef489c0611e7c8d04c34a8e70a6e16d78bf728f684d9f22e0")
        expected = added_communication_mappings()
        self.assertEqual(len(expected), 8)
        self.assertEqual(table["mappings"][1346:1354], expected)
        self.assertEqual(len(table["mappings"]), 1355)
        self.assertEqual({identifier: sum(row["icon_id"] == identifier for row in expected)
                          for identifier in ("imo", "zalo", "bip", "google-chat")},
                         {"imo": 3, "zalo": 1, "bip": 2, "google-chat": 2})
        self.assertEqual({row["android_package"] for row in expected},
                         {"com.imo.android.imoim", "com.zing.zalo", "com.turkcell.bip",
                          "com.google.android.apps.dynamite"})
        self.assertTrue(all("source_kind" not in row and "observed_on" not in row for row in expected))

    def test_real_canonical_table_emits_the_complete_current_public_inventory(self):
        canonical = pack.ROOT / "android/iconpack/components.json"
        with patch.object(pack, "COMPONENTS", canonical):
            manifest = pack.prepare_iconpack(self.export, canonical, self.output)
        self.assertEqual(manifest["version"], "0.1.16")
        self.assertEqual(manifest["artwork_version"], "0.32.0")
        self.assertEqual(manifest["counts"]["drawables"], 300)
        self.assertEqual(manifest["counts"]["component_mappings"], 1355)
        self.assertEqual(manifest["counts"]["upstream_component_mappings"], 1343)
        self.assertEqual(manifest["counts"]["observed_launcher_mappings"], 12)
        self.assertEqual(manifest["counts"]["named_package_hints"], 276)
        self.assertEqual(manifest["counts"]["package_hints"], 290)
        catalog = json.loads((self.output / "assets/catalog.json").read_bytes())
        self.assertEqual(len(catalog["packages"]), 290)
        self.assertEqual(len({row["package"] for row in catalog["packages"]}), 290)
        self.assertEqual({row["id"]: (row["package"], row["label"])
                          for row in catalog["packages"] if row["id"] in ("imo", "zalo", "bip", "google-chat")},
                         {"imo": ("com.imo.android.imoim", "imo"),
                          "zalo": ("com.zing.zalo", "Zalo"),
                          "bip": ("com.turkcell.bip", "BiP"),
                          "google-chat": ("com.google.android.apps.dynamite", "Google Chat")})
        entries = {row.attrib["component"]: row.attrib["drawable"]
                   for row in ET.parse(self.output / "assets/appfilter.xml").getroot()}
        self.assertEqual(len(entries), 1355)
        self.assertEqual(entries["ComponentInfo{com.dominospizza/com.dominospizza.SplashScreenActivity}"], "co_dominos")
        self.assertEqual(entries["ComponentInfo{com.dominospizza/com.dominos.activities.SplashScreenActivity}"], "co_dominos")
        expected_names = {"imo": "co_imo", "zalo": "co_zalo", "bip": "co_bip", "google-chat": "co_google_chat"}
        for row in added_communication_mappings():
            self.assertEqual(entries[row["component"]], expected_names[row["icon_id"]])
            self.assertNotIn(row["android_package"], entries)
        for name in expected_names.values():
            self.assertEqual((self.output / f"res/drawable-nodpi/{name}.png").read_bytes(), self.payloads[512])

    def test_unknown_drawable_wrong_package_and_package_only_components_are_refused(self):
        original = copy.deepcopy(self.table)
        for fault in ("drawable", "package", "package-only", "slash", "relative"):
            self.table = copy.deepcopy(original)
            row = self.table["mappings"][0]
            if fault == "drawable":
                row["icon_id"] = "not-in-this-catalog"
            elif fault == "package":
                row["android_package"] = "com.wrong.application"
                row["component"] = f'ComponentInfo{{com.wrong.application/{row["activity"]}}}'
            elif fault == "package-only":
                row["component"] = "com.android.chrome"
            elif fault == "slash":
                row["activity"] += "/extra"
            else:
                row["activity"] = ".Main"
                row["component"] = "ComponentInfo{com.android.chrome/.Main}"
            self.write_table()
            with self.subTest(fault=fault):
                self.refused()

    def test_conflicting_components_are_rejected_even_when_each_package_is_allowed(self):
        self.table["generic_packages"]["browser"] = ["com.android.chrome"]
        duplicate = copy.deepcopy(self.table["mappings"][0])
        duplicate["icon_id"] = "browser"
        self.table["mappings"].append(duplicate)
        self.write_table()
        self.refused(message="conflicting component")

    def test_unapproved_generic_package_and_audit_fields_are_refused(self):
        self.table["generic_packages"] = {}
        self.write_table()
        self.refused(message="verified function")
        self.table["generic_packages"] = {"phone": ["com.samsung.android.dialer"]}
        self.table["mappings"][0]["source_lines"] = [False]
        self.write_table()
        self.refused(message="source line")

    def test_pinned_opaque_activity_alias_is_not_rewritten(self):
        row = self.table["mappings"][2]
        row["activity"] = "samsung_phone_activity_alias"
        row["component"] = "ComponentInfo{com.samsung.android.dialer/samsung_phone_activity_alias}"
        self.write_table()
        pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertIn(row["component"], (self.output / "assets/appfilter.xml").read_text())

    def test_reparse_inputs_and_output_ancestors_are_refused(self):
        original = Path.lstat
        for target in (self.components, self.export / "manifest.json", self.base):
            def lstat(path, *args, **kwargs):
                if path == target:
                    return SimpleNamespace(st_mode=stat.S_IFREG if target.suffix else stat.S_IFDIR,
                                           st_file_attributes=0x400)
                return original(path, *args, **kwargs)
            with self.subTest(target=str(target)), patch.object(Path, "lstat", lstat):
                self.refused(message="reparse")

    def test_linked_input_manifest_is_refused_without_reading_target(self):
        source = self.copy_export()
        manifest = source / "manifest.json"
        manifest.unlink()
        target = self.base / "untouched.json"
        target.write_bytes(b"not parsed")
        try:
            manifest.symlink_to(target)
        except OSError as error:
            self.skipTest(f"File symlink fixture unavailable: {error}")
        self.refused(source=source, message="reparse")
        self.assertEqual(target.read_bytes(), b"not parsed")

    def test_injected_reparse_directory_is_refused_before_creating_its_children(self):
        mkdir, lstat = Path.mkdir, Path.lstat
        injected = []
        def reserve(path, *args, **kwargs):
            result = mkdir(path, *args, **kwargs)
            if path == self.output:
                mkdir(self.output / "res")
                injected.append(True)
            return result
        def observe(path, *args, **kwargs):
            if injected and path == self.output / "res":
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return lstat(path, *args, **kwargs)
        with patch.object(Path, "mkdir", reserve), patch.object(Path, "lstat", observe):
            with self.assertRaisesRegex(ValueError, "reparse"):
                pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertTrue(injected)
        self.assertEqual(list((self.output / "res").iterdir()), [])

    def test_input_drift_refuses_success_and_preserves_partial_resources(self):
        source = self.copy_export()
        original = Path.open
        injected = []
        def open_file(path, mode="r", *args, **kwargs):
            if mode == "xb" and path.name == "co_phone.png" and not injected:
                injected.append(True)
                with original(source / "Obscur/512/phone.png", "ab") as changed:
                    changed.write(b"changed during copy")
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, "open", open_file), self.assertRaisesRegex(ValueError, "changed during preparation"):
            pack.prepare_iconpack(source, self.components, self.output)
        self.assertTrue(injected)
        self.assertTrue((self.output / "res/drawable-nodpi/co_phone.png").is_file())
        with self.assertRaisesRegex(ValueError, "new output"):
            pack.prepare_iconpack(self.export, self.components, self.output)

    def test_craft_only_drift_refuses_success_and_preserves_partial_resources(self):
        # A comment leaves canonical drawings unchanged. Only the captured
        # generator-source identity can reject this change during preparation.
        fixture_root = self.base / "source-root"
        for relative in ("tokens-monochrome.json", "themeforge/icons.py",
                         "themeforge/icon_craft.py", "themeforge/icon_apps.py",
                         "tools/export-icons.mjs", "LICENSE"):
            target = fixture_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pack.ROOT / relative, target)
        original = Path.open
        injected = []
        def open_file(path, mode="r", *args, **kwargs):
            if mode == "xb" and path.name == "co_phone.png" and not injected:
                injected.append(True)
                with original(fixture_root / "themeforge/icon_craft.py", "ab") as changed:
                    changed.write(b"\n# Owned craft source drift fixture\n")
            return original(path, mode, *args, **kwargs)
        with patch.object(pack, "ROOT", fixture_root), patch.object(Path, "open", open_file), \
                self.assertRaisesRegex(ValueError, "changed during preparation"):
            pack.prepare_iconpack(self.export, self.components, self.output)
        self.assertTrue(injected)
        self.assertTrue((self.output / "res/drawable-nodpi/co_phone.png").is_file())
        self.assertTrue((self.output / "iconpack-manifest.json").is_file(),
                        "Refused preparation preserves its generated evidence; a manifest is not success")


if __name__ == "__main__":
    unittest.main()
