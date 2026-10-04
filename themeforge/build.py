"""Reproducible, bounded release packaging using only the standard library."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

from .chrome import build_theme
from .equicord import render_theme
from .discord_clients import CLIENTS, render_client_theme
from .firefox import COLOR_TOKENS as FIREFOX_COLORS, theme_manifest as firefox_manifest
from .vivaldi import COLOR_TOKENS as VIVALDI_COLORS, theme_id as vivaldi_id, theme_settings as vivaldi_settings
from .opera_gx import package_icon as gx_icon, theme_manifest as gx_manifest
from .legal import license_comment, license_text
from .tokens import load


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OWNER = "clair-obscur-themeforge"
MANIFEST = "artifact-manifest.json"
CHECKSUMS = "SHA256SUMS"
SHA = re.compile(r"[0-9a-f]{64}\Z")
# The existing Chrome and Equicord release remains byte-identical at 0.1.1.
# New adapters have their own version until a deliberate family release.
PORTABILITY_VERSION = "0.2.0"
BROWSER_VERSION = "0.3.0"


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def _linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _safe_destination(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    if path == path.parent:
        raise ValueError("The output must not be a filesystem root")
    for ancestor in (path, *path.parents):
        if ancestor.exists() or ancestor.is_symlink():
            if _linked(ancestor):
                raise ValueError("Output paths must not contain symlinks or reparse points")
    if path.exists() and not path.is_dir():
        raise ValueError("The output exists and is not a directory")
    return path


def _inventory(root: Path) -> tuple[dict[str, bytes], list[Path]]:
    """Read only regular files, refusing links and other unexpected entries."""
    files: dict[str, bytes] = {}
    directories: list[Path] = []
    if _linked(root):
        raise ValueError("Output root is a link")
    pending = [root]
    while pending:
        directory = pending.pop()
        for entry in sorted(directory.iterdir()):
            if _linked(entry):
                raise ValueError("Output contains a link or reparse point")
            if entry.is_dir():
                directories.append(entry)
                pending.append(entry)
            elif entry.is_file():
                files[entry.relative_to(root).as_posix()] = entry.read_bytes()
            else:
                raise ValueError("Output contains a non-regular entry")
    return files, directories


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        raise ValueError("Artifact path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Artifact path must stay inside its output")
    return value


def _verify_owned(root: Path) -> dict[str, bytes]:
    """Reject foreign, edited or partial builds before replacing any output."""
    if not root.exists():
        return {}
    files, directories = _inventory(root)
    if not files and not directories:
        return {}
    if MANIFEST not in files or CHECKSUMS not in files:
        raise ValueError("Refusing an output tree without this builder's complete manifest")
    try:
        manifest = json.loads(files[MANIFEST])
        if manifest.get("generator") != OWNER or manifest.get("schema_version") != 1:
            raise ValueError("Output belongs to a different generator")
        records = manifest["files"]
        if not isinstance(records, list):
            raise ValueError("Artifact records must be a list")
        expected = {MANIFEST, CHECKSUMS}
        for record in records:
            name = _safe_relative(record["path"])
            if name in expected:
                raise ValueError("Duplicate or reserved artifact path")
            expected.add(name)
            digest = record["sha256"]
            if not isinstance(digest, str) or not SHA.fullmatch(digest):
                raise ValueError("Invalid artifact digest")
            if name not in files or _digest(files[name]) != digest or len(files[name]) != record["bytes"]:
                raise ValueError("An existing artifact was changed or is missing")
        if set(files) != expected:
            raise ValueError("Output contains unrelated files")
        expected_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
        if {p.relative_to(root).as_posix() for p in directories} != expected_dirs:
            raise ValueError("Output contains unrelated directories")
        checksummed = {name: payload for name, payload in files.items() if name != CHECKSUMS}
        if files[CHECKSUMS] != _checksum_bytes(checksummed):
            raise ValueError("Output checksum file does not match its artifacts")
    except (KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Existing output manifest is malformed") from error
    return files


def _checksum_bytes(files: dict[str, bytes]) -> bytes:
    return "".join(f"{_digest(files[name])}  {name}\n" for name in sorted(files)).encode("ascii")


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(_safe_relative(name), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, files[name])
    return buffer.getvalue()


def _review_payloads(files: dict[str, bytes]) -> None:
    """Enforce the pure-theme boundary before producing any release archive."""
    expected = {f"chrome/{name}/{file}" for name in ("clair", "obscur") for file in ("manifest.json", "icon128.png", "LICENSE.txt")}
    expected |= {f"equicord/{name}.theme.css" for name in ("Clair", "Obscur")}
    expected |= {f"firefox/{name}/{file}" for name in ("clair", "obscur") for file in ("manifest.json", "LICENSE.txt")}
    expected |= {f"{client}/{name}-{label}.theme.css" for client, label in CLIENTS.items() for name in ("Clair", "Obscur")}
    expected |= {f"vivaldi/{name}/settings.json" for name in ("clair", "obscur")}
    expected |= {"vivaldi/LICENSE.txt", "opera-gx/manifest.json", "opera-gx/icon512.png", "opera-gx/LICENSE.txt"}
    if set(files) != expected:
        raise ValueError("Generated payload contains missing or unexpected files")
    for path, payload in files.items():
        if path.endswith(".png"):
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Theme icon is not a PNG")
            if path == "opera-gx/icon512.png" and payload[8:24] != b"\x00\x00\x00\rIHDR\x00\x00\x02\x00\x00\x00\x02\x00":
                raise ValueError("GX package icon must declare 512 by 512 pixels")
            continue
        text = payload.decode("utf-8")
        if re.search(r"(?:file://|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\[A-Za-z])", text):
            raise ValueError("Generated text contains a machine-local path")
        if path.endswith(".css"):
            if re.search(r"@import\b|url\s*\(|https?://|javascript:|expression\s*\(", text, re.IGNORECASE):
                raise ValueError("CSS must not include remote resources or executable content")
            if license_comment() not in text:
                raise ValueError("CSS must retain the complete canonical license comment")
        elif path.endswith("/LICENSE.txt"):
            if text != license_text():
                raise ValueError("Theme package must retain the complete canonical license")
        elif path.startswith("vivaldi/"):
            settings = json.loads(text)
            if set(settings) != {"engineVersion", "id", "name", "version", *VIVALDI_COLORS}:
                raise ValueError("Vivaldi settings contain unexpected non-color fields")
            name = "Clair" if path == "vivaldi/clair/settings.json" else "Obscur"
            if (settings["name"] != name or settings["id"] != vivaldi_id(name)
                    or type(settings["engineVersion"]) is not int or settings["engineVersion"] != 1
                    or type(settings["version"]) is not int or settings["version"] != 1):
                raise ValueError("Vivaldi identity and integer export revisions are invalid")
            if any(not isinstance(settings[field], str) or not re.fullmatch(r"#[0-9a-f]{6}", settings[field])
                   for field in VIVALDI_COLORS):
                raise ValueError("Vivaldi colors must be literal six-digit hex values")
        elif path == "opera-gx/manifest.json":
            manifest = json.loads(text)
            if set(manifest) != {"manifest_version", "name", "version", "description", "developer", "icons", "mod"}:
                raise ValueError("GX package contains unexpected manifest capabilities")
            if (manifest["manifest_version"] != 3 or manifest["name"] != "Clair and Obscur"
                    or manifest["version"] != BROWSER_VERSION
                    or manifest["developer"] != {"name": "T92T1914"}
                    or manifest["icons"] != {"512": "icon512.png"}):
                raise ValueError("GX identity or packaged icon is invalid")
            mod = manifest["mod"]
            if (set(mod) != {"schema_version", "license", "payload"}
                    or mod["schema_version"] != 1 or mod["license"] != "LICENSE.txt"
                    or set(mod["payload"]) != {"theme"}):
                raise ValueError("GX payload must contain only local color hints")
            modes = mod["payload"]["theme"]
            if set(modes) != {"light", "dark"}:
                raise ValueError("GX requires both light and dark appearances")
            for colors in modes.values():
                if set(colors) != {"gx_accent", "gx_secondary_base"}:
                    raise ValueError("GX appearance contains unsupported hints")
                for hint in colors.values():
                    if (set(hint) != {"h", "s", "l"}
                            or any(type(hint[key]) is not int or not 0 <= hint[key] <= limit
                                   for key, limit in (("h", 359), ("s", 100), ("l", 100)))):
                        raise ValueError("GX HSL hints must be bounded integers")
        elif path.startswith("firefox/"):
            manifest = json.loads(text)
            if set(manifest) != {"manifest_version", "name", "version", "author", "description", "browser_specific_settings", "theme"}:
                raise ValueError("Native Firefox package contains unexpected manifest capabilities")
            if manifest["manifest_version"] != 2 or set(manifest["theme"]) != {"colors", "properties"}:
                raise ValueError("Native Firefox package is not a color-only static theme")
            if set(manifest["theme"]["colors"]) != set(FIREFOX_COLORS):
                raise ValueError("Firefox color mapping is incomplete or unsupported")
            if any(not isinstance(value, str) or not re.fullmatch(r"#[0-9a-f]{6}", value)
                   for value in manifest["theme"]["colors"].values()):
                raise ValueError("Firefox colors must be literal six-digit hex values")
            name = manifest["name"]
            if name not in ("Clair", "Obscur"):
                raise ValueError("Firefox theme identity is invalid")
            mode = "light" if name == "Clair" else "dark"
            if manifest["theme"]["properties"] != {"color_scheme": mode, "content_color_scheme": "system"}:
                raise ValueError("Firefox must preserve manual theme and system content selection")
            if manifest["browser_specific_settings"] != {"gecko": {
                    "id": f"{name.lower()}@themes.t92t1914.github.io", "strict_min_version": "128.0"}}:
                raise ValueError("Firefox identity and minimum version are invalid")
        else:
            manifest = json.loads(text)
            if set(manifest) != {"manifest_version", "name", "version", "description", "icons", "theme"}:
                raise ValueError("Native Chrome package contains unexpected manifest capabilities")
            if manifest["manifest_version"] != 3 or set(manifest["theme"]) != {"colors"}:
                raise ValueError("Native Chrome package is not a color-only native theme")
            if manifest["icons"] != {"128": "icon128.png"}:
                raise ValueError("Chrome icon reference is not a packaged local asset")


def _generate(document: dict, stage: Path) -> dict:
    version = document["version"]
    for name in ("Clair", "Obscur"):
        build_theme(name, document["themes"][name], stage / "chrome", version)
        target = stage / "equicord" / f"{name}.theme.css"
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(render_theme(name, document["themes"][name], version).encode("utf-8"))
        native = stage / "firefox" / name.lower()
        native.mkdir(parents=True)
        (native / "manifest.json").write_bytes(_json_bytes(firefox_manifest(name, document["themes"][name], PORTABILITY_VERSION)))
        (native / "LICENSE.txt").write_text(license_text(), encoding="utf-8", newline="\n")
        native = stage / "vivaldi" / name.lower()
        native.mkdir(parents=True)
        (native / "settings.json").write_bytes(_json_bytes(vivaldi_settings(name, document["themes"][name])))
        for client, label in CLIENTS.items():
            target = stage / client / f"{name}-{label}.theme.css"
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(render_client_theme(client, name, document["themes"][name], PORTABILITY_VERSION).encode("utf-8"))
    # Vivaldi's documented color-only ZIP contains one JSON file. Its original
    # source grant remains alongside the unpacked settings and in the preview.
    (stage / "vivaldi" / "LICENSE.txt").write_text(license_text(), encoding="utf-8", newline="\n")
    native = stage / "opera-gx"
    native.mkdir()
    (native / "manifest.json").write_bytes(_json_bytes(gx_manifest(document["themes"], BROWSER_VERSION)))
    (native / "icon512.png").write_bytes(gx_icon(document["themes"]))
    (native / "LICENSE.txt").write_text(license_text(), encoding="utf-8", newline="\n")
    files, _ = _inventory(stage)
    _review_payloads(files)
    downloads = []
    for name in ("Clair", "Obscur"):
        native = {key.split("/", 2)[2]: data for key, data in files.items() if key.startswith(f"chrome/{name.lower()}/")}
        path = f"artifacts/{name}-Chrome-{version}.zip"
        files[path] = _zip_bytes(native)
        downloads.extend([
            {"name": name, "platform": "chrome", "path": path, "kind": "native-theme-zip", "version": version},
            {"name": name, "platform": "equicord", "path": f"equicord/{name}.theme.css", "kind": "local-theme-css", "version": version},
        ])
        # Edge uses the original Chromium artifact. An alias is not a native pass.
        downloads.append({"name": name, "platform": "edge", "path": path,
                          "kind": "chromium-theme-zip", "version": version, "native_acceptance": "unverified"})
        downloads.append({"name": name, "platform": "brave", "path": path,
                          "kind": "chromium-theme-zip", "version": version, "native_acceptance": "unverified"})
        native = {key.split("/", 2)[2]: data for key, data in files.items() if key.startswith(f"firefox/{name.lower()}/")}
        path = f"artifacts/{name}-Firefox-{PORTABILITY_VERSION}.xpi"
        files[path] = _zip_bytes(native)
        downloads.append({"name": name, "platform": "firefox", "path": path,
                          "kind": "unsigned-static-theme-xpi", "version": PORTABILITY_VERSION, "native_acceptance": "unverified"})
        path = f"artifacts/{name}-Vivaldi-{BROWSER_VERSION}.zip"
        files[path] = _zip_bytes({"settings.json": files[f"vivaldi/{name.lower()}/settings.json"]})
        downloads.append({"name": name, "platform": "vivaldi", "path": path,
                          "kind": "shareable-settings-zip", "version": BROWSER_VERSION, "native_acceptance": "unverified"})
        for client, label in CLIENTS.items():
            downloads.append({"name": name, "platform": client, "path": f"{client}/{name}-{label}.theme.css",
                              "kind": "local-theme-css", "version": PORTABILITY_VERSION, "native_acceptance": "unverified"})
    path = f"artifacts/Clair-Obscur-OperaGX-{BROWSER_VERSION}.zip"
    files[path] = _zip_bytes({key.split("/", 1)[1]: data for key, data in files.items() if key.startswith("opera-gx/")})
    downloads.append({"name": "Clair and Obscur", "platform": "opera-gx", "path": path,
                      "kind": "paired-color-hints-zip", "version": BROWSER_VERSION, "native_acceptance": "unverified"})
    manifest = {
        "schema_version": 1,
        "generator": OWNER,
        "version": version,
        "adapter_version": PORTABILITY_VERSION,
        "browser_adapter_version": BROWSER_VERSION,
        "tokens_sha256": _digest(_json_bytes(document)),
        "files": [{"path": name, "sha256": _digest(data), "bytes": len(data)} for name, data in sorted(files.items())],
        "downloads": downloads,
    }
    files[MANIFEST] = _json_bytes(manifest)
    files[CHECKSUMS] = _checksum_bytes(files)
    for name, data in files.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    _verify_owned(stage)
    return manifest


def _remove_owned_tree(root: Path, expected: dict[str, bytes]) -> None:
    """Delete only the exact files just inspected, then empty directories."""
    files, directories = _inventory(root)
    if files != expected:
        raise ValueError("Cleanup refused because owned temporary files changed")
    for name in sorted(files):
        (root / name).unlink()
    for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        directory.rmdir()
    root.rmdir()


@contextmanager
def _cleanup_scope(cleanup, label: str):
    """Retire owned temporary state without replacing an earlier failure."""
    try:
        yield
    except BaseException as failure:
        try:
            cleanup()
        except BaseException as cleanup_error:
            # Diagnostics must not turn an interruption or generation error
            # into an unrelated cleanup failure, even if add_note fails.
            try:
                failure.add_note(
                    f"{label} could not finish ({type(cleanup_error).__name__}). "
                    "Inspect remaining temporary files before retrying."
                )
            except BaseException:
                pass
        raise
    else:
        # Without an earlier error, failed cleanup remains the actual failure.
        cleanup()


def _retire_stage(stage: Path) -> None:
    if stage.exists():
        partial, _ = _inventory(stage)
        _remove_owned_tree(stage, partial)


@contextmanager
def _output_lock(output: Path):
    lock = output.parent / f".themeforge-{output.name}.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Another build owns this output lock. Inspect it before retrying") from error
    with _cleanup_scope(lock.unlink, "Output lock cleanup"):
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        yield


def _install_stage(stage: Path, output: Path, previous: dict[str, bytes],
                   generated: dict[str, bytes]) -> None:
    """Restore the prior tree if an owned install is interrupted before commit."""
    had_output = output.exists()
    backup = None
    try:
        if had_output:
            backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.previous-", dir=output.parent))
            backup.rmdir()
            output.rename(backup)
        stage.rename(output)
    except BaseException as failure:
        # A signal can arrive after rename takes effect but before it returns.
        # Inspect actual trees rather than treating the exception as proof that
        # nothing moved. Never replace or delete intervening foreign output.
        try:
            if backup is not None and backup.exists():
                backup_files, backup_directories = _inventory(backup)
                if (not backup_files and not backup_directories and output.exists()
                        and stage.exists() and _verify_owned(output) == previous):
                    _remove_owned_tree(backup, {})
                else:
                    if _verify_owned(backup) != previous:
                        raise ValueError("The previous build changed during recovery")
                    if output.exists():
                        if _verify_owned(output) != generated:
                            raise ValueError("The output changed during recovery")
                        _remove_owned_tree(output, generated)
                    backup.rename(output)
            elif not had_output and output.exists():
                if _verify_owned(output) != generated:
                    raise ValueError("The output changed during recovery")
                _remove_owned_tree(output, generated)
        except BaseException as recovery_error:
            failure.add_note(
                f"Build recovery could not finish ({type(recovery_error).__name__}). "
                "Preserved remaining output and previous-build files. Inspect them before retrying."
            )
        raise
    # The new tree is committed only after its install returned successfully.
    # Later cleanup failure leaves that complete output available for inspection.
    if backup is not None:
        _remove_owned_tree(backup, previous)


def build_release(tokens_path: Path, output: Path, *, check: bool = False) -> dict:
    """Build or compare the complete release tree without installing anything.

    Existing builds must retain their manifest, every original digest and no
    foreign files. A failed generator leaves the previous output untouched.
    The check mode compares every byte and does not rewrite the output tree.
    """
    try:
        document = load(Path(tokens_path))
    except (AttributeError, TypeError) as error:
        raise ValueError("Malformed token document structure") from error
    output = _safe_destination(Path(output))
    if check and not output.is_dir():
        raise ValueError("Check requires an existing complete output tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    with _output_lock(output):
        previous = _verify_owned(output)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
        with _cleanup_scope(lambda: _retire_stage(stage), "Staging cleanup"):
            manifest = _generate(document, stage)
            generated, _ = _inventory(stage)
            if check:
                if generated != previous:
                    raise ValueError("Generated output differs. Build into a fresh output to inspect the change")
                return manifest
            # Reinspect immediately before the rename so intervening user edits
            # are preserved instead of being silently replaced.
            if _verify_owned(output) != previous:
                raise ValueError("Output changed during generation")
            _install_stage(stage, output, previous, generated)
            return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify Clair and Obscur theme artifacts and portability candidates")
    parser.add_argument("--tokens", type=Path, default=PROJECT_ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="Compare the existing complete output without rewriting it")
    args = parser.parse_args(argv)
    try:
        manifest = build_release(args.tokens, args.output, check=args.check)
    except (OSError, ValueError, TypeError) as error:
        notes = "".join(f"{note}\n" for note in getattr(error, "__notes__", ()))
        parser.exit(1, f"Build failed: {error}\n{notes}")
    print(f"{'Verified' if args.check else 'Built'} {manifest['version']} with adapters {manifest['adapter_version']} "
          f"and browsers {manifest['browser_adapter_version']}: "
          f"{len(manifest['downloads'])} download choices, {len(manifest['files'])} payload files")
    return 0
