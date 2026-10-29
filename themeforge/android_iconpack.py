"""Prepare a selected icon-pack appearance from the qualified paired PNG export."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
from types import MappingProxyType
import xml.etree.ElementTree as ET
import zlib

from .icons import ROOT, _read_tree, _safe_output, load_icon_tokens, render_icons


VERSION = "0.1.15"
ARTWORK_VERSION = "0.31.0"
APPEARANCE = "Obscur"
COMPONENTS = ROOT / "android/iconpack/components.json"


@dataclass(frozen=True)
class IconPackConfiguration:
    appearance: str
    package: str
    label: str
    version: str
    version_code: int


CONFIGURATIONS = MappingProxyType({
    "Obscur": IconPackConfiguration("Obscur", "io.github.t92t1914.obscuricons",
                                     "Obscur Icons", VERSION, 16),
    "Clair": IconPackConfiguration("Clair", "io.github.t92t1914.clairicons",
                                    "Clair Icons", "0.1.4", 5),
})


def configuration(appearance: str = APPEARANCE) -> IconPackConfiguration:
    """Select one supported identity, never an arbitrary package or version."""
    if type(appearance) is not str or appearance not in CONFIGURATIONS:
        raise ValueError("Unsupported icon-pack appearance; select Clair or Obscur")
    return CONFIGURATIONS[appearance]

# Exact export identity; decoded pixel and visual qualification are separate checks.
PNG_MANIFEST_SHA256 = "0a42224b3c9608db506693bd0a6c01f26ee2ee78ebcd2f3eeee54cf5540f4931"
COMPONENT_SOURCE = {
    "repository": "LawnchairLauncher/lawnicons",
    "revision": "c85fc8fb825228b021317f83c0a1a9f00b1c889d",
    "path": "app/assets/appfilter.xml",
    "sha256": "9b03e294aff3890e4e9b1e3d591c46c58b2be7d4ca140c5d56363494e127ffd6",
    "license": "Apache-2.0",
    "license_path": "LICENSE",
    "license_sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "url": "https://github.com/LawnchairLauncher/lawnicons/blob/"
           "c85fc8fb825228b021317f83c0a1a9f00b1c889d/app/assets/appfilter.xml",
}


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _document(payload: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate icon-pack JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite icon-pack JSON value")

    try:
        result = json.loads(payload.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError("Invalid icon-pack JSON document") from error
    if not isinstance(result, dict):
        raise ValueError("Expected an icon-pack JSON object")
    return result


def _plain(value: Path, *, missing: bool = False) -> Path:
    value = Path(value)
    if ".." in value.parts or str(value).startswith("\\\\"):
        raise ValueError("Icon-pack paths must be ordinary local paths without traversal")
    path = Path(os.path.abspath(value))
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise ValueError("Missing icon-pack input") from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Icon-pack paths must not contain links or reparse points")
        if entry != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError("Icon-pack path ancestor is not an ordinary directory")
    return path


def _read(path: Path, limit: int = 4 * 1024 * 1024) -> bytes:
    path = _plain(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError("Icon-pack input must be a bounded regular file")
    payload = path.read_bytes()
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if len(payload) != before.st_size or any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError("Icon-pack input changed while reading")
    return payload


def _png(payload: bytes, size: int) -> None:
    """Check the encoded container. Pixel qualification belongs to its pinned export."""
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Expected a qualified PNG image")
    offset, kinds = 8, []
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise ValueError("Truncated PNG chunk")
        length, = struct.unpack_from(">I", payload, offset)
        end = offset + length + 12
        if end > len(payload):
            raise ValueError("Truncated PNG chunk")
        kind, data = payload[offset + 4:offset + 8], payload[offset + 8:end - 4]
        checksum, = struct.unpack_from(">I", payload, end - 4)
        if zlib.crc32(kind + data) & 0xffffffff != checksum:
            raise ValueError("PNG chunk checksum differs")
        if not kinds:
            if kind != b"IHDR" or length != 13 or struct.unpack(">IIBBBBB", data) != (size, size, 8, 6, 0, 0, 0):
                raise ValueError("Expected the qualified size and 8-bit RGBA PNG format")
        elif kind == b"IHDR":
            raise ValueError("Repeated PNG header")
        kinds.append(kind)
        offset = end
        if kind == b"IEND":
            if length or offset != len(payload):
                raise ValueError("Unexpected data after PNG end")
            break
    if not kinds or kinds[-1] != b"IEND" or b"IDAT" not in kinds:
        raise ValueError("Incomplete PNG image")


def drawable_name(identifier: str) -> str:
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", identifier):
        raise ValueError("Invalid icon identifier")
    return "co_" + identifier.replace("-", "_")


def _export(root: Path, selected_appearance: str = APPEARANCE) -> tuple[dict, dict[str, bytes], dict[Path, str]]:
    configuration(selected_appearance)
    root = _plain(root)
    raw = _read(root / "manifest.json")
    if _digest(raw) != PNG_MANIFEST_SHA256:
        raise ValueError("PNG export differs from the qualified current artwork manifest")
    document = _document(raw)
    canonical = render_icons(load_icon_tokens(ARTWORK_VERSION), version=ARTWORK_VERSION)
    svg = _document(canonical["manifest.json"])
    if (document.get("schema_version") != 1 or document.get("version") != ARTWORK_VERSION
            or document.get("generator") != "clair-obscur-png-export"
            or document.get("exporter_version") != "0.11.0"
            or document.get("token_version") != "1.0.0"
            or document.get("tokens_file") != "tokens-monochrome.json"
            or document.get("palette_variant") != "monochrome"
            or document.get("source_manifest_sha256") != _digest(canonical["manifest.json"])):
        raise ValueError("PNG export has the wrong artwork identity")
    for key in ("catalog", "functions", "catalog_date", "catalog_scope"):
        if document.get(key) != svg[key]:
            raise ValueError("PNG catalog differs from current SVG identity")
    if len(svg["functions"]) != 300 or len(set(svg["functions"])) != 300:
        raise ValueError("Expected all 300 current icon identifiers")
    if document.get("appearances") != ["Clair", "Obscur"] or document.get("sizes") != [512, 1024]:
        raise ValueError("PNG export is missing an appearance or size")
    guards = {root / "manifest.json": _digest(raw)}
    for key, relative in (("tokens_sha256", "tokens-monochrome.json"),
                          ("svg_generator_sha256", "themeforge/icons.py"),
                          ("svg_craft_sha256", "themeforge/icon_craft.py"),
                          ("svg_catalog_sha256", "themeforge/icon_apps.py"),
                          ("exporter_sha256", "tools/export-icons.mjs")):
        path = ROOT / relative
        digest = _digest(_read(path))
        if document.get(key) != digest:
            raise ValueError("PNG export source identity differs")
        guards[path] = digest
    license_payload = _read(root / "LICENSE")
    if document.get("license") != {"path": "LICENSE", "bytes": len(license_payload), "sha256": _digest(license_payload)}:
        raise ValueError("PNG export license identity differs")
    if license_payload != _read(ROOT / "LICENSE"):
        raise ValueError("PNG export license differs from the project license")
    guards[root / "LICENSE"] = _digest(license_payload)
    guards[ROOT / "LICENSE"] = _digest(license_payload)
    expected = {f"{appearance}/{size}/{identifier}.png"
                for appearance in ("Clair", "Obscur") for size in (512, 1024)
                for identifier in svg["functions"]}
    records = document.get("files")
    if not isinstance(records, list) or len(records) != 1200:
        raise ValueError("Expected the complete 1200-file PNG export")
    svgs = {row["path"]: row["sha256"] for row in svg["files"]}
    selected, observed = {}, set()
    for row in records:
        if (not isinstance(row, dict) or not isinstance(row.get("path"), str)
                or row["path"] not in expected or row["path"] in observed):
            raise ValueError("Unexpected, repeated or unsafe PNG path")
        relative = row["path"]
        appearance, size_text, filename = relative.split("/")
        identifier, size = filename[:-4], int(size_text)
        if (row.get("appearance") != appearance or row.get("function") != identifier
                or row.get("width") != size or row.get("height") != size
                or row.get("source_svg_sha256") != svgs[f"{appearance}/{identifier}.svg"]):
            raise ValueError("PNG file identity differs from its canonical SVG")
        path = root / relative
        payload = _read(path)
        if len(payload) != row.get("bytes") or _digest(payload) != row.get("sha256"):
            raise ValueError("PNG file bytes differ from their qualified manifest")
        _png(payload, size)
        guards[path] = row["sha256"]
        observed.add(relative)
        if appearance == selected_appearance and size == 512:
            selected[identifier] = payload
    if observed != expected:
        raise ValueError("PNG export is incomplete")
    actual, directories = set(), set()
    for parent, children, names in os.walk(root, followlinks=False):
        for name in children:
            path = _plain(Path(parent) / name)
            if not path.is_dir():
                raise ValueError("Unexpected PNG export directory")
            directories.add(path.relative_to(root).as_posix())
        for name in names:
            path = _plain(Path(parent) / name)
            if not path.is_file():
                raise ValueError("Unexpected PNG export entry")
            actual.add(path.relative_to(root).as_posix())
    if actual != expected | {"manifest.json", "LICENSE"} or directories != {
            "Clair", "Obscur", "Clair/512", "Clair/1024", "Obscur/512", "Obscur/1024"}:
        raise ValueError("PNG export contains missing or extra entries")
    selected["LICENSE"] = license_payload
    return document, selected, guards


def _components(path: Path, catalog: list[dict]) -> tuple[dict, bytes, dict[Path, str]]:
    path, canonical_path = _plain(path), _plain(COMPONENTS)
    payload, canonical = _read(path), _read(COMPONENTS)
    if path == canonical_path and payload != canonical:
        raise ValueError("Component input changed during admission")
    table = _document(payload)
    if table != _document(canonical):
        raise ValueError("Component table differs from the reviewed canonical table")
    if (set(table) != {"schema_version", "source", "mappings", "generic_packages"}
            or type(table["schema_version"]) is not int or table["schema_version"] != 1
            or table["source"] != COMPONENT_SOURCE):
        raise ValueError("Invalid component source or table schema")
    by_id = {row["id"]: row for row in catalog}
    generics = table["generic_packages"]
    package_pattern = r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+"
    if not isinstance(generics, dict):
        raise ValueError("Expected verified generic package lists")
    for identifier, packages in generics.items():
        if (identifier not in by_id or by_id[identifier]["kind"] != "function"
                or not isinstance(packages, list) or not packages
                or not all(isinstance(package, str) and re.fullmatch(package_pattern, package) for package in packages)
                or len(packages) != len(set(packages))):
            raise ValueError("Invalid verified generic package list")
    mappings = table["mappings"]
    if not isinstance(mappings, list) or not 1 <= len(mappings) <= 4096:
        raise ValueError("Expected bounded exact component mappings")
    seen = set()
    required = {"icon_id", "android_package", "activity", "component"}
    upstream_evidence = {"source_lines", "source_components", "source_types"}
    optional = upstream_evidence | {"source_kind", "observed_on"}
    for row in mappings:
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - optional:
            raise ValueError("Invalid exact component mapping schema")
        if "source_kind" in row:
            observed_on = row.get("observed_on")
            if (row["source_kind"] != "observed-launcher"
                    or not isinstance(observed_on, str)
                    or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", observed_on)):
                raise ValueError("Invalid observed launcher source metadata")
            try:
                date.fromisoformat(observed_on)
            except ValueError as error:
                raise ValueError("Invalid observed launcher observation date") from error
            if set(row) & upstream_evidence:
                raise ValueError("Observed launcher mappings must not claim upstream source evidence")
        elif "observed_on" in row:
            raise ValueError("Observation date requires an observed launcher source")
        identifier, package, activity = row["icon_id"], row["android_package"], row["activity"]
        if not isinstance(identifier, str) or identifier not in by_id:
            raise ValueError("Component mapping refers to a missing drawable")
        if not isinstance(package, str) or not re.fullmatch(package_pattern, package):
            raise ValueError("Invalid component package")
        # Activity aliases can contain '-' and need not share the package namespace.
        # Reviewed upstream declarations and launcher observations supply exact names.
        if not isinstance(activity, str) or not re.fullmatch(r"[A-Za-z0-9_$][A-Za-z0-9_.$-]*", activity):
            raise ValueError("Expected an exact normalized activity name")
        if row["component"] != f"ComponentInfo{{{package}/{activity}}}":
            raise ValueError("ComponentInfo must match its exact package and activity")
        allowed = ([by_id[identifier]["android_package"]] if by_id[identifier]["kind"] == "app"
                   else generics.get(identifier, []))
        if package not in allowed:
            raise ValueError("Component package differs from its named app or verified function")
        if row["component"] in seen:
            raise ValueError("Repeated or conflicting component mapping")
        if ("source_lines" in row and (not isinstance(row["source_lines"], list)
                or not row["source_lines"] or not all(type(line) is int and line > 0 for line in row["source_lines"]))):
            raise ValueError("Invalid component source line evidence")
        if ("source_components" in row and (not isinstance(row["source_components"], list)
                or not row["source_components"] or not all(isinstance(item, str) and len(item) <= 1024
                                                         for item in row["source_components"]))):
            raise ValueError("Invalid component source identity evidence")
        if ("source_types" in row and (not isinstance(row["source_types"], list)
                or not row["source_types"] or any(item not in ("item", "calendar") for item in row["source_types"]))):
            raise ValueError("Invalid component source entry type")
        seen.add(row["component"])
    return table, payload, {path: _digest(payload), canonical_path: _digest(canonical)}


def _xml(document: ET.Element) -> bytes:
    ET.indent(document, space="  ")
    return ET.tostring(document, encoding="utf-8", xml_declaration=True) + b"\n"


def prepare_iconpack(png_export: Path, components: Path, output: Path, *,
                     appearance: str = APPEARANCE) -> dict:
    """Create new APK source resources. Do not build, sign, install or launch anything."""
    selected = configuration(appearance)
    output = _plain(output, missing=True)
    _safe_output(output)
    if (output == ROOT or output in ROOT.parents or output == ROOT / "outputs"
            or ROOT / "outputs" in output.parents):
        raise ValueError("Icon-pack output must stay outside managed output and source roots")
    if output.exists():
        raise ValueError("Icon-pack preparation requires a new output directory; existing entries are preserved")
    source, component_path = _plain(png_export), _plain(components)
    if output == source or output in source.parents or source in output.parents:
        raise ValueError("Icon-pack output and PNG input trees must be separate")
    document, images, guards = _export(source, selected.appearance)
    table, component_bytes, table_guards = _components(component_path, document["catalog"])
    guards.update(table_guards)
    names = {identifier: drawable_name(identifier) for identifier in document["functions"]}
    if len(set(names.values())) != 300:
        raise ValueError("Android drawable names collide")
    files = {f"res/drawable-nodpi/{names[identifier]}.png": images[identifier]
             for identifier in document["functions"]}
    appfilter = ET.Element("resources")
    for row in sorted(table["mappings"], key=lambda item: item["component"]):
        ET.SubElement(appfilter, "item", {"component": row["component"], "drawable": names[row["icon_id"]]})
    files["res/xml/appfilter.xml"] = files["assets/appfilter.xml"] = _xml(appfilter)
    index = ET.Element("resources")
    ET.SubElement(index, "category", {"title": selected.appearance})
    for identifier in document["functions"]:
        ET.SubElement(index, "item", {"drawable": names[identifier]})
    files["res/xml/drawable.xml"] = _xml(index)
    packages, seen = [], set()
    for row in document["catalog"]:
        if row["kind"] == "app":
            package = row["android_package"]
            packages.append({"package": package, "label": row["label"], "id": row["id"]})
            seen.add(package)
    if len(packages) != len(seen) or len(packages) != 276:
        raise ValueError("Expected 276 distinct named package hints")
    for row in document["catalog"]:
        for package in table["generic_packages"].get(row["id"], []):
            if package not in seen:
                packages.append({"package": package, "label": row["label"], "id": row["id"]})
                seen.add(package)
    files["assets/catalog.json"] = _json_bytes({"schema_version": 1, "artwork_version": ARTWORK_VERSION,
                                              "pack_version": selected.version, "packages": packages})
    files["assets/icon-artwork-LICENSE.txt"] = images["LICENSE"]
    manifest = {"schema_version": 1, "generator": "themeforge.android_iconpack", "version": selected.version,
        "appearance": selected.appearance, "artwork_version": ARTWORK_VERSION,
        "application_id": selected.package, "app_label": selected.label,
        "version_code": selected.version_code,
        "source": {"png_manifest_sha256": _digest(_read(source / "manifest.json")),
                   "svg_manifest_sha256": document["source_manifest_sha256"],
                   "components_sha256": _digest(component_bytes), "component_source": table["source"]},
        "counts": {"drawables": 300, "component_mappings": len(table["mappings"]),
                   "mapped_icons": len({row["icon_id"] for row in table["mappings"]}),
                   "upstream_component_mappings": sum("source_kind" not in row for row in table["mappings"]),
                   "observed_launcher_mappings": sum(row.get("source_kind") == "observed-launcher"
                                                      for row in table["mappings"]),
                   "named_package_hints": 276, "package_hints": len(packages)},
        "files": [{"path": name, "bytes": len(payload), "sha256": _digest(payload)}
                  for name, payload in sorted(files.items())],
        "scope": f"{selected.appearance} APK source resources and exact reviewed activity mappings only. "
                 "No APK build, signing, installation, launcher/Theme Park or phone acceptance."}

    def unchanged():
        if any(_digest(_read(path)) != digest for path, digest in guards.items()):
            raise ValueError("Icon-pack input changed during preparation")

    unchanged()
    _plain(output, missing=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    _plain(output, missing=True)
    output.mkdir(exist_ok=False)
    # Exclusive writes retain a partial owned tree after interruption, never repair it.
    generated = {**files, "iconpack-manifest.json": _json_bytes(manifest)}
    for name, payload in generated.items():
        target = output / name
        _plain(target.parent, missing=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        _plain(target, missing=True)
        with target.open("xb") as stream:
            stream.write(payload)
    unchanged()
    actual, directories = _read_tree(output)
    if actual != generated or directories != {"res", "res/drawable-nodpi", "res/xml", "assets"}:
        raise ValueError("Prepared icon-pack resources changed or contain extra entries")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png-export", type=Path, required=True)
    parser.add_argument("--components", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--appearance", choices=tuple(CONFIGURATIONS), default=APPEARANCE)
    options = parser.parse_args(argv)
    try:
        manifest = prepare_iconpack(options.png_export, options.components, options.output,
                                    appearance=options.appearance)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Android icon-pack preparation: {error}\n")
    print(f'Prepared {manifest["counts"]["drawables"]} {manifest["appearance"]} drawables with '
          f'{manifest["counts"]["component_mappings"]} exact component mappings; native acceptance unverified')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
