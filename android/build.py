"""Build one explicitly selected icon pack with the existing Android SDK path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.16"
VERSION_CODE = 17
ARTWORK_VERSION = "0.32.0"
PACKAGE = "io.github.t92t1914.obscuricons"
BUILD_TOOLS = "36.1.0"
API = 36
MIN_API = 26
ANDROID = "{http://schemas.android.com/apk/res/android}"
ET.register_namespace("android", ANDROID[1:-1])


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _ordinary(path: Path) -> Path:
    """Reject links before any resolve or traversal into an input or output."""
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("Linked or reparse paths are not supported: " + str(part))
    return path


def _identity(path: Path) -> dict:
    _ordinary(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > 256 * 1024 * 1024:
        raise ValueError("Expected a bounded regular file: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in fields):
        raise ValueError("Input changed while reading: " + str(path))
    return {"bytes": before.st_size, "sha256": digest.hexdigest()}


def _tree_files(root: Path) -> list[Path]:
    _ordinary(root)
    if not root.is_dir():
        raise ValueError("Expected a source directory: " + str(root))
    result = []
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in folders:
            _ordinary(Path(directory) / name)
        for name in files:
            path = _ordinary(Path(directory) / name)
            if not path.is_file():
                raise ValueError("Source entries must be regular files: " + str(path))
            result.append(path)
    return sorted(result)


def _build_inputs(static: Path, components: Path, png: Path, tools: dict) -> list[Path]:
    sources = _tree_files(static) + [Path(__file__).absolute(), ROOT / "themeforge/android_iconpack.py",
        ROOT / "themeforge/icons.py", ROOT / "themeforge/icon_craft.py", ROOT / "themeforge/icon_apps.py",
        ROOT / "tokens-monochrome.json", components, ROOT / "android/iconpack/components.json", png / "manifest.json"]
    return sorted(set(sources + list(tools.values())))


def _verify_input_identities(inputs: list[Path], identities: dict) -> None:
    if {str(path): _identity(path) for path in inputs} != identities:
        raise ValueError("Build source or SDK inputs changed. Preserve this build as unqualified.")


def _validate_output(output: Path, inputs: list[Path]) -> None:
    _ordinary(output)
    if output.exists():
        raise ValueError("The output already exists. Select a fresh directory to preserve it.")
    if output.is_relative_to(ROOT):
        raise ValueError("Build output must stay outside the repository.")
    if any(output.is_relative_to(path) for path in inputs):
        raise ValueError("Build output must stay outside the selected SDK, JDK and artwork inputs.")


def _copy_static(source: Path, project: Path) -> None:
    files = _tree_files(source)
    targets = [(path, project / path.relative_to(source)) for path in files]
    # Reject the complete collision set before copying any static file.
    for _, target in targets:
        _ordinary(target)
        if target.exists():
            raise ValueError("Static app file collides with generated artwork: " + str(target))
    for path, target in targets:
        identity = _identity(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        _ordinary(target.parent)
        with path.open("rb") as source_stream, target.open("xb") as dest:
            for block in iter(lambda: source_stream.read(1024 * 1024), b""):
                dest.write(block)
        if _identity(target) != identity or _identity(path) != identity:
            raise ValueError("Static source changed during copying: " + str(path))


def _configuration(selected=None):
    # Import the same closed identity table as the preparer, only when requested.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from themeforge.android_iconpack import IconPackConfiguration, configuration
    default = configuration()
    if (default.package, default.version, default.version_code) != (PACKAGE, VERSION, VERSION_CODE):
        raise ValueError("Icon-pack preparer defaults differ from the build identity.")
    if selected is None:
        return default
    if not isinstance(selected, IconPackConfiguration) or selected is not configuration(selected.appearance):
        raise ValueError("Unsupported icon-pack build configuration.")
    return selected


def _version_label(configuration=None) -> str:
    selected = _configuration(configuration)
    return f"Icon pack {selected.version} | Artwork {ARTWORK_VERSION}"


def _activity_path(configuration) -> Path:
    return Path("src", *configuration.package.split("."), "IconPackActivity.java")


def _strings(configuration) -> dict[str, str]:
    result = {"app_name": configuration.label, "versions": _version_label(configuration),
              "introduction": "Black and white icons from Clair and Obscur.",
              "instructions": "In Theme Park, edit an icon theme, open Icon, then Iconpack, and select Obscur Icons. "
                              "Preview the result and save it as a new theme before applying."}
    if configuration.appearance == "Clair":
        result.update(introduction="Black icons on white tiles from Clair and Obscur.",
            instructions="In Theme Park, edit a separate icon-theme draft, open Icon, then Iconpack, and select Clair Icons. "
                         "Preview it before saving or applying. Keep your working theme available for restoration. "
                         "Installing this pack does not apply a theme.")
    return result


def _colors(configuration) -> dict[str, str]:
    background, foreground = ("#FFFFFF", "#000000") if configuration.appearance == "Clair" else ("#000000", "#FFFFFF")
    return {"iconpack_background": background, "iconpack_foreground": foreground}


def _style(configuration) -> tuple[str, dict[str, str]]:
    light = configuration.appearance == "Clair"
    items = {"android:fontFamily": "sans", "android:windowBackground": "@color/iconpack_background",
             "android:colorAccent": "@color/iconpack_foreground", "android:windowLightStatusBar": str(light).lower(),
             "android:windowLightNavigationBar": str(light).lower()}
    if light:
        items.update({"android:statusBarColor": "@color/iconpack_background",
                      "android:navigationBarColor": "@color/iconpack_background", "android:forceDarkAllowed": "false"})
    return ("android:style/Theme.Material.Light.NoActionBar" if light else "android:style/Theme.Material.NoActionBar", items)


def _manifest_contract(root: ET.Element, configuration, *, queries: list[str]) -> None:
    if (root.tag != "manifest" or (root.get("package"), root.get(ANDROID + "versionCode"),
            root.get(ANDROID + "versionName")) != (configuration.package, str(configuration.version_code), configuration.version)):
        raise ValueError("Static app manifest package/version differs from the build identity.")
    allowed = {"package", ANDROID + "versionCode", ANDROID + "versionName", ANDROID + "compileSdkVersion",
               ANDROID + "compileSdkVersionCodename", "platformBuildVersionCode", "platformBuildVersionName"}
    if set(root.attrib) - allowed:
        raise ValueError("Unexpected manifest identity or shared-UID attributes.")
    if any(element.tag.startswith("uses-permission") for element in root.iter()):
        raise ValueError("This icon pack must not request permissions.")
    if [node.tag for node in root] != ["uses-sdk", "queries", "application"]:
        raise ValueError("The icon-pack manifest component inventory differs from the supported app.")
    sdk = root.find("uses-sdk")
    if sdk.attrib != {ANDROID + "minSdkVersion": str(MIN_API), ANDROID + "targetSdkVersion": str(API)}:
        raise ValueError("The app API requirements differ from this build.")
    query = root.find("queries")
    if query.attrib or any(node.tag != "package" or list(node) for node in query):
        raise ValueError("The manifest must contain only the supported package queries.")
    if [node.attrib for node in query] != [{ANDROID + "name": name} for name in queries]:
        raise ValueError("Manifest package queries differ from the ordered catalog.")
    app = root.find("application")
    required = {ANDROID + "label": "@string/app_name", ANDROID + "icon": "@drawable/co_settings",
                ANDROID + "allowBackup": "false", ANDROID + "fullBackupContent": "false",
                ANDROID + "supportsRtl": "true", ANDROID + "theme": "@style/IconPackTheme"}
    if app.attrib != required or [node.tag for node in app] != ["activity"]:
        raise ValueError("Application labels, theme, backup flags or component inventory differ.")
    activity = app.find("activity")
    if activity.attrib != {ANDROID + "name": configuration.package + ".IconPackActivity", ANDROID + "exported": "true"}:
        raise ValueError("Activity namespace or exported state differs from the selected package.")
    expected = [("android.intent.action.MAIN", "android.intent.category.LAUNCHER"),
                ("org.adw.launcher.THEMES", "android.intent.category.DEFAULT"),
                ("org.adw.ActivityStarter.THEMES", "android.intent.category.DEFAULT"),
                ("com.novalauncher.THEME", "android.intent.category.DEFAULT")]
    observed = []
    for intent in activity:
        if intent.tag != "intent-filter" or intent.attrib or [node.tag for node in intent] != ["action", "category"]:
            raise ValueError("Unexpected icon-pack intent-filter structure.")
        if any(list(node) or set(node.attrib) != {ANDROID + "name"} for node in intent):
            raise ValueError("Unexpected icon-pack intent-filter attributes.")
        observed.append((intent[0].get(ANDROID + "name"), intent[1].get(ANDROID + "name")))
    if observed != expected:
        raise ValueError("The four launcher/icon-pack intent filters must remain exact.")


def _validate_source_identity(source: Path, preparer_version: str, preparer_artwork_version: str,
                              configuration=None) -> None:
    selected = _configuration(configuration)
    if (preparer_version, preparer_artwork_version) != (selected.version, ARTWORK_VERSION):
        raise ValueError("Icon-pack preparer versions differ from the build identity.")
    manifest, strings = source / "AndroidManifest.xml", source / "res/values/strings.xml"
    _identity(manifest)
    _identity(strings)
    try:
        root = ET.parse(manifest).getroot()
        resources = ET.parse(strings).getroot()
    except ET.ParseError as error:
        raise ValueError("Static app identity XML is invalid.") from error
    _manifest_contract(root, selected, queries=[])
    labels = resources.findall("string[@name='versions']")
    if (resources.tag != "resources" or len(labels) != 1 or list(labels[0])
            or labels[0].text != _version_label(selected)):
        raise ValueError("Static versions string differs from the pack and artwork identity.")
    for name, text in _strings(selected).items():
        values = resources.findall("string[@name='" + name + "']")
        if len(values) != 1 or list(values[0]) or values[0].text != text:
            raise ValueError("Static app label/help differs from the selected identity: " + name)
    for name in ("colors.xml", "styles.xml"):
        _identity(source / "res/values" / name)
    colors = ET.parse(source / "res/values/colors.xml").getroot()
    if colors.tag != "resources" or any(node.tag != "color" or list(node) for node in colors) or len(colors) != 2 or \
            {node.get("name"): node.text for node in colors} != _colors(selected):
        raise ValueError("Static app colors differ from the selected appearance.")
    styles = ET.parse(source / "res/values/styles.xml").getroot()
    parent, items = _style(selected)
    if styles.tag != "resources" or len(styles) != 1 or styles[0].tag != "style" or \
            styles[0].attrib != {"name": "IconPackTheme", "parent": parent} or \
            len(styles[0]) != len(items) or any(node.tag != "item" or list(node) for node in styles[0]) or \
            {node.get("name"): node.text for node in styles[0]} != items:
        raise ValueError("Static native theme differs from the selected appearance.")
    java = source / _activity_path(selected)
    _identity(java)
    if [path.relative_to(source) for path in _tree_files(source / "src")] != [_activity_path(selected)] or \
            re.findall(r"^package ([A-Za-z0-9_.]+);$", java.read_text(encoding="utf-8"), re.MULTILINE) != [selected.package]:
        raise ValueError("Static Activity Java namespace differs from the selected package.")


def _configure_project(project: Path, configuration) -> None:
    """Materialize only the closed Clair fields in the fresh owned build copy."""
    selected, default = _configuration(configuration), _configuration()
    if project.is_relative_to(ROOT):
        raise ValueError("Variant rendering must not edit repository source.")
    _validate_source_identity(project, default.version, ARTWORK_VERSION, default)
    if selected == default:
        return
    manifest = project / "AndroidManifest.xml"
    tree = ET.parse(manifest)
    tree.getroot().set("package", selected.package)
    tree.getroot().set(ANDROID + "versionCode", str(selected.version_code))
    tree.getroot().set(ANDROID + "versionName", selected.version)
    tree.getroot().find("application/activity").set(ANDROID + "name", selected.package + ".IconPackActivity")
    tree.write(manifest, encoding="utf-8", xml_declaration=True)
    for filename, tag, values in (("strings.xml", "string", _strings(selected)), ("colors.xml", "color", _colors(selected))):
        path = project / "res/values" / filename
        tree = ET.parse(path)
        for name, text in values.items():
            tree.getroot().find(tag + "[@name='" + name + "']").text = text
        tree.write(path, encoding="utf-8", xml_declaration=True)
    path = project / "res/values/styles.xml"
    tree = ET.parse(path)
    parent, values = _style(selected)
    tree.getroot()[0].set("parent", parent)
    for item in tree.getroot()[0]:
        item.text = values[item.get("name")]
    existing = {item.get("name") for item in tree.getroot()[0]}
    for name, text in values.items():
        if name not in existing:
            ET.SubElement(tree.getroot()[0], "item", {"name": name}).text = text
    tree.write(path, encoding="utf-8", xml_declaration=True)
    old_java, new_java = project / _activity_path(default), project / _activity_path(selected)
    text = old_java.read_text(encoding="utf-8")
    text, count = re.subn(r"^package " + re.escape(default.package) + r";$", "package " + selected.package + ";", text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected exactly one template Java package declaration.")
    _ordinary(new_java)
    new_java.parent.mkdir(parents=True, exist_ok=True)
    with new_java.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    old_java.unlink()
    _validate_source_identity(project, selected.version, ARTWORK_VERSION, selected)


def _catalog_packages(project: Path, configuration=None) -> list[str]:
    selected = _configuration(configuration)
    catalog_path = project / "assets/catalog.json"
    _identity(catalog_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if set(catalog) != {"schema_version", "artwork_version", "pack_version", "packages"}:
        raise ValueError("The public package catalog has unexpected fields.")
    if (catalog["schema_version"], catalog["artwork_version"], catalog["pack_version"]) != (1, ARTWORK_VERSION, selected.version):
        raise ValueError("The public package catalog version is unsupported.")
    packages = []
    if not isinstance(catalog["packages"], list) or not catalog["packages"]:
        raise ValueError("The public package catalog is empty.")
    for row in catalog["packages"]:
        if not isinstance(row, dict) or set(row) != {"package", "label", "id"}:
            raise ValueError("Unexpected public package entry.")
        if not isinstance(row["package"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", row["package"]):
            raise ValueError("Invalid public package name.")
        if not isinstance(row["label"], str) or not row["label"] or not isinstance(row["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]*", row["id"]):
            raise ValueError("Invalid public package label or artwork ID.")
        packages.append(row["package"])
    if len(packages) != len(set(packages)):
        raise ValueError("Duplicate public package query.")
    return packages


def _write_queries(project: Path, configuration=None) -> list[str]:
    selected = _configuration(configuration)
    packages = _catalog_packages(project, selected)
    manifest = project / "AndroidManifest.xml"
    _identity(manifest)
    tree = ET.parse(manifest)
    root = tree.getroot()
    if root.tag != "manifest" or root.attrib.get("package") != selected.package:
        raise ValueError("The static app manifest has an unexpected package.")
    if any(element.tag.startswith("uses-permission") for element in root.iter()):
        raise ValueError("This icon pack must not request permissions.")
    queries = root.findall("queries")
    if len(queries) > 1 or any(list(query) or query.attrib for query in queries):
        raise ValueError("Static package queries must be empty before catalog generation.")
    query = queries[0] if queries else ET.Element("queries")
    if not queries:
        application = root.find("application")
        root.insert(list(root).index(application) if application is not None else len(root), query)
    for package in packages:
        ET.SubElement(query, "package", {ANDROID + "name": package})
    tree.write(manifest, encoding="utf-8", xml_declaration=True)
    return packages


def _compiled_pairs(text: str) -> list[tuple[str, str]]:
    pairs, current = [], None
    for line in text.splitlines() + ["E: end"]:
        if re.match(r"\s*E:", line):
            if current is not None:
                if set(current) != {"component", "drawable"}:
                    raise ValueError("Compiled appfilter item has unexpected attributes.")
                pairs.append((current["component"], current["drawable"]))
            current = {} if re.match(r"\s*E: item(?:\s|$)", line) else None
        elif current is not None:
            match = re.match(r'\s*A: (component|drawable)(?:\([^)]*\))?="([^"]*)"', line)
            if match:
                if match[1] in current:
                    raise ValueError("Duplicate compiled appfilter attribute.")
                current[match[1]] = match[2]
    return pairs


def _compiled_version_label(text: str, configuration=None) -> str:
    declarations, values, current = 0, [], False
    for line in text.splitlines():
        resource = re.match(r"\s*resource\s+0x[0-9a-fA-F]+\s+(\S+)", line)
        if resource:
            current = resource[1] == "string/versions"
            declarations += int(current)
        elif re.match(r"\s*(?:type|Package)\s", line):
            current = False
        elif current and line.strip():
            values.append(line.strip())
    if declarations != 1 or values != ['() "' + _version_label(configuration) + '"']:
        raise ValueError("Compiled APK versions string differs from the pack and artwork identity.")
    return _version_label(configuration)


def _resource_blocks(text: str) -> dict[str, tuple[str, list[str]]]:
    result, current = {}, None
    for line in text.splitlines():
        match = re.match(r"\s*resource\s+(0x[0-9a-fA-F]+)\s+(\S+)", line)
        if match:
            if match[2] in result:
                raise ValueError("Duplicate compiled resource: " + match[2])
            current = match[2]
            result[current] = (match[1].lower(), [])
        elif re.match(r"\s*(?:type|Package)\s", line):
            current = None
        elif current and line.strip():
            result[current][1].append(line.strip())
    return result


def _compiled_appearance(text: str, configuration) -> dict:
    selected = _configuration(configuration)
    if re.findall(r"^Package name=(\S+) id=7f$", text, re.MULTILINE) != [selected.package]:
        raise ValueError("Compiled resources use the wrong package namespace.")
    blocks = _resource_blocks(text)
    for name, expected in _strings(selected).items():
        if blocks.get("string/" + name, (None, []))[1] != ['() "' + expected + '"']:
            raise ValueError("Compiled app label/help differs from the selected identity: " + name)
    for name, expected in _colors(selected).items():
        values = blocks.get("color/" + name, (None, []))[1]
        if values != ["() #ff" + expected[1:].lower()]:
            raise ValueError("Compiled app colors differ from the selected appearance: " + name)
    # Public android.R.style and R.attr IDs, not build-dependent application IDs.
    parent = "0x01030241" if selected.appearance == "Clair" else "0x0103022e"
    values = blocks.get("style/IconPackTheme", (None, []))[1]
    if not values or values[0] != "() (style) size=" + str(len(_style(selected)[1])) + " parent=" + parent:
        raise ValueError("Compiled native theme parent differs from the selected appearance.")
    # AAPT2 prints local color names in style bags. Their unique values were checked above.
    background = "@color/iconpack_background"
    foreground = "@color/iconpack_foreground"
    light = str(selected.appearance == "Clair").lower()
    expected = {"0x01010054": background, "0x010103ac": '"sans"', "0x01010435": foreground,
                "0x010104e0": light, "0x0101056c": light}
    if selected.appearance == "Clair":
        expected.update({"0x01010451": background, "0x01010452": background, "0x0101058c": "false"})
    items = {}
    for value in values[1:]:
        match = re.fullmatch(r"(0x[0-9a-fA-F]+)=(.*)", value)
        if not match or match[1].lower() in items:
            raise ValueError("Unexpected or duplicate compiled native theme item.")
        items[match[1].lower()] = match[2]
    if items != expected:
        raise ValueError("Compiled native theme colors or system-bar states differ.")
    return blocks


def _compiled_manifest(text: str) -> ET.Element:
    roots, stack = [], []
    for line in text.splitlines():
        element = re.match(r"^(\s*)E: ([A-Za-z0-9_.-]+)(?:\s|$)", line)
        if element:
            depth = len(element[1])
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node = ET.Element(element[2])
            if stack:
                stack[-1][1].append(node)
            else:
                roots.append(node)
            stack.append((depth, node))
        else:
            attribute = re.match(r"\s*A: ([^=]+)=(.*)", line)
            if not attribute:
                continue
            if not stack:
                raise ValueError("Compiled manifest attribute has no element.")
            name = re.sub(r"\(0x[0-9a-fA-F]+\)$", "", attribute[1])
            prefix = "http://schemas.android.com/apk/res/android:"
            if name.startswith(prefix):
                name = ANDROID + name[len(prefix):]
            elif name.startswith("android:"):
                name = ANDROID + name[8:]
            value = attribute[2].split(" (Raw:", 1)[0]
            if value.startswith('"'):
                value = json.loads(value)
            numeric = re.fullmatch(r"\(type 0x([0-9a-fA-F]+)\)0x([0-9a-fA-F]+)", value)
            if numeric:
                value = str(bool(int(numeric[2], 16))).lower() if int(numeric[1], 16) == 18 else str(int(numeric[2], 16))
            if name in stack[-1][1].attrib:
                raise ValueError("Duplicate compiled manifest attribute.")
            stack[-1][1].set(name, value)
    if len(roots) != 1:
        raise ValueError("Expected exactly one compiled manifest root.")
    return roots[0]


def _compiled_manifest_identity(text: str, project: Path, configuration, blocks: dict) -> int:
    root = _compiled_manifest(text)
    app = root.find("application")
    if app is None:
        raise ValueError("Compiled manifest has no application.")
    for attribute, resource in (("label", "string/app_name"), ("icon", "drawable/co_settings"), ("theme", "style/IconPackTheme")):
        if resource not in blocks or app.get(ANDROID + attribute) != "@" + blocks[resource][0]:
            raise ValueError("Compiled application resource reference differs: " + attribute)
        app.set(ANDROID + attribute, "@" + resource)
    queries = _catalog_packages(project, configuration)
    try:
        _manifest_contract(root, configuration, queries=queries)
    except ValueError as error:
        raise ValueError("Compiled manifest differs: " + str(error)) from error
    return len(queries)


def _compiled_activity_class(text: str, configuration) -> int:
    descriptors, blocks, active = [], 0, False
    for line in text.splitlines():
        if re.match(r"^Class #\d+(?:\s|$)", line):
            blocks += 1
            active = True
        else:
            match = re.fullmatch(r"\s*Class descriptor\s*:\s*'(L[^']+;)'\s*", line)
            if match:
                if not active:
                    raise ValueError("DEX class descriptor is outside a class-definition block.")
                descriptors.append(match[1])
                active = False
    expected = "L" + configuration.package.replace(".", "/") + "/IconPackActivity;"
    if not blocks or blocks != len(descriptors) or len(descriptors) != len(set(descriptors)) or expected not in descriptors:
        raise ValueError("Compiled DEX does not define the selected launchable Activity.")
    for other in ("io.github.t92t1914.obscuricons", "io.github.t92t1914.clairicons"):
        if other != configuration.package and any(name.startswith("L" + other.replace(".", "/") + "/") for name in descriptors):
            raise ValueError("Compiled DEX contains the other icon pack's namespace.")
    return len(descriptors)


def _verify_apk(apk: Path, project: Path, prepared: dict, compiled_filter: str, badging: str,
                compiled_resources: str, compiled_manifest: str, compiled_dex: str,
                inspected_dex: dict, configuration=None) -> dict:
    selected = _configuration(configuration)
    expected_png = {Path(row["path"]).name: row for row in prepared["files"]
                    if row["path"].startswith("res/drawable-nodpi/") and row["path"].endswith(".png")}
    if len(expected_png) != 300:
        raise ValueError("The prepared icon pack must contain 300 original selected-appearance PNGs.")
    for row in prepared["files"]:
        if _identity(project / row["path"]) != {key: row[key] for key in ("bytes", "sha256")}:
            raise ValueError("Prepared project file changed: " + row["path"])
    expected_pairs = [(item.attrib["component"], item.attrib["drawable"])
                      for item in ET.parse(project / "assets/appfilter.xml").getroot().findall("item")]
    if _compiled_pairs(compiled_filter) != expected_pairs:
        raise ValueError("Compiled appfilter mappings differ from the generated source.")
    package = re.search(r"^package: name='([^']+)' versionCode='([^']*)' versionName='([^']*)'", badging, re.MULTILINE)
    if package is None or package.groups() != (selected.package, str(selected.version_code), selected.version):
        raise ValueError("Compiled APK package/version differs from the separate icon-pack identity.")
    if any(line.startswith("uses-permission") for line in badging.splitlines()):
        raise ValueError("The APK unexpectedly requests a permission.")
    if "minSdkVersion:'26'" not in badging or "targetSdkVersion:'36'" not in badging:
        raise ValueError("Compiled APK API requirements differ from this build.")
    versions = _compiled_version_label(compiled_resources, selected)
    if re.findall(r"^application-label:'([^']*)'$", badging, re.MULTILINE) != [selected.label]:
        raise ValueError("Compiled APK application label differs from the selected pack.")
    launchable = re.findall(r"^launchable-activity: name='([^']*)'", badging, re.MULTILINE)
    if launchable != [selected.package + ".IconPackActivity"]:
        raise ValueError("Compiled APK launchable Activity differs from the selected pack.")
    blocks = _compiled_appearance(compiled_resources, selected)
    query_count = _compiled_manifest_identity(compiled_manifest, project, selected, blocks)
    classes = _compiled_activity_class(compiled_dex, selected)
    assets = _tree_files(project / "assets")
    with ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
            raise ValueError("The APK contains duplicate members.")
        if {name for name in names if re.fullmatch(r"classes[0-9]*\.dex", name)} != {"classes.dex"}:
            raise ValueError("The APK must contain exactly one DEX program.")
        for name in names:
            if name.startswith("/") or "\\" in name or ":" in name or ".." in name.split("/"):
                raise ValueError("The APK contains an unsafe member name.")
        actual_png = {}
        for name in names:
            if re.fullmatch(r"res/drawable(?:-[^/]+)?/co_[a-z0-9_]+\.png", name):
                base = Path(name).name
                if base in actual_png:
                    raise ValueError("The APK contains multiple variants of one icon.")
                actual_png[base] = name
        if set(actual_png) != set(expected_png):
            raise ValueError("The APK drawable inventory differs from the prepared artwork.")
        for base, expected in expected_png.items():
            info = archive.getinfo(actual_png[base])
            if info.file_size != expected["bytes"] or info.file_size > 2 * 1024 * 1024:
                raise ValueError("Unexpected APK PNG size: " + base)
            raw = archive.read(info)
            if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
                raise ValueError("AAPT2 changed an accepted PNG byte: " + base)
        for path in assets:
            info = archive.getinfo("assets/" + path.relative_to(project / "assets").as_posix())
            expected = _identity(path)
            if info.file_size != expected["bytes"] or hashlib.sha256(archive.read(info)).hexdigest() != expected["sha256"]:
                raise ValueError("APK assets differ from the prepared project: " + path.name)
        if {name for name in names if name.startswith("assets/")} != {
                "assets/" + path.relative_to(project / "assets").as_posix() for path in assets}:
            raise ValueError("APK asset inventory differs from the prepared project.")
        if "classes.dex" not in names:
            raise ValueError("The APK has no DEX program.")
        dex = archive.getinfo("classes.dex")
        if dex.file_size > 8 * 1024 * 1024 or {"bytes": dex.file_size, "sha256": hashlib.sha256(archive.read(dex)).hexdigest()} != inspected_dex:
            raise ValueError("Final APK DEX differs from the class-definition readback input.")
        if "classes.dex" not in names or not archive.read("classes.dex").startswith(b"dex\n"):
            raise ValueError("The APK has no DEX program.")
    return {"drawables_byte_exact": 300, "assets_byte_exact": len(assets),
            "compiled_component_mappings": len(expected_pairs), "compiled_package_queries": query_count,
            "application_label": selected.label, "activity": selected.package + ".IconPackActivity",
            "DEX_class_definitions": classes, "appearance": selected.appearance,
            "displayed_versions": versions, "permissions": []}


def _run(argv: list[str], output: Path, name: str, report: dict, environment: dict) -> str:
    log = output / (name + ".log")
    safe_argv = list(argv)
    if "--ks" in safe_argv:
        safe_argv[safe_argv.index("--ks") + 1] = "<external-keystore>"
    command = {"name": name, "argv": safe_argv, "status": "running"}
    report["commands"].append(command)
    receipt = output / "build.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        # A real file retains compiler output even if this wrapper is interrupted.
        with log.open("xb") as diagnostic:
            completed = subprocess.run(argv, cwd=output, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=diagnostic, stderr=subprocess.STDOUT, timeout=180,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        command.update(returncode=completed.returncode, status="passed" if completed.returncode == 0 else "failed")
        if completed.returncode:
            raise ValueError("Build command failed. Inspect " + log.name)
        if log.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Compiler diagnostics exceeded the bounded readback limit. Log retained.")
        return log.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as error:
        command.update(status="timeout", error="180-second command timeout. Partial outputs are preserved.")
        raise ValueError("Build command timed out. Inspect " + log.name) from error
    finally:
        if log.exists():
            command["log"] = {"path": log.name, **_identity(log)}
        receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png-dir", type=Path, required=True, help="Qualified current artwork PNG export directory")
    parser.add_argument("--appearance", choices=("Obscur", "Clair"), default="Obscur", help="Closed package/artwork variant; default preserves Obscur")
    parser.add_argument("--components", type=Path, default=ROOT / "android/iconpack/components.json")
    parser.add_argument("--sdk", type=Path, required=True, help="Explicit Android SDK root with API36 and Build Tools36.1.0")
    parser.add_argument("--java-bin", type=Path, required=True, help="Full JDK17 bin directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh build directory outside the repository")
    parser.add_argument("--keystore", type=Path, help="Existing private Android keystore outside source; absent means unsigned")
    parser.add_argument("--ks-pass-env", help="Name of an existing environment variable for apksigner; never a password argument")
    options = parser.parse_args(argv)
    png, components, sdk, java_bin, output = [_absolute(path) for path in
        (options.png_dir, options.components, options.sdk, options.java_bin, options.output_dir)]
    try:
        _validate_output(output, [png, sdk, java_bin.parent])
        if bool(options.keystore) != bool(options.ks_pass_env):
            raise ValueError("Signing requires both --keystore and --ks-pass-env. Omit both for an unsigned build.")
        key = None
        if options.keystore:
            key = _ordinary(_absolute(options.keystore))
            if not key.is_file() or key.is_relative_to(ROOT):
                raise ValueError("Use an existing Android keystore outside the repository.")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", options.ks_pass_env) or options.ks_pass_env not in os.environ:
                raise ValueError("--ks-pass-env must name an existing environment variable.")
        sys.path.insert(0, str(ROOT))
        from themeforge import android_iconpack
        selected = _configuration(android_iconpack.configuration(options.appearance))
        static = ROOT / "android/app"
        _validate_source_identity(static, android_iconpack.VERSION, android_iconpack.ARTWORK_VERSION)
        bt = sdk / "build-tools" / BUILD_TOOLS
        executable = ".exe" if os.name == "nt" else ""
        tools = {"java": java_bin / ("java" + executable), "javac": java_bin / ("javac" + executable),
                 "aapt2": bt / ("aapt2" + executable), "zipalign": bt / ("zipalign" + executable),
                 "dexdump": bt / ("dexdump" + executable),
                 "d8": bt / "lib/d8.jar", "apksigner": bt / "lib/apksigner.jar",
                 "android_jar": sdk / "platforms/android-36/android.jar"}
        inputs = _build_inputs(static, components, png, tools)
        identities = {str(path): _identity(path) for path in inputs}
    except (OSError, ValueError) as error:
        parser.error(str(error))
    output.mkdir(parents=True, exist_ok=False)
    receipt = output / "build.json"
    report = {"version": selected.version, "version_code": selected.version_code, "package": selected.package,
              "appearance": selected.appearance, "application_label": selected.label, "artwork_version": ARTWORK_VERSION,
              "status": "running", "signing_requested": key is not None,
              "signed": False, "signature_verified": False,
              "scope": "Local APK build and byte/format verification only; no installation, launcher or phone acceptance",
              "inputs": identities, "commands": []}
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        project = output / "project"
        prepared = android_iconpack.prepare_iconpack(png, components, project, appearance=selected.appearance)
        if (prepared.get("version"), prepared.get("artwork_version"), prepared.get("appearance"),
                prepared.get("application_id"), prepared.get("app_label"), prepared.get("version_code")) != (
                selected.version, ARTWORK_VERSION, selected.appearance, selected.package, selected.label, selected.version_code) or prepared.get("counts", {}).get("drawables") != 300:
            raise ValueError("Unexpected prepared icon-pack identity or inventory.")
        _copy_static(static, project)
        _configure_project(project, selected)
        _validate_source_identity(project, selected.version, android_iconpack.ARTWORK_VERSION, selected)
        queries = _write_queries(project, selected)
        if len(queries) != prepared["counts"]["package_hints"]:
            raise ValueError("Generated query count differs from the prepared public catalog.")
        report["preparation"] = prepared
        report["package_queries"] = queries
        project_inputs = {str(path.relative_to(project)): _identity(path) for path in _tree_files(project)}
        report["project_inputs"] = project_inputs
        temp = output / "temp"
        temp.mkdir()
        environment = os.environ.copy()
        for name in ("_JAVA_OPTIONS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "JDK_JAVAC_OPTIONS", "CLASSPATH"):
            environment.pop(name, None)
        environment.update(TEMP=str(temp), TMP=str(temp), JAVA_HOME=str(java_bin.parent))
        java = [str(tools["java"]), "-Xmx256m", "-XX:ActiveProcessorCount=1", "-XX:-UsePerfData", "-Djava.awt.headless=true"]
        run = lambda name, command: _run(command, output, name, report, environment)
        resources = output / "compiled-resources.zip"
        run("01-aapt2-compile", [str(tools["aapt2"]), "compile", "--no-crunch", "--dir", str(project / "res"), "-o", str(resources)])
        generated = output / "generated"
        generated.mkdir()
        resource_apk = output / "resources-unsigned.apk"
        run("02-aapt2-link", [str(tools["aapt2"]), "link", "-o", str(resource_apk), "-I", str(tools["android_jar"]),
            "--manifest", str(project / "AndroidManifest.xml"), "--java", str(generated), "-A", str(project / "assets"),
            "--min-sdk-version", str(MIN_API), "--target-sdk-version", str(API), "--version-code", str(selected.version_code), "--version-name", selected.version, str(resources)])
        classes = output / "classes"
        classes.mkdir()
        sources = sorted([path for path in _tree_files(project) + _tree_files(generated) if path.suffix == ".java"])
        if not sources:
            raise ValueError("No static Activity or generated Java resources were found.")
        run("03-javac", [str(tools["javac"]), "-J-Xmx256m", "-J-XX:ActiveProcessorCount=1", "-J-XX:-UsePerfData",
            "-J-Djava.awt.headless=true", "-encoding", "UTF-8", "-proc:none", "-source", "8", "-target", "8",
            "-bootclasspath", str(tools["android_jar"]), "-classpath", str(tools["android_jar"]), "-d", str(classes), *map(str, sources)])
        class_files = [path for path in _tree_files(classes) if path.suffix == ".class"]
        if not class_files:
            raise ValueError("Javac returned without class files.")
        dex = output / "dex"
        dex.mkdir()
        run("04-d8", java + ["-cp", str(tools["d8"]), "com.android.tools.r8.D8", "--release", "--thread-count", "1",
            "--min-api", str(MIN_API), "--lib", str(tools["android_jar"]), "--output", str(dex), *map(str, class_files)])
        if {path.name for path in _tree_files(dex)} != {"classes.dex"}:
            raise ValueError("This small icon pack must produce exactly one DEX file.")
        unsigned = output / "assembled-unsigned.apk"
        with ZipFile(resource_apk) as source, ZipFile(unsigned, "x", compression=ZIP_DEFLATED, compresslevel=9) as target:
            names = source.namelist()
            if len(names) != len(set(names)) or "classes.dex" in names:
                raise ValueError("Resource APK contains duplicate members or unexpected DEX.")
            for info in source.infolist():
                target.writestr(info, source.read(info))
            info = ZipInfo("classes.dex", (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, (dex / "classes.dex").read_bytes())
        stem = ("Clair-Icons-" if selected.appearance == "Clair" else "Clair-Obscur-Icons-") + selected.version
        aligned = output / (stem + "-unsigned.apk")
        run("05-zipalign", [str(tools["zipalign"]), "-P", "16", "4", str(unsigned), str(aligned)])
        final = aligned
        if key is not None:
            final = output / (stem + ".apk")
            run("06-apksigner-sign", java + ["-jar", str(tools["apksigner"]), "sign", "--ks", str(key),
                "--ks-pass", "env:" + options.ks_pass_env, "--out", str(final), str(aligned)])
            run("07-apksigner-verify", java + ["-jar", str(tools["apksigner"]), "verify", "--verbose", "--print-certs", str(final)])
            report.update(signed=True, signature_verified=True)
        run("08-zipalign-check", [str(tools["zipalign"]), "-c", "-P", "16", "4", str(final)])
        final_identity = _identity(final)
        tree = run("09-appfilter-readback", [str(tools["aapt2"]), "dump", "xmltree", str(final), "--file", "res/xml/appfilter.xml"])
        badging = run("10-package-readback", [str(tools["aapt2"]), "dump", "badging", str(final)])
        resource_dump = run("11-resource-readback", [str(tools["aapt2"]), "dump", "resources", str(final)])
        manifest_dump = run("12-manifest-readback", [str(tools["aapt2"]), "dump", "xmltree", str(final), "--file", "AndroidManifest.xml"])
        consumer_dex = output / "final-classes.dex"
        with ZipFile(final) as archive:
            info = archive.getinfo("classes.dex")
            if info.file_size > 8 * 1024 * 1024:
                raise ValueError("Final APK DEX exceeds the bounded class readback input.")
            with consumer_dex.open("xb") as stream:
                stream.write(archive.read(info))
        dex_identity = _identity(consumer_dex)
        dex_dump = run("13-dex-class-readback", [str(tools["dexdump"]), "-f", str(consumer_dex)])
        if _identity(consumer_dex) != dex_identity:
            raise ValueError("Final DEX readback input changed.")
        report["APK_checks"] = _verify_apk(final, project, prepared, tree, badging, resource_dump,
                                          manifest_dump, dex_dump, dex_identity, selected)
        if _identity(final) != final_identity:
            raise ValueError("Final APK changed during compiled readback.")
        _verify_input_identities(inputs, identities)
        if {str(path.relative_to(project)): _identity(path) for path in _tree_files(project)} != project_inputs:
            raise ValueError("Prepared build project changed. Preserve this build as unqualified.")
        report.update(status="built and verified signed APK" if key is not None else "built and verified unsigned APK; not installable until signed",
                      APK={"name": final.name, **_identity(final)}, no_installation_or_native_acceptance=True)
        code = 0
    except KeyboardInterrupt:
        report.update(status="interrupted; partial outputs retained", error="Build interrupted.")
        code = 130
    except Exception as error:
        report.update(status="failed; partial outputs retained", error_type=type(error).__name__, error=str(error))
        code = 1
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"] + ". Evidence: " + str(receipt))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
