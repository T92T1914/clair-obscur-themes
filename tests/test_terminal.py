"""Schemes-only Windows Terminal packaging, not native terminal acceptance."""

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from themeforge import terminal
from themeforge.tokens import contrast, luminance, validate


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = "Clair-Obscur-Windows-Terminal-0.1.0.json"
ARCHIVE = "Clair-Obscur-Windows-Terminal-0.1.0.zip"
ANSI = ("black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
        "brightBlack", "brightRed", "brightGreen", "brightYellow", "brightBlue",
        "brightPurple", "brightCyan", "brightWhite")
CORE = {"background": "code", "foreground": "text", "selectionBackground": "selected", "cursorColor": "focus"}
FOREGROUND_EXCEPTIONS = {"Clair": ("white", "brightWhite"), "Obscur": ("black", "brightBlack")}
# These expectations deliberately do not import the implementation's mappings.
EXPECTED = {
    "Clair": {
        "black": "#242424", "red": "#a32e32", "green": "#276548", "yellow": "#805100",
        "blue": "#365f78", "purple": "#744b88", "cyan": "#256971", "white": "#fdfcf8",
        "brightBlack": "#595854", "brightRed": "#b33b3f", "brightGreen": "#387555",
        "brightYellow": "#8e6112", "brightBlue": "#476f88", "brightPurple": "#805794",
        "brightCyan": "#2c7178", "brightWhite": "#ffffff",
    },
    "Obscur": {
        "black": "#151515", "red": "#f2a3a3", "green": "#8ecb9b", "yellow": "#e3bf79",
        "blue": "#b3c8d8", "purple": "#c3a4dc", "cyan": "#8acbd0", "white": "#bcbcbc",
        "brightBlack": "#494949", "brightRed": "#ffb8b8", "brightGreen": "#a6e0b3",
        "brightYellow": "#f4d391", "brightBlue": "#c2d7e6", "brightPurple": "#d7bcec",
        "brightCyan": "#a7dfe3", "brightWhite": "#f4f4f4",
    },
}


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class TerminalThemeTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))

    def test_fragment_is_only_two_named_schemes_with_closed_color_fields(self):
        files = terminal.render_terminal(self.document)
        fragment = json.loads(files[FRAGMENT])
        self.assertEqual(set(fragment), {"schemes"})
        self.assertEqual(len(fragment["schemes"]), 2)
        for name, scheme in zip(("Clair", "Obscur"), fragment["schemes"]):
            self.assertEqual(scheme["name"], f"Clair Obscur - {name}")
            self.assertEqual(set(scheme), {"name", *CORE, *ANSI})
            self.assertEqual(len(scheme), 21)
            self.assertEqual(scheme, terminal.color_scheme(name, self.document))
            for field, value in scheme.items():
                if field != "name":
                    self.assertRegex(value, r"^#[0-9a-f]{6}$", (name, field))
        # A color fragment must not become an application/profile/font policy.
        self.assertNotRegex(files[FRAGMENT].decode(),
            r"profiles|defaults|commandline|font|startingDirectory|tabTitle|actions|keybindings|theme")

    def test_palette_roles_fixed_extras_and_default_background_contrast(self):
        for name in ("Clair", "Obscur"):
            scheme = terminal.color_scheme(name, self.document)
            palette = self.document["themes"][name]
            for field, role in CORE.items():
                self.assertEqual(scheme[field], palette[role], (name, field))
            self.assertEqual({field: scheme[field] for field in ANSI}, EXPECTED[name])
            self.assertEqual(len({scheme[field] for field in ANSI}), 16)
            qualified = set(ANSI) - set(FOREGROUND_EXCEPTIONS[name])
            self.assertEqual(len(qualified), 14)
            for field in qualified:
                self.assertGreaterEqual(contrast(scheme[field], scheme["background"]), 4.5, (name, field))
                self.assertGreaterEqual(contrast(scheme[field], palette["canvas"]), 4.5, (name, field, "canvas"))
            for field in FOREGROUND_EXCEPTIONS[name]:
                self.assertLess(contrast(scheme[field], scheme["background"]), 4.5, (name, field))
            for white in ("white", "brightWhite"):
                for black in ("black", "brightBlack"):
                    self.assertGreaterEqual(contrast(scheme[white], scheme[black]), 4.5, (name, white, black))
            for normal in ANSI[:8]:
                bright = "bright" + normal[0].upper() + normal[1:]
                self.assertGreater(luminance(scheme[bright]), luminance(scheme[normal]), (name, normal))
            self.assertGreaterEqual(contrast(scheme["foreground"], scheme["background"]), 4.5)
            self.assertGreaterEqual(contrast(scheme["foreground"], scheme["selectionBackground"]), 4.5)
            self.assertGreaterEqual(contrast(scheme["cursorColor"], scheme["background"]), 3)
        # The rejected initial candidate made every ANSI foreground contrast with
        # the default background, but broke explicitly paired neutral output.
        # These witnesses prevent that optimization from silently returning.
        for foreground, background in (("#bcbcbc", "#858585"), ("#595854", "#242424")):
            self.assertLess(contrast(foreground, background), 4.5)

    def test_render_is_deterministic_does_not_mutate_and_tracks_shared_role_changes(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {name: dict(reversed(list(values.items())))
                               for name, values in reversed(list(self.document["themes"].items()))}
        original = terminal.render_terminal(self.document)
        self.assertEqual(terminal.render_terminal(reordered), original)
        self.assertEqual(self.document, before)
        changed = copy.deepcopy(self.document)
        changed["version"] = "2.3.4"
        changed["themes"]["Clair"]["text"] = "#202020"
        updated = terminal.render_terminal(changed)
        schemes = json.loads(updated[FRAGMENT])["schemes"]
        self.assertEqual(schemes[0]["foreground"], "#202020")
        self.assertEqual(schemes[0]["black"], "#202020")
        self.assertEqual(schemes[1], json.loads(original[FRAGMENT])["schemes"][1])
        self.assertEqual(json.loads(updated["manifest.json"])["token_version"], "2.3.4")
        self.assertEqual(json.loads(updated["manifest.json"])["version"], "0.1.0")

    def test_archive_manifest_license_and_checksums_identify_actual_bytes(self):
        files = terminal.render_terminal(self.document)
        self.assertEqual(set(files), {FRAGMENT, "LICENSE.txt", ARCHIVE, "manifest.json", "SHA256SUMS"})
        with zipfile.ZipFile(io.BytesIO(files[ARCHIVE])) as archive:
            self.assertEqual(set(archive.namelist()), {FRAGMENT, "LICENSE.txt"})
            self.assertEqual(len(archive.infolist()), 2)
            self.assertIsNone(archive.testzip())
            for info in archive.infolist():
                self.assertEqual(archive.read(info.filename), files[info.filename])
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertNotIn("..", info.filename.split("/"))
        self.assertEqual(files["LICENSE.txt"],
            (ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n").encode() + b"\n")
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["generator"], "themeforge.terminal")
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["token_schema"], 1)
        self.assertEqual(manifest["token_version"], "0.1.1")
        self.assertEqual(manifest["native_acceptance"], "unverified")
        self.assertEqual(manifest["archive"], ARCHIVE)
        self.assertEqual(manifest["fragment"], FRAGMENT)
        self.assertEqual(manifest["schemes"],
                         {name: f"Clair Obscur - {name}" for name in ("Clair", "Obscur")})
        self.assertEqual(manifest["foreground_exceptions"],
                         {name: list(fields) for name, fields in FOREGROUND_EXCEPTIONS.items()})
        for name, scheme in zip(("Clair", "Obscur"), json.loads(files[FRAGMENT])["schemes"]):
            expected_ratios = {field: round(contrast(scheme[field], scheme["background"]), 6)
                               for field in ANSI}
            self.assertEqual(manifest["default_background_contrast"][name], expected_ratios)
            expected_pairs = {f"{white}/{black}": round(contrast(scheme[white], scheme[black]), 6)
                              for white in ("white", "brightWhite") for black in ("black", "brightBlack")}
            self.assertEqual(manifest["neutral_pair_contrast"][name], expected_pairs)
        canonical = (json.dumps(self.document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()
        self.assertEqual(manifest["tokens_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual({record["path"] for record in manifest["files"]}, {FRAGMENT, "LICENSE.txt", ARCHIVE})
        self.assertEqual(len(manifest["files"]), 3)
        for record in manifest["files"]:
            self.assertEqual(record["bytes"], len(files[record["path"]]))
            self.assertEqual(record["sha256"], hashlib.sha256(files[record["path"]]).hexdigest())
        expected = "".join(f"{hashlib.sha256(payload).hexdigest()}  {path}\n"
                           for path, payload in sorted(files.items()) if path != "SHA256SUMS")
        self.assertEqual(files["SHA256SUMS"], expected.encode("ascii"))

    def test_invalid_and_adapter_contrast_breaking_tokens_fail_before_output(self):
        invalid = [None, [], {**self.document, "schema_version": True},
                   {**self.document, "version": None}, {**self.document, "themes": None}]
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        bad_color = copy.deepcopy(self.document)
        bad_color["themes"]["Clair"]["accent"] = "url(https://invalid.example/)"
        invalid.append(bad_color)
        terminal_failure = copy.deepcopy(self.document)
        terminal_failure["themes"]["Clair"]["code"] = "#dad8cf"
        validate(terminal_failure)  # A valid shared palette can still fail this adapter.
        self.assertLess(contrast("#476f88", "#dad8cf"), 4.5)
        invalid.append(terminal_failure)
        for role, color in (("muted", "#f4f4f4"), ("error", "#fffefc")):
            invalid_ansi = copy.deepcopy(self.document)
            invalid_ansi["themes"]["Obscur"][role] = color
            validate(invalid_ansi)
            # The first aliases white/brightWhite, the second reverses red intensity.
            invalid.append(invalid_ansi)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "terminal"
                with self.assertRaises(ValueError):
                    terminal.build_terminal(document, output)
                self.assertFalse(output.exists())
        with self.assertRaises(ValueError):
            terminal.color_scheme("other", self.document)

    def test_fresh_build_and_exact_check_preserve_output_without_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "terminal"
            result = terminal.build_terminal(self.document, output)
            self.assertEqual(result["version"], "0.1.0")
            before = snapshot(output)
            self.assertEqual(before, terminal.render_terminal(self.document))
            terminal.build_terminal(self.document, output, check=True)
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, output)
            self.assertEqual(snapshot(output), before)
            for name in ("empty", "foreign"):
                foreign = Path(temporary) / name
                foreign.mkdir()
                if name == "foreign":
                    (foreign / "keep.txt").write_bytes(b"preserve exact bytes")
                previous = snapshot(foreign)
                for check in (False, True):
                    with self.assertRaises(ValueError):
                        terminal.build_terminal(self.document, foreign, check=check)
                    self.assertEqual(snapshot(foreign), previous)
            existing_file = Path(temporary) / "file"
            existing_file.write_bytes(b"leave file intact")
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, existing_file)
            self.assertEqual(existing_file.read_bytes(), b"leave file intact")
            missing = Path(temporary) / "missing"
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, missing, check=True)
            self.assertFalse(missing.exists())

    def test_changed_missing_extra_and_empty_directory_check_fail_without_repair(self):
        for mutation in ("changed", "missing", "extra-file", "extra-dir", "manifest", "checksum"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "terminal"
                terminal.build_terminal(self.document, output)
                fragment = output / FRAGMENT
                if mutation == "changed": fragment.write_bytes(fragment.read_bytes() + b" ")
                elif mutation == "missing": fragment.unlink()
                elif mutation == "extra-file": (output / "keep.txt").write_bytes(b"preserve")
                elif mutation == "extra-dir": (output / "keep").mkdir()
                elif mutation == "manifest": (output / "manifest.json").write_bytes(b"{}\n")
                else: (output / "SHA256SUMS").write_bytes(b"\n")
                before = snapshot(output)
                with self.assertRaises(ValueError):
                    terminal.build_terminal(self.document, output, check=True)
                self.assertEqual(snapshot(output), before)
                if mutation == "extra-dir": self.assertTrue((output / "keep").is_dir())

    def test_root_managed_and_linked_destinations_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(terminal, "ROOT", Path(temporary)):
            base = Path(temporary)
            for target in (base / "dist", base / "dist/terminal", Path(base.anchor)):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    terminal.build_terminal(self.document, target)
            self.assertFalse((base / "dist").exists())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            destination = base / "target"
            destination.mkdir()
            (destination / "keep.txt").write_bytes(b"unchanged")
            link = base / "link"
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(destination), str(link))
            else:
                link.symlink_to(destination, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinks or reparse"):
                terminal.build_terminal(self.document, link / "terminal")
            self.assertEqual(snapshot(destination), {"keep.txt": b"unchanged"})

    def test_injected_file_is_not_overwritten_and_partial_output_is_retained(self):
        original_open = Path.open
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial"
            fragment = output / FRAGMENT
            injected = False
            def open_with_injection(path, *args, **kwargs):
                nonlocal injected
                if path == fragment and args and args[0] == "xb" and not injected:
                    injected = True
                    with original_open(path, "wb") as stream:
                        stream.write(b"external write must remain exact")
                return original_open(path, *args, **kwargs)
            with patch.object(Path, "open", open_with_injection):
                with self.assertRaises(FileExistsError):
                    terminal.build_terminal(self.document, output)
            self.assertTrue(injected)
            self.assertEqual(fragment.read_bytes(), b"external write must remain exact")
            before = snapshot(output)
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, output)
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, output, check=True)
            self.assertEqual(snapshot(output), before)

    def test_write_interruption_retains_partial_evidence_and_refuses_replacement(self):
        original_open = Path.open
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial"
            failure = output / "LICENSE.txt"
            def open_with_failure(path, *args, **kwargs):
                if path == failure and args and args[0] == "xb":
                    raise OSError("retained simulated write interruption")
                return original_open(path, *args, **kwargs)
            with patch.object(Path, "open", open_with_failure):
                with self.assertRaisesRegex(OSError, "write interruption"):
                    terminal.build_terminal(self.document, output)
            before = snapshot(output)
            self.assertEqual(before.get(FRAGMENT), terminal.render_terminal(self.document)[FRAGMENT])
            self.assertNotIn("manifest.json", before)
            self.assertNotIn("SHA256SUMS", before)
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, output)
            with self.assertRaises(ValueError):
                terminal.build_terminal(self.document, output, check=True)
            self.assertEqual(snapshot(output), before)


class TerminalPreviewTests(unittest.TestCase):
    def setUp(self):
        from themeforge.build import build_release
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.artifacts = self.base / "artifacts"
        self.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))
        build_release(ROOT / "tokens.json", self.artifacts)

    def test_public_and_portable_deliver_exact_terminal_package_guide_and_labeled_colors(self):
        from preview import PORTABLE_ARCHIVE, preview_files
        files = preview_files(ROOT, self.artifacts)
        expected_files = {f"terminal/{name}": payload
                          for name, payload in terminal.render_terminal(self.document).items()}
        expected_files["terminal/installation.md"] = (ROOT / "docs/windows-terminal.md").read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as portable:
            deliveries = (files, {path: portable.read(path) for path in portable.namelist()})
        for delivery in deliveries:
            with self.subTest(distribution=json.loads(delivery["site-manifest.json"])["distribution"]["kind"]):
                self.assertEqual({path: payload for path, payload in delivery.items()
                                  if path.startswith("terminal/")}, expected_files)
                manifest = json.loads(delivery["site-manifest.json"])
                for path, payload in expected_files.items():
                    self.assertEqual(manifest["files"][path], hashlib.sha256(payload).hexdigest())
                page = delivery["index.html"].decode()
                self.assertNotIn("{{", page)
                self.assertIn(f'href="terminal/{ARCHIVE}" download', page)
                self.assertIn('href="terminal/SHA256SUMS" download', page)
                self.assertIn('href="terminal/installation.md"', page)
                cards = re.findall(r'<article class="terminal-palette" data-palette="([^"]+)"[^>]*>(.*?)</article>',
                                   page, re.DOTALL)
                self.assertEqual([name for name, _ in cards], ["Clair", "Obscur"])
                for name, card in cards:
                    self.assertIn(f"Clair Obscur - {name}", card)
                    samples = re.findall(r'<div class="terminal-slot" data-ansi="([^"]+)"><p>[^<]+</p>'
                                         r'<code style="([^"]+)">Aa 0123</code><small>([^<]+)</small></div>', card)
                    self.assertEqual([field for field, _, _ in samples], list(ANSI))
                    for field, style, context in samples:
                        partner = ("black" if name == "Clair" else "white") if field in FOREGROUND_EXCEPTIONS[name] else None
                        background = EXPECTED[name][partner] if partner else self.document["themes"][name]["code"]
                        self.assertEqual(style, f"color:{EXPECTED[name][field]};background:{background}")
                        self.assertEqual(context, f"on {partner}" if partner else "on default")

    def test_terminal_preview_preserves_desktop_downloads_and_all_icon_revisions(self):
        from preview import (POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE, ICON_ARCHIVE, ICON_CHECKSUMS,
                             LEGACY_ICON_ARCHIVE, PREVIOUS_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE,
                             MONOCHROME_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE,
                             PORTABLE_ARCHIVE, preview_files)
        from themeforge.icons import render_icons
        video_editing_ids = ('inshot', 'youcut', 'vn-video-editor', 'kinemaster', 'powerdirector', 'filmora', 'vivavideo', 'gopro-quik', 'videoshow', 'alight-motion')
        desktop = snapshot(self.artifacts)
        self.assertEqual(len(desktop), 32)
        icons = render_icons(json.loads((ROOT / 'tokens-monochrome.json').read_bytes()))
        current_svg = {path: payload for path, payload in icons.items() if path.endswith(".svg")}
        self.assertEqual(len(current_svg), 584)
        token_bytes = (ROOT / "tokens.json").read_bytes()
        files = preview_files(ROOT, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as portable:
            deliveries = (files, {path: portable.read(path) for path in portable.namelist()})
        for delivery in deliveries:
            self.assertEqual({path.removeprefix("downloads/"): payload for path, payload in delivery.items()
                              if path.startswith("downloads/")}, desktop)
            self.assertEqual({path.removeprefix("icons/"): payload for path, payload in delivery.items()
                              if path.startswith("icons/") and path.endswith(".svg")}, current_svg)
            self.assertEqual(hashlib.sha256(delivery[VIDEO_EDITING_ICON_ARCHIVE]).hexdigest(),
                             "db1e52859497c2d4852362c1bd5d365a2aab2b6473069bc6aa49c4895d3e0ffa")
            with zipfile.ZipFile(io.BytesIO(delivery[POLISHED_ICON_ARCHIVE])) as polished:
                self.assertEqual(hashlib.sha256(delivery[POLISHED_ICON_ARCHIVE]).hexdigest(),
                                 "504402b2f2b93ea6315a92738487fd4545c949b7f28a10fcaa79f383e7db7caf")
                self.assertEqual(hashlib.sha256(polished.read("manifest.json")).hexdigest(),
                                 "3c2a4316d0a118dfa585c637c3e8caebc0b961f9ab097d2950639475b5155b03")
                self.assertEqual(json.loads(polished.read("manifest.json"))["version"], "0.21.0")
                polished_previous_svg = {name: polished.read(name) for name in polished.namelist() if name.endswith(".svg")}
            self.assertEqual(set(current_svg), set(polished_previous_svg))
            self.assertEqual({name for name in current_svg if current_svg[name] != polished_previous_svg[name]},
                             {f"{appearance}/{identifier}.svg" for appearance in ("Clair", "Obscur")
                              for identifier in ("threads", "evernote", "myradar", "goodreads")})
            with zipfile.ZipFile(io.BytesIO(delivery[VIDEO_EDITING_ICON_ARCHIVE])) as video_editing:
                self.assertEqual(hashlib.sha256(video_editing.read("manifest.json")).hexdigest(),
                                 "f451ea0520367d0f3b4057c87d6f1204e381122a8da4cd57f8f00d8dbf00efbe")
                video_svg = {name: video_editing.read(name) for name in video_editing.namelist() if name.endswith(".svg")}
                self.assertEqual(json.loads(video_editing.read("manifest.json"))["version"], "0.20.0")
            self.assertEqual(set(current_svg), set(video_svg))
            polished_svg = {name for name in video_svg if polished_previous_svg[name] != video_svg[name]}
            self.assertEqual(polished_svg, {f"{appearance}/{identifier}.svg"
                for appearance in ("Clair", "Obscur") for identifier in ('ai-dungeon', 'usaa', 'discord', 'link-to-windows', 'chatgpt', 'prime-video', 'g2a')})
            self.assertEqual(hashlib.sha256(delivery[PHONE_SERVICE_ICON_ARCHIVE]).hexdigest(),
                             "0e638e99a265b7b3d5c04e77c3611c732e6b36fa3d26a674e255d89e0c1fd346")
            with zipfile.ZipFile(io.BytesIO(delivery[PHONE_SERVICE_ICON_ARCHIVE])) as previous_phone_service:
                self.assertEqual(hashlib.sha256(previous_phone_service.read("manifest.json")).hexdigest(),
                                 "e1be7375d5697623c539b0b08989be070edf3df5a501a95753d0c78fc44ff503")
                self.assertEqual(json.loads(previous_phone_service.read("manifest.json"))["version"], "0.17.0")
                preserved_svg = {name: previous_phone_service.read(name) for name in previous_phone_service.namelist()
                                 if name.endswith(".svg")}
            self.assertEqual(set(current_svg) - set(preserved_svg), {f"{appearance}/{identifier}.svg"
                for appearance in ("Clair", "Obscur") for identifier in ("gboard", *video_editing_ids)})
            changed_svg = {name for name in preserved_svg if video_svg[name] != preserved_svg[name]}
            self.assertEqual(changed_svg, {f"{appearance}/{identifier}.svg"
                for appearance in ("Clair", "Obscur")
                for identifier in ("google-messages", "google-translate", "fandom", "ace-hardware",
                                   "dollar-general", "myfitnesspal", "wallpaper-engine", "webtoon")})
            self.assertEqual(hashlib.sha256(delivery[READING_ICON_ARCHIVE]).hexdigest(),
                             "3fbf8b53e12ddae6ea354d6ed20a1464c4874192a24f5dee7f231baed0e7f3a0")
            # Immutable 0.1.0 identity checked against both the retained PR38
            # preview archive and its delivered user download, independently.
            original_archive_hash = "040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34"
            self.assertEqual(hashlib.sha256(delivery[LEGACY_ICON_ARCHIVE]).hexdigest(), original_archive_hash)
            self.assertEqual(hashlib.sha256(delivery[PREVIOUS_ICON_ARCHIVE]).hexdigest(),
                             '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312')
            self.assertEqual(hashlib.sha256(delivery[FIRST_APP_ICON_ARCHIVE]).hexdigest(),
                             'd217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756')
            self.assertEqual(hashlib.sha256(delivery[SECOND_APP_ICON_ARCHIVE]).hexdigest(),
                             'fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf')
            self.assertEqual(hashlib.sha256(delivery[THIRD_APP_ICON_ARCHIVE]).hexdigest(),
                             '2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a')
            self.assertEqual(hashlib.sha256(delivery[MONOCHROME_ICON_ARCHIVE]).hexdigest(),
                             "241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb")
            self.assertEqual(hashlib.sha256(delivery[COMPANION_ICON_ARCHIVE]).hexdigest(),
                             "aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05")
            self.assertEqual(hashlib.sha256(delivery[BROAD_ICON_ARCHIVE]).hexdigest(),
                             "fcdaec582be7508b3e62bd9168695ea1650e33c8e53c3de46f3614ae53d833cf")
            with zipfile.ZipFile(io.BytesIO(delivery[BROAD_ICON_ARCHIVE])) as previous_broad:
                self.assertEqual(json.loads(previous_broad.read("manifest.json"))["version"], "0.8.0")
                self.assertEqual(hashlib.sha256(previous_broad.read("manifest.json")).hexdigest(),
                                 "7a8a35d6ba1186a718e970e26c5c6b7b19bf4949010c7bc89af3cb6063b95252")
            self.assertEqual(hashlib.sha256(delivery[EVERYDAY_ICON_ARCHIVE]).hexdigest(),
                             "994ce1d819414b06062d5cd32a03eeb8891e9074b09491dfb2c774a55ae5a3b1")
            with zipfile.ZipFile(io.BytesIO(delivery[EVERYDAY_ICON_ARCHIVE])) as previous_everyday:
                self.assertEqual(json.loads(previous_everyday.read("manifest.json"))["version"], "0.9.0")
                self.assertEqual(hashlib.sha256(previous_everyday.read("manifest.json")).hexdigest(),
                                 "7f3e3137cc2b3e72a4861368b6864158de8f5a17e5b2a57a2b0489c5ca0f78b5")
                previous_svg = {name: previous_everyday.read(name) for name in previous_everyday.namelist()
                                if name.endswith(".svg")}
                self.assertEqual(len(previous_svg), 350)
                self.assertEqual({name: preserved_svg[name] for name in previous_svg}, previous_svg)
            with zipfile.ZipFile(io.BytesIO(delivery[FOOD_ORDER_ICON_ARCHIVE])) as previous_food:
                self.assertEqual(hashlib.sha256(delivery[FOOD_ORDER_ICON_ARCHIVE]).hexdigest(),
                                 "a81ffb8c4fb3ef32f3c8391c53016e99246b755ce9079fdee84b5948790ab8e0")
                previous_manifest = previous_food.read("manifest.json")
                self.assertEqual(hashlib.sha256(previous_manifest).hexdigest(),
                                 "b9b1995bee3f538137bd1f5edd4da4ba5358ce3908d19ff9b493c4f19c8ec88d")
                previous_catalog = json.loads(previous_manifest)
                self.assertEqual(previous_catalog["version"], "0.10.0")
                self.assertEqual(len(previous_catalog["catalog"]), 187)
                self.assertEqual(json.loads(icons["manifest.json"])["catalog"][:187],
                                 previous_catalog["catalog"])
                previous_svg = {name: previous_food.read(name) for name in previous_food.namelist()
                                if name.endswith(".svg")}
                self.assertEqual(len(previous_svg), 374)
                self.assertEqual({name: preserved_svg[name] for name in previous_svg}, previous_svg)
            with zipfile.ZipFile(io.BytesIO(delivery[TRAVEL_ICON_ARCHIVE])) as previous_travel:
                self.assertEqual(hashlib.sha256(delivery[TRAVEL_ICON_ARCHIVE]).hexdigest(),
                                 "04cce2b812ad4f6ed7bcfda172a9bfe5a6d63d058b6899570a1dbe94f162884d")
                travel_catalog = json.loads(previous_travel.read("manifest.json"))
                self.assertEqual(travel_catalog["version"], "0.11.0")
                self.assertEqual(len(travel_catalog["files"]), 394)
                for name in previous_travel.namelist():
                    if name.endswith(".svg"):
                        self.assertEqual(previous_travel.read(name), preserved_svg[name])
            with zipfile.ZipFile(io.BytesIO(delivery[FINANCE_ICON_ARCHIVE])) as previous_finance:
                self.assertEqual(hashlib.sha256(delivery[FINANCE_ICON_ARCHIVE]).hexdigest(),
                                 "db8ed7e2c62d36786b2c2d510fdf68f83649fda512f6bb018f5043491cb8f0cf")
                finance_catalog = json.loads(previous_finance.read("manifest.json"))
                self.assertEqual(finance_catalog["version"], "0.12.0")
                self.assertEqual(len(finance_catalog["files"]), 414)
                self.assertEqual(len(finance_catalog["catalog"]), 207)
                self.assertEqual(json.loads(icons["manifest.json"])["catalog"][:207],
                                 finance_catalog["catalog"])
                for name in previous_finance.namelist():
                    if name.endswith(".svg"):
                        self.assertEqual(previous_finance.read(name), preserved_svg[name])
            with zipfile.ZipFile(io.BytesIO(delivery[WEATHER_ICON_ARCHIVE])) as previous_weather:
                self.assertEqual(hashlib.sha256(delivery[WEATHER_ICON_ARCHIVE]).hexdigest(),
                                 "e6f7c532d0c625666a0f3403ee27842ac8612e6368d49f64fb3e84b667a42ca1")
                weather_catalog = json.loads(previous_weather.read("manifest.json"))
                self.assertEqual(weather_catalog["version"], "0.13.0")
                self.assertEqual(len(weather_catalog["files"]), 434)
                self.assertEqual(len(weather_catalog["catalog"]), 217)
                self.assertEqual(json.loads(icons["manifest.json"])["catalog"][:217],
                                 weather_catalog["catalog"])
                for name in previous_weather.namelist():
                    if name.endswith(".svg"):
                        self.assertEqual(previous_weather.read(name), preserved_svg[name])
            with zipfile.ZipFile(io.BytesIO(delivery[RUNNING_TRAINING_ICON_ARCHIVE])) as previous_running:
                self.assertEqual(hashlib.sha256(delivery[RUNNING_TRAINING_ICON_ARCHIVE]).hexdigest(),
                                 "4b3324d30b0b6e94a52e0d51a206e499e6e2b6be82052752963da9446c44e6c1")
                running_manifest = previous_running.read("manifest.json")
                self.assertEqual(hashlib.sha256(running_manifest).hexdigest(),
                                 "4ac31c55d2723a0e27ee4892eb29d59dbdcb179443f496fced7b69337c0699df")
                running_catalog = json.loads(running_manifest)
                self.assertEqual(running_catalog["version"], "0.14.0")
                self.assertEqual(len(running_catalog["files"]), 450)
                self.assertEqual(len(running_catalog["catalog"]), 225)
                self.assertEqual(json.loads(icons["manifest.json"])["catalog"][:225],
                                 running_catalog["catalog"])
                previous_svg = {name: previous_running.read(name) for name in previous_running.namelist()
                                if name.endswith(".svg")}
                self.assertEqual(len(previous_svg), 450)
                self.assertEqual({name: preserved_svg[name] for name in previous_svg}, previous_svg)
            with zipfile.ZipFile(io.BytesIO(delivery[LEARNING_ICON_ARCHIVE])) as previous_learning:
                self.assertEqual(hashlib.sha256(delivery[LEARNING_ICON_ARCHIVE]).hexdigest(),
                                 "df05503c0f1825d09e5b5fb96fcb87401490fef601518ca4e526a6e6d564197c")
                learning_manifest = previous_learning.read("manifest.json")
                self.assertEqual(hashlib.sha256(learning_manifest).hexdigest(),
                                 "3979cc7eaf90a5cf8aab82bd711fc8d2ff92388856cbb41b9321442693b88b2b")
                learning_catalog = json.loads(learning_manifest)
                self.assertEqual(learning_catalog["version"], "0.15.0")
                self.assertEqual(len(learning_catalog["files"]), 466)
                self.assertEqual(len(learning_catalog["catalog"]), 233)
                self.assertEqual(json.loads(icons["manifest.json"])["catalog"][:233], learning_catalog["catalog"])
                previous_svg = {name: previous_learning.read(name) for name in previous_learning.namelist()
                                if name.endswith(".svg")}
                self.assertEqual(len(previous_svg), 466)
                self.assertEqual({name: preserved_svg[name] for name in previous_svg}, previous_svg)
            self.assertEqual(hashlib.sha256(delivery[REFINED_ICON_ARCHIVE]).hexdigest(),
                             "5bbf577f50b3dae894405e598d9ca7d8e6246cac9e7f2859c7b5f5ba0771e985")
            with zipfile.ZipFile(io.BytesIO(delivery[REFINED_ICON_ARCHIVE])) as refined:
                refined_svg = {name: refined.read(name) for name in refined.namelist() if name.endswith(".svg")}
                self.assertEqual({name: video_svg[name] for name in refined_svg}, refined_svg)
                self.assertEqual(set(current_svg) - set(refined_svg), {f"{appearance}/{identifier}.svg"
                    for appearance in ("Clair", "Obscur") for identifier in ("gboard", *video_editing_ids)})
            self.assertEqual(hashlib.sha256(delivery[GBOARD_ICON_ARCHIVE]).hexdigest(),
                             "22ffaf915634a27adc9608e77d8c0d5bd885bc3bfae323a509f2f566a330334e")
            with zipfile.ZipFile(io.BytesIO(delivery[GBOARD_ICON_ARCHIVE])) as gboard:
                gboard_svg = {name: gboard.read(name) for name in gboard.namelist() if name.endswith(".svg")}
                self.assertEqual({name: video_svg[name] for name in gboard_svg}, gboard_svg)
                self.assertEqual(set(current_svg) - set(gboard_svg), {f"{appearance}/{identifier}.svg"
                    for appearance in ("Clair", "Obscur") for identifier in video_editing_ids})
            with zipfile.ZipFile(io.BytesIO(delivery[ICON_ARCHIVE])) as current:
                self.assertEqual(json.loads(current.read("manifest.json"))["version"], "0.22.0")
            self.assertEqual(delivery[ICON_CHECKSUMS],
                             ''.join(f'{hashlib.sha256(delivery[path]).hexdigest()}  {Path(path).name}\n'
                                      for path in (ICON_ARCHIVE, POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                                                  PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE)).encode())
        self.assertEqual(snapshot(self.artifacts), desktop)
        self.assertEqual((ROOT / "tokens.json").read_bytes(), token_bytes)


if __name__ == "__main__":
    unittest.main()
