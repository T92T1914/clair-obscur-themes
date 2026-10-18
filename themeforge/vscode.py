"""Generate a separate declarative VS Code color-theme candidate and local VSIX."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

from .build import _checksum_bytes, _digest, _inventory, _json_bytes, _safe_destination, _zip_bytes
from .legal import license_text
from .tokens import validate, load


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
ENGINE = "^1.100.0"
PUBLISHER = "T92T1914"
NAME = "clair-obscur"
ARCHIVE = f"Clair-Obscur-VSCode-{VERSION}.vsix"
VSIX_NAMESPACE = "http://schemas.microsoft.com/developer/vsx-schema/2011"
CONTENT_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"

# Theme colors leave layout, fonts, scaling, syntax grammars and settings with VS Code.
COLOR_TOKENS = {
    "foreground": "text", "descriptionForeground": "muted",
    "disabledForeground": "disabled", "errorForeground": "error", "focusBorder": "focus",
    "widget.border": "border", "textLink.foreground": "accent", "textLink.activeForeground": "focus",
    "textCodeBlock.background": "code", "textBlockQuote.background": "panel",
    "textBlockQuote.border": "divider", "textSeparator.foreground": "divider",
    "activityBar.background": "canvas", "activityBar.foreground": "text",
    "activityBar.inactiveForeground": "muted", "activityBar.activeBorder": "accent",
    "sideBar.background": "panel", "sideBar.foreground": "text", "sideBar.border": "divider",
    "sideBarTitle.foreground": "text", "sideBarSectionHeader.background": "control",
    "sideBarSectionHeader.foreground": "text", "sideBarSectionHeader.border": "divider",
    "titleBar.activeBackground": "canvas", "titleBar.activeForeground": "text",
    "titleBar.inactiveBackground": "control", "titleBar.inactiveForeground": "muted",
    "titleBar.border": "divider", "statusBar.background": "panel", "statusBar.foreground": "text",
    "statusBar.border": "divider", "statusBar.noFolderBackground": "panel",
    "statusBar.noFolderForeground": "text", "statusBar.debuggingBackground": "accent",
    "statusBar.debuggingForeground": "on_accent",
    "editorGroup.border": "divider", "editorGroupHeader.tabsBackground": "panel",
    "tab.activeBackground": "code", "tab.activeForeground": "text",
    "tab.inactiveBackground": "panel", "tab.inactiveForeground": "muted",
    "tab.border": "divider", "tab.activeBorderTop": "focus",
    "editor.background": "code", "editor.foreground": "text", "editorCursor.foreground": "accent",
    "editorLineNumber.foreground": "muted", "editorLineNumber.activeForeground": "text",
    "editorGutter.background": "code", "editorWhitespace.foreground": "divider",
    "editorIndentGuide.background1": "divider", "editorIndentGuide.activeBackground1": "border",
    "editorError.foreground": "error", "editorWarning.foreground": "warning",
    "editorInfo.foreground": "accent", "editorHint.foreground": "muted",
    "editorWidget.background": "panel", "editorWidget.foreground": "text",
    "editorWidget.border": "border", "editorSuggestWidget.background": "panel",
    "editorSuggestWidget.foreground": "text", "editorSuggestWidget.border": "border",
    "editorSuggestWidget.selectedBackground": "selected", "editorSuggestWidget.highlightForeground": "accent",
    "list.activeSelectionBackground": "selected", "list.activeSelectionForeground": "text",
    "list.inactiveSelectionBackground": "control", "list.inactiveSelectionForeground": "text",
    "list.focusBackground": "selected", "list.focusForeground": "text", "list.focusOutline": "focus",
    "list.hoverBackground": "hover", "list.hoverForeground": "text", "list.highlightForeground": "accent",
    "input.background": "control", "input.foreground": "text", "input.border": "border",
    "input.placeholderForeground": "muted", "inputOption.activeBackground": "selected",
    "inputOption.activeForeground": "text", "inputOption.activeBorder": "focus",
    "inputValidation.errorBackground": "panel", "inputValidation.errorForeground": "error",
    "inputValidation.errorBorder": "error", "inputValidation.warningBackground": "panel",
    "inputValidation.warningForeground": "warning", "inputValidation.warningBorder": "warning",
    "inputValidation.infoBackground": "panel", "inputValidation.infoForeground": "accent",
    "inputValidation.infoBorder": "accent", "dropdown.background": "control",
    "dropdown.foreground": "text", "dropdown.border": "border",
    "button.background": "accent", "button.foreground": "on_accent", "button.hoverBackground": "focus",
    "button.secondaryBackground": "control", "button.secondaryForeground": "text",
    "button.secondaryHoverBackground": "hover", "badge.background": "accent", "badge.foreground": "on_accent",
    "panel.background": "canvas", "panel.border": "divider", "panelTitle.activeForeground": "text",
    "panelTitle.inactiveForeground": "muted", "panelTitle.activeBorder": "focus",
    "notificationCenterHeader.background": "control", "notifications.background": "panel",
    "notifications.foreground": "text", "notifications.border": "border",
    "quickInput.background": "panel", "quickInput.foreground": "text",
    "progressBar.background": "accent",
}

# Transparent layers retain host decorations instead of painting opaque rectangles.
OVERLAY_TOKENS = {
    "editor.selectionBackground": ("selected", "aa"),
    "editor.inactiveSelectionBackground": ("selected", "66"),
    "editor.selectionHighlightBackground": ("accent", "22"),
    "editor.findMatchBackground": ("accent", "22"),
    "editor.findMatchHighlightBackground": ("accent", "22"),
    "editor.lineHighlightBackground": ("hover", "33"),
    "diffEditor.insertedTextBackground": ("success", "22"),
    "diffEditor.removedTextBackground": ("error", "22"),
}

SYNTAX_TOKENS = (
    ("Comments", ("comment", "punctuation.definition.comment"), "muted"),
    ("Keywords", ("keyword", "storage"), "accent"),
    ("Strings", ("string",), "success"),
    ("Constants", ("constant.numeric", "constant.language", "constant.character"), "warning"),
    ("Functions", ("entity.name.function", "support.function"), "accent"),
    ("Types", ("entity.name.type", "entity.name.class", "support.type", "support.class"), "accent"),
    ("Variables", ("variable",), "text"),
    ("Invalid", ("invalid",), "error"),
    ("Headings", ("markup.heading",), "accent"),
    ("Inserted", ("markup.inserted",), "success"),
    ("Deleted", ("markup.deleted",), "error"),
    ("Inline code", ("markup.inline.raw",), "warning"),
)
SEMANTIC_TOKENS = {
    "namespace": "accent", "class": "accent", "enum": "accent", "interface": "accent",
    "struct": "accent", "type": "accent", "typeParameter": "accent", "parameter": "text",
    "variable": "text", "property": "text", "enumMember": "warning", "event": "accent",
    "function": "accent", "method": "accent", "macro": "accent", "label": "text",
    "comment": "muted", "string": "success", "keyword": "accent", "number": "warning",
    "regexp": "success", "operator": "accent", "decorator": "accent",
}


def _validated(document: dict) -> None:
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    try:
        validate(document)
    except (TypeError, AttributeError) as error:
        raise ValueError("Malformed token document") from error


def extension_manifest() -> dict:
    return {
        "name": NAME, "displayName": "Clair and Obscur", "publisher": PUBLISHER,
        "version": VERSION, "description": "Shared light and dark colors for VS Code. Fonts and settings remain host controlled.",
        "engines": {"vscode": ENGINE}, "categories": ["Themes"], "license": "MIT",
        "contributes": {"themes": [
            {"id": "clair-obscur-clair", "label": "Clair", "uiTheme": "vs", "path": "./themes/clair-color-theme.json"},
            {"id": "clair-obscur-obscur", "label": "Obscur", "uiTheme": "vs-dark", "path": "./themes/obscur-color-theme.json"},
        ]},
    }


def color_theme(name: str, document: dict) -> dict:
    _validated(document)
    if name not in ("Clair", "Obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    palette = document["themes"][name]
    colors = {key: palette[role].lower() for key, role in COLOR_TOKENS.items()}
    colors.update({key: palette[role].lower() + alpha for key, (role, alpha) in OVERLAY_TOKENS.items()})
    return {
        "name": name, "colors": colors,
        "tokenColors": [{"name": label, "scope": list(scopes), "settings": {"foreground": palette[role].lower()}}
                        for label, scopes, role in SYNTAX_TOKENS],
        "semanticHighlighting": True,
        "semanticTokenColors": {selector: palette[role].lower() for selector, role in SEMANTIC_TOKENS.items()},
    }


def _xml(element: ET.Element) -> bytes:
    ET.indent(element, space="  ")
    return ET.tostring(element, encoding="utf-8", xml_declaration=True) + b"\n"


def _vsix_manifest() -> bytes:
    # The container follows microsoft/vscode-vsce's public package.ts format.
    package = ET.Element("PackageManifest", {"Version": "2.0.0", "xmlns": VSIX_NAMESPACE})
    metadata = ET.SubElement(package, "Metadata")
    ET.SubElement(metadata, "Identity", {"Language": "en-US", "Id": NAME, "Version": VERSION, "Publisher": PUBLISHER})
    ET.SubElement(metadata, "DisplayName").text = "Clair and Obscur"
    ET.SubElement(metadata, "Description", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}).text = extension_manifest()["description"]
    ET.SubElement(metadata, "Categories").text = "Themes"
    properties = ET.SubElement(metadata, "Properties")
    ET.SubElement(properties, "Property", {"Id": "Microsoft.VisualStudio.Code.Engine", "Value": ENGINE})
    installation = ET.SubElement(package, "Installation")
    ET.SubElement(installation, "InstallationTarget", {"Id": "Microsoft.VisualStudio.Code"})
    ET.SubElement(package, "Dependencies")
    assets = ET.SubElement(package, "Assets")
    ET.SubElement(assets, "Asset", {"Type": "Microsoft.VisualStudio.Code.Manifest", "Path": "extension/package.json", "Addressable": "true"})
    ET.SubElement(assets, "Asset", {"Type": "Microsoft.VisualStudio.Services.Content.License", "Path": "extension/LICENSE.txt", "Addressable": "true"})
    return _xml(package)


def _content_types() -> bytes:
    types = ET.Element("Types", {"xmlns": CONTENT_NAMESPACE})
    for ending, content_type in (("json", "application/json"), ("vsixmanifest", "text/xml"), ("txt", "text/plain")):
        ET.SubElement(types, "Default", {"Extension": ending, "ContentType": content_type})
    return _xml(types)


def _vsix_bytes(extension: dict[str, bytes]) -> bytes:
    # Preserve the desktop ZIP path policy. VSIX adds one fixed bracketed member
    # required by its container format, never an arbitrary caller-supplied name.
    ordinary = {**extension, "extension.vsixmanifest": _vsix_manifest()}
    buffer = io.BytesIO(_zip_bytes(ordinary))
    with zipfile.ZipFile(buffer, "a", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("[Content_Types].xml", date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, _content_types())
    return buffer.getvalue()


def render_vscode(document: dict) -> dict[str, bytes]:
    """Return a paired extension, deterministic VSIX and independent identities."""
    _validated(document)
    files = {"extension/package.json": _json_bytes(extension_manifest()),
             "extension/LICENSE.txt": license_text().encode("utf-8")}
    for name in ("Clair", "Obscur"):
        files[f"extension/themes/{name.lower()}-color-theme.json"] = _json_bytes(color_theme(name, document))
    files[ARCHIVE] = _vsix_bytes(files)
    manifest = {
        "schema_version": 1, "generator": "themeforge.vscode", "version": VERSION,
        "token_schema": document["schema_version"], "token_version": document["version"],
        "tokens_sha256": _digest(_json_bytes(document)),
        "extension_id": f"{PUBLISHER}.{NAME}", "engine": ENGINE, "archive": ARCHIVE,
        "packaging": "Deterministic local VSIX container; not a vsce execution or Marketplace submission",
        "scope": "Declarative workbench, TextMate and semantic colors; no font or configuration changes",
        "native_acceptance": "unverified",
        "files": [{"path": path, "bytes": len(payload), "sha256": _digest(payload)}
                  for path, payload in sorted(files.items())],
    }
    files["manifest.json"] = _json_bytes(manifest)
    files["SHA256SUMS"] = _checksum_bytes(files)
    return files


def _safe_output(path: Path) -> Path:
    path = _safe_destination(path)
    if path == ROOT / "dist" or ROOT / "dist" in path.parents:
        raise ValueError("VS Code output must stay outside managed desktop dist")
    return path


def build_vscode(document: dict, output: Path, *, check: bool = False) -> dict:
    """Create a new independent tree, or compare exact existing output without repair."""
    files = render_vscode(document)
    output = _safe_output(Path(output))
    expected_directories = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}
    if check:
        if not output.is_dir():
            raise ValueError("VS Code check requires an existing generated output directory")
        actual, directories = _inventory(output)
        if actual != files or {directory.relative_to(output).as_posix() for directory in directories} != expected_directories:
            raise ValueError("VS Code output differs: changed, missing or extra entries")
    else:
        if output.exists():
            raise ValueError("VS Code generation requires a new output directory; existing entries are preserved")
        output.parent.mkdir(parents=True, exist_ok=True)
        output = _safe_output(output)
        output.mkdir(exist_ok=False)
        # Reserve every expected directory exclusively. Do not adopt a subtree
        # inserted between the root reservation and its first write.
        for name in sorted(expected_directories, key=lambda name: (len(PurePosixPath(name).parts), name)):
            directory = _safe_destination(output / name)
            directory.mkdir(exist_ok=False)
        for name, payload in files.items():
            target = _safe_destination(output / name)
            # A failed exclusive write retains the incomplete output as evidence.
            with target.open("xb") as stream:
                stream.write(payload)
    return json.loads(files["manifest.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, required=True, help="A new directory outside managed desktop dist")
    parser.add_argument("--check", action="store_true", help="Compare exact generated output without writing")
    args = parser.parse_args(argv)
    try:
        manifest = build_vscode(load(args.tokens), args.output, check=args.check)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.exit(1, f"VS Code generation: {error}\n")
    print(f'{"Verified" if args.check else "Generated"} paired VS Code {manifest["version"]} candidate; native acceptance unverified')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
