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
from .legal import license_comment, license_text
from .tokens import load


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OWNER = "clair-obscur-themeforge"
MANIFEST = "artifact-manifest.json"
CHECKSUMS = "SHA256SUMS"
SHA = re.compile(r"[0-9a-f]{64}\Z")


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
    if set(files) != expected:
        raise ValueError("Generated payload contains missing or unexpected files")
    for path, payload in files.items():
        if path.endswith(".png"):
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Chrome icon is not a PNG")
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
                raise ValueError("Chrome package must retain the complete canonical license")
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
    files, _ = _inventory(stage)
    _review_payloads(files)
    downloads = []
    for name in ("Clair", "Obscur"):
        native = {key.split("/", 2)[2]: data for key, data in files.items() if key.startswith(f"chrome/{name.lower()}/")}
        path = f"artifacts/{name}-Chrome-{version}.zip"
        files[path] = _zip_bytes(native)
        downloads.extend([
            {"name": name, "platform": "chrome", "path": path, "kind": "native-theme-zip"},
            {"name": name, "platform": "equicord", "path": f"equicord/{name}.theme.css", "kind": "local-theme-css"},
        ])
    manifest = {
        "schema_version": 1,
        "generator": OWNER,
        "version": version,
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
def _output_lock(output: Path):
    lock = output.parent / f".themeforge-{output.name}.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Another build owns this output lock. Inspect it before retrying") from error
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        yield
    finally:
        lock.unlink()


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
        try:
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
            backup = None
            if output.exists():
                backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.previous-", dir=output.parent))
                backup.rmdir()
                output.rename(backup)
            try:
                stage.rename(output)
            except OSError:
                if backup is not None:
                    backup.rename(output)
                raise
            if backup is not None:
                _remove_owned_tree(backup, previous)
            return manifest
        finally:
            if stage.exists():
                partial, _ = _inventory(stage)
                _remove_owned_tree(stage, partial)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the four Clair and Obscur theme artifacts")
    parser.add_argument("--tokens", type=Path, default=PROJECT_ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="Compare the existing complete output without rewriting it")
    args = parser.parse_args(argv)
    try:
        manifest = build_release(args.tokens, args.output, check=args.check)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"{'Verified' if args.check else 'Built'} {manifest['version']}: four theme downloads, {len(manifest['files'])} payload files")
    return 0
