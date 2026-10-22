"""Build the separate Obscur icon pack with an explicitly selected Android SDK."""

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
VERSION = "0.1.4"
VERSION_CODE = 5
ARTWORK_VERSION = "0.21.0"
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


def _write_queries(project: Path) -> list[str]:
    catalog_path = project / "assets/catalog.json"
    _identity(catalog_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if set(catalog) != {"schema_version", "artwork_version", "pack_version", "packages"}:
        raise ValueError("The public package catalog has unexpected fields.")
    if (catalog["schema_version"], catalog["artwork_version"], catalog["pack_version"]) != (1, ARTWORK_VERSION, VERSION):
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
    manifest = project / "AndroidManifest.xml"
    _identity(manifest)
    tree = ET.parse(manifest)
    root = tree.getroot()
    if root.tag != "manifest" or root.attrib.get("package") != PACKAGE:
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


def _verify_apk(apk: Path, project: Path, prepared: dict, compiled_filter: str, badging: str) -> dict:
    expected_png = {Path(row["path"]).name: row for row in prepared["files"]
                    if row["path"].startswith("res/drawable-nodpi/") and row["path"].endswith(".png")}
    if len(expected_png) != 292:
        raise ValueError("The prepared icon pack must contain 292 original Obscur PNGs.")
    expected_pairs = [(item.attrib["component"], item.attrib["drawable"])
                      for item in ET.parse(project / "assets/appfilter.xml").getroot().findall("item")]
    if sorted(_compiled_pairs(compiled_filter)) != sorted(expected_pairs):
        raise ValueError("Compiled appfilter mappings differ from the generated source.")
    package = re.search(r"^package: name='([^']+)' versionCode='([^']*)' versionName='([^']*)'", badging, re.MULTILINE)
    if package is None or package.groups() != (PACKAGE, str(VERSION_CODE), VERSION):
        raise ValueError("Compiled APK package/version differs from the separate icon-pack identity.")
    if any(line.startswith("uses-permission") for line in badging.splitlines()):
        raise ValueError("The APK unexpectedly requests a permission.")
    if "minSdkVersion:'26'" not in badging or "targetSdkVersion:'36'" not in badging:
        raise ValueError("Compiled APK API requirements differ from this build.")
    for row in prepared["files"]:
        if _identity(project / row["path"]) != {key: row[key] for key in ("bytes", "sha256")}:
            raise ValueError("Prepared project file changed: " + row["path"])
    assets = _tree_files(project / "assets")
    with ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
            raise ValueError("The APK contains duplicate members.")
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
        if "classes.dex" not in names or not archive.read("classes.dex").startswith(b"dex\n"):
            raise ValueError("The APK has no DEX program.")
    return {"drawables_byte_exact": 292, "assets_byte_exact": len(assets),
            "compiled_component_mappings": len(expected_pairs), "permissions": []}


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
    parser.add_argument("--png-dir", type=Path, required=True, help="Qualified 0.21 PNG export directory")
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
        bt = sdk / "build-tools" / BUILD_TOOLS
        executable = ".exe" if os.name == "nt" else ""
        tools = {"java": java_bin / ("java" + executable), "javac": java_bin / ("javac" + executable),
                 "aapt2": bt / ("aapt2" + executable), "zipalign": bt / ("zipalign" + executable),
                 "d8": bt / "lib/d8.jar", "apksigner": bt / "lib/apksigner.jar",
                 "android_jar": sdk / "platforms/android-36/android.jar"}
        static = ROOT / "android/app"
        source_files = _tree_files(static) + [Path(__file__).absolute(), ROOT / "themeforge/android_iconpack.py",
            ROOT / "themeforge/icons.py", ROOT / "themeforge/icon_apps.py", ROOT / "tokens-monochrome.json",
            components, ROOT / "android/iconpack/components.json", png / "manifest.json"]
        inputs = sorted(set(source_files + list(tools.values())))
        identities = {str(path): _identity(path) for path in inputs}
    except (OSError, ValueError) as error:
        parser.error(str(error))
    output.mkdir(parents=True, exist_ok=False)
    receipt = output / "build.json"
    report = {"version": VERSION, "package": PACKAGE, "status": "running", "signing_requested": key is not None,
              "signed": False, "signature_verified": False,
              "scope": "Local APK build and byte/format verification only; no installation, launcher or phone acceptance",
              "inputs": identities, "commands": []}
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        sys.path.insert(0, str(ROOT))
        from themeforge.android_iconpack import prepare_iconpack
        project = output / "project"
        prepared = prepare_iconpack(png, components, project)
        if (prepared.get("version"), prepared.get("artwork_version"), prepared.get("appearance")) != (VERSION, ARTWORK_VERSION, "Obscur") or prepared.get("counts", {}).get("drawables") != 292:
            raise ValueError("Unexpected prepared icon-pack identity or inventory.")
        _copy_static(static, project)
        queries = _write_queries(project)
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
            "--min-sdk-version", str(MIN_API), "--target-sdk-version", str(API), "--version-code", str(VERSION_CODE), "--version-name", VERSION, str(resources)])
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
        aligned = output / ("Clair-Obscur-Icons-" + VERSION + "-unsigned.apk")
        run("05-zipalign", [str(tools["zipalign"]), "-P", "16", "4", str(unsigned), str(aligned)])
        final = aligned
        if key is not None:
            final = output / ("Clair-Obscur-Icons-" + VERSION + ".apk")
            run("06-apksigner-sign", java + ["-jar", str(tools["apksigner"]), "sign", "--ks", str(key),
                "--ks-pass", "env:" + options.ks_pass_env, "--out", str(final), str(aligned)])
            run("07-apksigner-verify", java + ["-jar", str(tools["apksigner"]), "verify", "--verbose", "--print-certs", str(final)])
            report.update(signed=True, signature_verified=True)
        run("08-zipalign-check", [str(tools["zipalign"]), "-c", "-P", "16", "4", str(final)])
        tree = run("09-appfilter-readback", [str(tools["aapt2"]), "dump", "xmltree", str(final), "--file", "res/xml/appfilter.xml"])
        badging = run("10-package-readback", [str(tools["aapt2"]), "dump", "badging", str(final)])
        report["APK_checks"] = _verify_apk(final, project, prepared, tree, badging)
        if {str(path): _identity(path) for path in inputs} != identities:
            raise ValueError("Build source or SDK inputs changed. Preserve this build as unqualified.")
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
