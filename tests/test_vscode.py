"""Declarative VS Code packaging and color contracts, not native editor acceptance."""

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
import xml.etree.ElementTree as ET
import zipfile

from themeforge import vscode
from themeforge.tokens import contrast


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_FILES = {
    "extension/package.json", "extension/LICENSE.txt",
    "extension/themes/clair-color-theme.json", "extension/themes/obscur-color-theme.json",
}
ARCHIVE = "Clair-Obscur-VSCode-0.1.0.vsix"
VSIX_NS = "{http://schemas.microsoft.com/developer/vsx-schema/2011}"
CONTENT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def composite(color, background):
    if len(color) == 7:
        return color
    alpha = int(color[7:9], 16) / 255
    rgb = [round(int(color[index:index + 2], 16) * alpha +
                 int(background[index:index + 2], 16) * (1 - alpha)) for index in (1, 3, 5)]
    return "#" + "".join(f"{value:02x}" for value in rgb)


class VSCodeThemeTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))

    def test_paired_extension_has_only_declarative_theme_capabilities(self):
        package = json.loads(vscode.render_vscode(self.document)["extension/package.json"])
        self.assertEqual(set(package), {"name", "displayName", "publisher", "version", "description",
                                       "engines", "categories", "license", "contributes"})
        self.assertEqual(package["name"], "clair-obscur")
        self.assertEqual(package["publisher"], "T92T1914")
        self.assertEqual(package["version"], "0.1.0")
        self.assertEqual(package["engines"], {"vscode": "^1.100.0"})
        self.assertEqual(package["categories"], ["Themes"])
        self.assertEqual(package["license"], "MIT")
        self.assertEqual(package["contributes"], {"themes": [
            {"id": "clair-obscur-clair", "label": "Clair", "uiTheme": "vs", "path": "./themes/clair-color-theme.json"},
            {"id": "clair-obscur-obscur", "label": "Obscur", "uiTheme": "vs-dark", "path": "./themes/obscur-color-theme.json"},
        ]})
        # A theme must not become an extension-host program or an installation policy.
        for forbidden in ("main", "browser", "activationEvents", "dependencies", "extensionDependencies",
                          "extensionPack", "scripts", "enabledApiProposals"):
            self.assertNotIn(forbidden, package)

    def test_workbench_uses_exact_semantic_roles_in_important_user_surfaces(self):
        expected = {
            "foreground": "text", "focusBorder": "focus", "activityBar.background": "canvas",
            "sideBar.background": "panel", "sideBar.foreground": "text", "sideBar.border": "divider",
            "titleBar.activeBackground": "canvas", "titleBar.inactiveBackground": "control",
            "statusBar.background": "panel", "statusBar.foreground": "text",
            "editor.background": "code", "editor.foreground": "text",
            "editorCursor.foreground": "accent", "editorLineNumber.foreground": "muted",
            "editorError.foreground": "error", "editorWarning.foreground": "warning",
            "editorInfo.foreground": "accent", "editorSuggestWidget.background": "panel",
            "tab.activeBackground": "code", "tab.activeForeground": "text",
            "tab.inactiveBackground": "panel", "tab.inactiveForeground": "muted",
            "list.activeSelectionBackground": "selected", "list.activeSelectionForeground": "text",
            "list.hoverBackground": "hover", "list.hoverForeground": "text",
            "input.background": "control", "input.foreground": "text", "input.border": "border",
            "input.placeholderForeground": "muted", "button.background": "accent",
            "button.foreground": "on_accent", "button.secondaryBackground": "control",
            "button.secondaryForeground": "text", "panel.background": "canvas",
            "notifications.background": "panel", "notifications.foreground": "text",
        }
        for name in ("Clair", "Obscur"):
            theme = vscode.color_theme(name, self.document)
            self.assertEqual(set(theme), {"name", "colors", "tokenColors", "semanticHighlighting", "semanticTokenColors"})
            self.assertEqual(theme["name"], name)
            self.assertTrue(theme["semanticHighlighting"])
            for key, role in expected.items():
                self.assertEqual(theme["colors"][key], self.document["themes"][name][role], (name, key))
            self.assertGreaterEqual(len(theme["colors"]), len(expected))
            for color in theme["colors"].values():
                self.assertRegex(color, r"^#[0-9a-f]{6}(?:[0-9a-f]{2})?$")
            # Color data never changes the user's code font, geometry or scaling.
            text = json.dumps(theme).lower()
            self.assertNotRegex(text, r"fontfamily|fontstyle|fontweight|fontsize|lineheight|letterspacing|configurationdefaults")

    def test_syntax_and_semantic_grammars_have_independent_expected_examples(self):
        for name in ("Clair", "Obscur"):
            palette = self.document["themes"][name]
            theme = vscode.color_theme(name, self.document)
            scopes = {scope: entry["settings"] for entry in theme["tokenColors"] for scope in entry["scope"]}
            for scope, role in (("comment", "muted"), ("keyword", "accent"), ("storage", "accent"),
                                ("string", "success"), ("constant.numeric", "warning"), ("entity.name.function", "accent"),
                                ("entity.name.class", "accent"), ("variable", "text"), ("invalid", "error"),
                                ("markup.inserted", "success"), ("markup.deleted", "error")):
                self.assertEqual(scopes[scope], {"foreground": palette[role]})
            for selector, role in (("comment", "muted"), ("keyword", "accent"), ("string", "success"),
                                   ("number", "warning"), ("variable", "text"), ("class", "accent"),
                                   ("method", "accent"), ("parameter", "text"), ("enumMember", "warning")):
                self.assertEqual(theme["semanticTokenColors"][selector], palette[role])
            self.assertEqual(len(scopes), sum(len(entry["scope"]) for entry in theme["tokenColors"]))

    def test_actual_text_control_and_selection_pairs_keep_readable_contrast(self):
        for name in ("Clair", "Obscur"):
            theme = vscode.color_theme(name, self.document)
            colors = theme["colors"]
            for foreground, background in (("editor.foreground", "editor.background"),
                    ("editorLineNumber.foreground", "editor.background"),
                    ("sideBar.foreground", "sideBar.background"), ("statusBar.foreground", "statusBar.background"),
                    ("tab.activeForeground", "tab.activeBackground"), ("tab.inactiveForeground", "tab.inactiveBackground"),
                    ("input.foreground", "input.background"), ("input.placeholderForeground", "input.background"),
                    ("list.activeSelectionForeground", "list.activeSelectionBackground"),
                    ("list.hoverForeground", "list.hoverBackground"), ("button.foreground", "button.background"),
                    ("button.foreground", "button.hoverBackground"),
                    ("button.secondaryForeground", "button.secondaryBackground"),
                    ("notifications.foreground", "notifications.background")):
                self.assertGreaterEqual(contrast(colors[foreground], colors[background]), 4.5, (name, foreground, background))
            for entry in theme["tokenColors"]:
                self.assertGreaterEqual(contrast(entry["settings"]["foreground"], colors["editor.background"]), 4.5, (name, entry["name"]))
            for selector, foreground in theme["semanticTokenColors"].items():
                self.assertGreaterEqual(contrast(foreground, colors["editor.background"]), 4.5, (name, selector))
            for key in ("editor.selectionBackground", "editor.inactiveSelectionBackground", "editor.selectionHighlightBackground",
                        "editor.findMatchBackground", "editor.findMatchHighlightBackground", "editor.lineHighlightBackground",
                        "diffEditor.insertedTextBackground", "diffEditor.removedTextBackground"):
                self.assertEqual(len(colors[key]), 9)
                self.assertLess(int(colors[key][-2:], 16), 255, "Editor overlays preserve underlying decorations")
                foregrounds = {colors["editor.foreground"], *theme["semanticTokenColors"].values(),
                               *(entry["settings"]["foreground"] for entry in theme["tokenColors"])}
                for foreground in foregrounds:
                    with self.subTest(appearance=name, overlay=key, foreground=foreground):
                        self.assertGreaterEqual(contrast(foreground, composite(colors[key], colors["editor.background"])), 4.5)
            for background in ("editor.background", "input.background", "list.activeSelectionBackground"):
                self.assertGreaterEqual(contrast(colors["focusBorder"], colors[background]), 3, (name, background))

    def test_vsix_closed_inventory_xml_identity_assets_and_packaged_license(self):
        files = vscode.render_vscode(self.document)
        self.assertEqual(set(files), EXTENSION_FILES | {ARCHIVE, "manifest.json", "SHA256SUMS"})
        with zipfile.ZipFile(io.BytesIO(files[ARCHIVE])) as archive:
            self.assertEqual(set(archive.namelist()), EXTENSION_FILES | {"extension.vsixmanifest", "[Content_Types].xml"})
            self.assertIsNone(archive.testzip())
            for path in EXTENSION_FILES:
                self.assertEqual(archive.read(path), files[path])
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertNotIn("..", info.filename.split("/"))
            manifest = ET.fromstring(archive.read("extension.vsixmanifest"))
            self.assertEqual(manifest.tag, VSIX_NS + "PackageManifest")
            self.assertEqual(manifest.attrib, {"Version": "2.0.0"})
            identity = manifest.find(f"{VSIX_NS}Metadata/{VSIX_NS}Identity")
            self.assertEqual(identity.attrib, {"Language": "en-US", "Id": "clair-obscur", "Version": "0.1.0", "Publisher": "T92T1914"})
            target = manifest.find(f"{VSIX_NS}Installation/{VSIX_NS}InstallationTarget")
            self.assertEqual(target.attrib, {"Id": "Microsoft.VisualStudio.Code"})
            self.assertEqual(list(manifest.find(VSIX_NS + "Dependencies")), [])
            properties = manifest.findall(f"{VSIX_NS}Metadata/{VSIX_NS}Properties/{VSIX_NS}Property")
            self.assertIn({"Id": "Microsoft.VisualStudio.Code.Engine", "Value": "^1.100.0"}, [item.attrib for item in properties])
            assets = {item.attrib["Type"]: item.attrib for item in manifest.find(VSIX_NS + "Assets")}
            self.assertEqual(set(assets), {"Microsoft.VisualStudio.Code.Manifest", "Microsoft.VisualStudio.Services.Content.License"})
            self.assertEqual(assets["Microsoft.VisualStudio.Code.Manifest"]["Path"], "extension/package.json")
            self.assertEqual(assets["Microsoft.VisualStudio.Services.Content.License"]["Path"], "extension/LICENSE.txt")
            for item in assets.values():
                self.assertEqual(item["Addressable"], "true")
                self.assertIn(item["Path"], archive.namelist())
            types = ET.fromstring(archive.read("[Content_Types].xml"))
            self.assertEqual(types.tag, CONTENT_NS + "Types")
            self.assertEqual({item.get("Extension"): item.get("ContentType") for item in types},
                             {"json": "application/json", "vsixmanifest": "text/xml", "txt": "text/plain"})
        self.assertEqual(files["extension/LICENSE.txt"], (ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n").encode() + b"\n")

    def test_independent_manifest_and_checksums_cover_exact_output_bytes(self):
        files = vscode.render_vscode(self.document)
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["generator"], "themeforge.vscode")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["token_version"], "0.1.1")
        self.assertEqual(manifest["archive"], ARCHIVE)
        self.assertEqual(manifest["extension_id"], "T92T1914.clair-obscur")
        self.assertEqual(manifest["native_acceptance"], "unverified")
        records = manifest["files"]
        self.assertEqual({record["path"] for record in records}, EXTENSION_FILES | {ARCHIVE})
        self.assertEqual(len(records), 5)
        for record in records:
            self.assertEqual(record["bytes"], len(files[record["path"]]))
            self.assertEqual(record["sha256"], hashlib.sha256(files[record["path"]]).hexdigest())
        expected = "".join(f"{hashlib.sha256(payload).hexdigest()}  {path}\n"
                           for path, payload in sorted(files.items()) if path != "SHA256SUMS")
        self.assertEqual(files["SHA256SUMS"], expected.encode("ascii"))
        for path, payload in files.items():
            if path.endswith(".json"):
                self.assertNotRegex(payload.decode(), r"https?://|file://|[A-Za-z]:[\\/]|fontFamily|configurationDefaults")

    def test_determinism_no_input_mutation_and_shared_token_changes(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {name: dict(reversed(list(values.items())))
                               for name, values in reversed(list(self.document["themes"].items()))}
        original = vscode.render_vscode(self.document)
        self.assertEqual(vscode.render_vscode(reordered), original)
        self.assertEqual(self.document, before)
        changed = copy.deepcopy(self.document)
        changed["version"] = "2.3.4"
        changed["themes"]["Clair"]["canvas"] = "#f7f6f2"
        updated = vscode.render_vscode(changed)
        self.assertEqual(json.loads(updated["extension/themes/clair-color-theme.json"])["colors"]["activityBar.background"], "#f7f6f2")
        self.assertNotEqual(updated["extension/themes/clair-color-theme.json"], original["extension/themes/clair-color-theme.json"])
        self.assertEqual(updated["extension/themes/obscur-color-theme.json"], original["extension/themes/obscur-color-theme.json"])
        self.assertEqual(json.loads(updated["extension/package.json"])["version"], "0.1.0")
        self.assertEqual(json.loads(updated["manifest.json"])["token_version"], "2.3.4")

    def test_fresh_build_and_check_do_not_replace_any_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "vscode"
            result = vscode.build_vscode(self.document, output)
            self.assertEqual(result["version"], "0.1.0")
            before = snapshot(output)
            self.assertEqual(before, vscode.render_vscode(self.document))
            vscode.build_vscode(self.document, output, check=True)
            self.assertEqual(snapshot(output), before)
            with self.assertRaisesRegex(ValueError, "new output directory"):
                vscode.build_vscode(self.document, output)
            self.assertEqual(snapshot(output), before)

    def test_changed_missing_extra_and_extra_empty_directory_fail_without_repair(self):
        for mutation in ("changed", "missing", "extra-file", "extra-dir", "manifest", "checksum"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "vscode"
                vscode.build_vscode(self.document, output)
                theme = output / "extension/themes/clair-color-theme.json"
                if mutation == "changed": theme.write_bytes(theme.read_bytes() + b" ")
                elif mutation == "missing": theme.unlink()
                elif mutation == "extra-file": (output / "keep.txt").write_bytes(b"preserve")
                elif mutation == "extra-dir": (output / "keep").mkdir()
                elif mutation == "manifest": (output / "manifest.json").write_bytes(b"{}\n")
                else: (output / "SHA256SUMS").write_bytes(b"\n")
                before = snapshot(output)
                with self.assertRaisesRegex(ValueError, "differs"):
                    vscode.build_vscode(self.document, output, check=True)
                self.assertEqual(snapshot(output), before)
                if mutation == "extra-dir": self.assertTrue((output / "keep").is_dir())

    def test_foreign_empty_and_file_outputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("foreign", "empty"):
                output = base / name
                output.mkdir()
                if name == "foreign": (output / "keep.txt").write_bytes(b"exact bytes")
                before = snapshot(output)
                for check in (False, True):
                    with self.assertRaises(ValueError): vscode.build_vscode(self.document, output, check=check)
                    self.assertEqual(snapshot(output), before)
            output = base / "file"
            output.write_bytes(b"unchanged")
            with self.assertRaises(ValueError): vscode.build_vscode(self.document, output)
            self.assertEqual(output.read_bytes(), b"unchanged")

    def test_invalid_tokens_fail_before_creating_output(self):
        invalid = [None, [], {**self.document, "schema_version": True}, {**self.document, "version": None},
                   {**self.document, "themes": None}]
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        bad_color = copy.deepcopy(self.document)
        bad_color["themes"]["Clair"]["accent"] = "url(https://invalid.example/)"
        invalid.append(bad_color)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "vscode"
                with self.assertRaises(ValueError): vscode.build_vscode(document, output)
                self.assertFalse(output.exists())
        with self.assertRaises(ValueError): vscode.color_theme("other", self.document)

    def test_root_managed_and_linked_destinations_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(vscode, "ROOT", Path(temporary)):
            base = Path(temporary)
            for target in (base / "dist", base / "dist/vscode", Path(base.anchor)):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    vscode.build_vscode(self.document, target)
            self.assertFalse((base / "dist").exists())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            destination = base / "target"
            destination.mkdir()
            (destination / "keep.txt").write_bytes(b"unchanged")
            link = base / "link"
            try:
                link.symlink_to(destination, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink fixture unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "symlinks or reparse"):
                vscode.build_vscode(self.document, link / "vscode")
            self.assertEqual(snapshot(destination), {"keep.txt": b"unchanged"})

    def test_partial_write_failure_retains_evidence_and_refuses_replacement(self):
        original_open = Path.open
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial"
            failure = output / "extension/themes/obscur-color-theme.json"
            def open_with_failure(path, *args, **kwargs):
                if path == failure and args and args[0] == "xb":
                    raise OSError("retained simulated write interruption")
                return original_open(path, *args, **kwargs)
            with patch.object(Path, "open", open_with_failure):
                with self.assertRaisesRegex(OSError, "write interruption"):
                    vscode.build_vscode(self.document, output)
            before = snapshot(output)
            self.assertEqual(set(before), {"extension/package.json", "extension/LICENSE.txt", "extension/themes/clair-color-theme.json"})
            with self.assertRaisesRegex(ValueError, "new output directory"):
                vscode.build_vscode(self.document, output)
            with self.assertRaisesRegex(ValueError, "differs"):
                vscode.build_vscode(self.document, output, check=True)
            self.assertEqual(snapshot(output), before)

    def test_injected_directory_link_is_refused_after_reservation_and_before_writes(self):
        original_mkdir = Path.mkdir
        for stage in ("root-reserved", "directories-reserved"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                output = base / "output"
                external = base / "external"
                external.mkdir()
                (external / "keep.txt").write_bytes(b"external marker must remain exact")
                injected = False
                def mkdir_with_injection(path, *args, **kwargs):
                    nonlocal injected
                    result = original_mkdir(path, *args, **kwargs)
                    inject_here = output if stage == "root-reserved" else output / "extension/themes"
                    if path == inject_here and not injected:
                        injected = True
                        if stage == "directories-reserved":
                            (output / "extension/themes").rmdir()
                            (output / "extension").rmdir()
                        link = output / "extension"
                        if os.name == "nt":
                            import _winapi
                            _winapi.CreateJunction(str(external), str(link))
                        else:
                            link.symlink_to(external, target_is_directory=True)
                    return result
                with patch.object(Path, "mkdir", mkdir_with_injection):
                    with self.assertRaisesRegex(ValueError, "symlinks or reparse"):
                        vscode.build_vscode(self.document, output)
                self.assertTrue(injected)
                self.assertTrue(output.is_dir(), "Failed partial output remains available")
                self.assertFalse((output / "manifest.json").exists())
                self.assertEqual(snapshot(external), {"keep.txt": b"external marker must remain exact"})

    def test_cli_output_required_and_missing_check_does_not_create_output(self):
        with self.assertRaises(SystemExit) as error: vscode.main([])
        self.assertEqual(error.exception.code, 2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "vscode"
            self.assertEqual(vscode.main(["--output", str(output)]), 0)
            self.assertEqual(vscode.main(["--output", str(output), "--check"]), 0)
            missing = Path(temporary) / "missing"
            with self.assertRaises(SystemExit) as error: vscode.main(["--output", str(missing), "--check"])
            self.assertEqual(error.exception.code, 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
