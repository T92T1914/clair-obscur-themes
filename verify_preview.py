"""Compare an extracted portable preview with its included directory manifest."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import BinaryIO

MAX_MANIFEST_BYTES = 65_536
MAX_DECLARED_FILES = 128
MAX_ENTRIES = 256
MAX_FILE_BYTES = 8_388_608
MAX_READ_BYTES = 16_777_216
READ_CHUNK = 65_536
MAX_REPORT_BYTES = 262_144
MANIFEST_NAME = 'site-manifest.json'
CORE_FILES = frozenset({
    'index.html', 'preview.css', 'preview.js', 'tokens.css', 'LICENSE',
    'source.zip', 'source-SHA256SUMS', 'release-SHA256SUMS',
    'downloads/artifact-manifest.json', 'downloads/SHA256SUMS',
})
VERIFICATION_FILES = frozenset({'verify_preview.py', 'portable-verification.md'})
RELEASE_PREFIX = (
    'https://github.com/T92T1914/clair-obscur-themes/releases/download/'
)
DISCLOSURE = (
    'Consistency with the included manifest only. '
    'Origin, safety and native compatibility remain unverified.'
)


class VerificationInputError(ValueError):
    """An unsupported input or content limit prevents admission."""


class VerificationObservationError(OSError):
    """A failed read or observed change prevents a completed comparison."""


@dataclass(frozen=True)
class Observation:
    kind: str
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    attributes: int


@dataclass
class ReadBudget:
    used: int = 0

    def available(self, reserve: int = 0) -> int:
        return MAX_READ_BYTES - self.used - reserve

    def read(self, stream: BinaryIO, count: int, reserve: int) -> bytes:
        if count < 1 or count > self.available(reserve):
            raise VerificationInputError('Aggregate read limit exceeded')
        data = stream.read(count)
        self.used += len(data)
        return data


@dataclass(frozen=True)
class Manifest:
    hashes: dict[str, str]
    files: frozenset[str]
    directories: frozenset[str]
    revision: str | None
    state: str


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _safe_path(name: str) -> None:
    if not isinstance(name, str) or not 1 <= len(name) <= 240:
        raise VerificationInputError('Unsupported relative path length')
    parts = name.split('/')
    if len(parts) > 8:
        raise VerificationInputError(f'Path depth exceeds eight: {_quoted(name)}')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {
        f'{prefix}{number}' for prefix in ('COM', 'LPT') for number in range(1, 10)
    }
    for part in parts:
        if (not re.fullmatch(r'[A-Za-z0-9_.-]+', part)
                or part in ('.', '..') or part.endswith('.')
                or part.split('.')[0].upper() in reserved):
            raise VerificationInputError(f'Unsupported relative path: {_quoted(name)}')


def _names(files: set[str], directories: set[str]) -> None:
    if len(files) + len(directories) > MAX_ENTRIES:
        raise VerificationInputError('Combined inventory limit exceeded')
    if files & directories:
        raise VerificationInputError('File and directory paths conflict')
    spellings: dict[str, str] = {}
    for name in sorted(files | directories, key=lambda value: value.encode('utf-8')):
        _safe_path(name)
        lowered = name.lower()
        if lowered in spellings:
            raise VerificationInputError('Case-insensitive inventory paths collide')
        spellings[lowered] = name
        parts = name.split('/')
        for end in range(1, len(parts)):
            if '/'.join(parts[:end]) in files:
                raise VerificationInputError('File and directory prefix paths conflict')


def _object(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise VerificationInputError(f'Unsupported {label} shape')
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationInputError('Duplicate manifest object key')
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise VerificationInputError(f'Nonfinite manifest constant: {value}')


def parse_manifest(data: bytes) -> Manifest:
    """Admit this portable schema without interpreting any declared file."""
    if len(data) > MAX_MANIFEST_BYTES:
        raise VerificationInputError('Manifest byte limit exceeded')
    try:
        document = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                              parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise VerificationInputError('Invalid UTF-8 JSON manifest') from error
    root = _object(document, {
        'schema_version', 'generator', 'source', 'release', 'distribution', 'files',
    }, 'manifest')
    if type(root['schema_version']) is not int or root['schema_version'] != 2:
        raise VerificationInputError('Unsupported manifest schema version')
    if root['generator'] != 'clair-obscur-preview':
        raise VerificationInputError('Unsupported manifest generator')
    distribution = _object(root['distribution'], {'kind'}, 'distribution')
    if distribution['kind'] != 'portable-kit':
        raise VerificationInputError('Manifest is not an extracted portable kit')
    hashes = root['files']
    if not isinstance(hashes, dict) or not 1 <= len(hashes) <= MAX_DECLARED_FILES:
        raise VerificationInputError('Unsupported declared file count')
    for name, digest in hashes.items():
        _safe_path(name)
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise VerificationInputError('Invalid declared SHA-256')
    if MANIFEST_NAME in hashes or not CORE_FILES <= hashes.keys():
        raise VerificationInputError('Missing core files or self-referential manifest')
    if VERIFICATION_FILES & hashes.keys() and not VERIFICATION_FILES <= hashes.keys():
        raise VerificationInputError('Verifier and guide must both be declared')
    files = set(hashes) | {MANIFEST_NAME}
    directories = {
        '/'.join(name.split('/')[:end])
        for name in files for end in range(1, len(name.split('/')))
    }
    _names(files, directories)
    source = _object(root['source'], {'revision', 'state', 'archive', 'sha256'}, 'source')
    revision, state = source['revision'], source['state']
    if revision is None:
        valid_identity = state == 'unavailable'
    else:
        valid_identity = (
            isinstance(revision, str)
            and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision) is not None
            and state in ('clean', 'modified')
        )
    if not valid_identity:
        raise VerificationInputError('Unsupported stored source identity')
    if source['archive'] != 'source.zip' or source['sha256'] != hashes['source.zip']:
        raise VerificationInputError('Source archive hash declaration disagrees')
    release = _object(root['release'], {'version', 'source_url', 'checksums_url'}, 'release')
    version = release['version']
    if (not isinstance(version, str) or len(version) > 32
            or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version)):
        raise VerificationInputError('Unsupported release version')
    base = f'{RELEASE_PREFIX}v{version}/'
    if (release['source_url'] != base + 'source.zip'
            or release['checksums_url'] != base + 'release-SHA256SUMS'):
        raise VerificationInputError('Unsupported stored release URLs')
    return Manifest(dict(hashes), frozenset(files), frozenset(directories), revision, state)


def _observation(info: os.stat_result) -> Observation:
    attributes = getattr(info, 'st_file_attributes', 0)
    if stat.S_ISLNK(info.st_mode) or attributes & 0x400:
        raise VerificationInputError('Linked or reparse entries are unsupported')
    if stat.S_ISREG(info.st_mode):
        kind = 'FILE'
    elif stat.S_ISDIR(info.st_mode):
        kind = 'DIR'
    else:
        raise VerificationInputError('Nonregular entries are unsupported')
    return Observation(kind, info.st_dev, info.st_ino, info.st_mode, info.st_size,
                       info.st_mtime_ns, info.st_ctime_ns, attributes)


def _lstat(path: Path) -> Observation:
    try:
        return _observation(path.lstat())
    except OSError as error:
        raise VerificationObservationError(f'Cannot observe {_quoted(path.name)}') from error


def _root(value: str | Path) -> tuple[Path, dict[Path, Observation]]:
    raw = os.fspath(value)
    if not raw or '\x00' in raw:
        raise VerificationInputError('Select a nonempty extracted directory path')
    path = Path(raw).absolute()
    if os.path.abspath(path) == path.anchor:
        raise VerificationInputError('Filesystem roots are not supported')
    ancestors: dict[Path, Observation] = {}
    # Inspect in traversal order, before using a child through an ancestor.
    for item in (*reversed(path.parents), path):
        try:
            observed = _observation(item.lstat())
        except (FileNotFoundError, NotADirectoryError) as error:
            raise VerificationInputError('Selected directory is missing or not a directory') from error
        except OSError as error:
            raise VerificationObservationError('Cannot observe selected directory') from error
        if observed.kind != 'DIR':
            raise VerificationInputError('Selected path or ancestor is not a directory')
        ancestors[item] = observed
    return path, ancestors


def inventory(root: Path) -> dict[str, Observation]:
    """Collect at most 256 entries without following links or reading content."""
    result: dict[str, Observation] = {}
    pending = [root]
    files: set[str] = set()
    directories: set[str] = set()
    while pending:
        directory = pending.pop()
        try:
            observed_directory = _lstat(directory)
        except VerificationInputError as error:
            raise VerificationObservationError('Directory changed during inventory') from error
        if observed_directory.kind != 'DIR':
            raise VerificationObservationError('Directory changed during inventory')
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if len(result) >= MAX_ENTRIES:
                        raise VerificationInputError('Actual inventory limit exceeded')
                    path = directory / entry.name
                    name = path.relative_to(root).as_posix()
                    _safe_path(name)
                    # Fresh path metadata carries file identity on Windows.
                    # DirEntry.stat can supply cached or dummy identity fields.
                    observed = _lstat(path)
                    result[name] = observed
                    (files if observed.kind == 'FILE' else directories).add(name)
                    _names(files, directories)
                    if observed.kind == 'DIR':
                        pending.append(path)
        except OSError as error:
            raise VerificationObservationError('Cannot complete directory inventory') from error
    return result


def _same(path: Path, expected: Observation) -> None:
    try:
        actual = _lstat(path)
    except VerificationInputError as error:
        raise VerificationObservationError('Entry changed during verification') from error
    if actual != expected:
        raise VerificationObservationError(f'Entry changed: {_quoted(path.name)}')


def _read(root: Path, name: str, expected: Observation, budget: ReadBudget,
          cap: int, reserve: int = 0, capture: bool = False) -> tuple[str, bytes]:
    if expected.kind != 'FILE':
        raise VerificationObservationError('Expected regular file changed type')
    if expected.size > cap:
        raise VerificationInputError(f'File byte limit exceeded: {_quoted(name)}')
    if expected.size + 1 > budget.available(reserve):
        raise VerificationInputError('Aggregate read limit exceeded')
    path = root / name
    _same(path, expected)
    digest = hashlib.sha256()
    captured = bytearray()
    count = 0
    try:
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0)
        flags |= getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, 'rb', buffering=0) as stream:
            try:
                opened = _observation(os.fstat(stream.fileno()))
            except VerificationInputError as error:
                raise VerificationObservationError('Opened file is no longer regular') from error
            if opened != expected:
                raise VerificationObservationError(f'Opened file changed: {_quoted(name)}')
            while True:
                request = min(READ_CHUNK, expected.size - count + 1,
                              budget.available(reserve))
                data = budget.read(stream, request, reserve)
                if not data:
                    break
                count += len(data)
                if count > expected.size:
                    raise VerificationObservationError(f'File grew: {_quoted(name)}')
                digest.update(data)
                if capture:
                    captured.extend(data)
            if count != expected.size:
                raise VerificationObservationError(f'File changed while reading: {_quoted(name)}')
            try:
                final_opened = _observation(os.fstat(stream.fileno()))
            except VerificationInputError as error:
                raise VerificationObservationError('Opened file changed while reading') from error
            if final_opened != expected:
                raise VerificationObservationError(f'File changed while reading: {_quoted(name)}')
    except OSError as error:
        raise VerificationObservationError(f'Cannot read stable file: {_quoted(name)}') from error
    _same(path, expected)
    return digest.hexdigest(), bytes(captured)


def _report(manifest: Manifest, observed: dict[str, Observation], hashes: dict[str, str],
            manifest_digest: str) -> tuple[int, bytes]:
    files = {name for name, entry in observed.items() if entry.kind == 'FILE'}
    directories = set(observed) - files
    groups = (
        ('missing FILE', manifest.files - files),
        ('missing DIR', manifest.directories - directories),
        ('changed FILE', {name for name, digest in hashes.items()
                          if digest != manifest.hashes[name]}),
        ('extra FILE', files - manifest.files),
        ('extra DIR', directories - manifest.directories),
    )
    status = int(any(paths for _, paths in groups))
    result = 'discrepancies' if status else 'consistent'
    lines = [
        f'Portable kit verification: {result}',
        f'Expected regular files: {len(manifest.files)}',
        f'Expected directories: {len(manifest.directories)}',
        f'Observed manifest SHA-256: {manifest_digest}',
        f'Stored source revision: {manifest.revision or "null"}',
        f'Stored source state: {manifest.state}',
    ]
    for label, paths in groups:
        for name in sorted(paths, key=lambda value: value.encode('utf-8')):
            row = f'{label} {_quoted(name)}'
            if label == 'changed FILE':
                row += f' expected={manifest.hashes[name]} observed={hashes[name]}'
            lines.append(row)
    rendered = ('\n'.join([*lines, DISCLOSURE]) + '\n').encode('ascii')
    if len(rendered) > MAX_REPORT_BYTES:
        raise VerificationInputError('Complete report byte limit exceeded')
    return status, rendered


def verify(root: str | Path) -> tuple[int, bytes]:
    """Return a completed report, or refuse without emitting a partial verdict."""
    directory, ancestors = _root(root)
    first = inventory(directory)
    manifest_entry = first.get(MANIFEST_NAME)
    if manifest_entry is None or manifest_entry.kind != 'FILE':
        raise VerificationInputError('Missing regular site-manifest.json')
    budget = ReadBudget()
    manifest_digest, data = _read(directory, MANIFEST_NAME, manifest_entry,
                                  budget, MAX_MANIFEST_BYTES, capture=True)
    manifest = parse_manifest(data)
    hashes: dict[str, str] = {}
    reserve = len(data) + 1
    for name in sorted(manifest.hashes, key=lambda value: value.encode('utf-8')):
        entry = first.get(name)
        if entry is not None and entry.kind == 'FILE':
            hashes[name], _ = _read(directory, name, entry, budget, MAX_FILE_BYTES, reserve)
    for path, entry in ancestors.items():
        _same(path, entry)
    try:
        second = inventory(directory)
    except VerificationInputError as error:
        raise VerificationObservationError('Inventory changed during verification') from error
    if second != first:
        raise VerificationObservationError('Inventory changed during verification')
    _, checked_data = _read(directory, MANIFEST_NAME, manifest_entry,
                            budget, MAX_MANIFEST_BYTES, capture=True)
    if checked_data != data:
        raise VerificationObservationError('Manifest changed during verification')
    for path, entry in ancestors.items():
        _same(path, entry)
    return _report(manifest, first, hashes, manifest_digest)


def _diagnostic(message: str) -> None:
    try:
        sys.stderr.write(f'Portable kit verification: {message}\n')
    except OSError:
        pass


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='Complete extracted portable kit directory')
    args = parser.parse_args(arguments)
    try:
        status, rendered = verify(args.directory)
    except VerificationInputError as error:
        _diagnostic(f'refused: {error}')
        return 2
    except OSError as error:
        _diagnostic(f'unverified: {error}')
        return 3
    except KeyboardInterrupt:
        _diagnostic('interrupted, no completed verdict')
        return 130
    try:
        if sys.stdout.buffer.write(rendered) != len(rendered):
            raise OSError('Incomplete report write')
        sys.stdout.buffer.flush()
    except OSError as error:
        _diagnostic(f'output failed: {error}')
        return 3
    except KeyboardInterrupt:
        _diagnostic('interrupted during output, no completed verdict')
        return 130
    return status


if __name__ == '__main__':
    exit_code = main()
    if exit_code in (3, 130):
        try:
            sys.stdout.close()
        except OSError:
            pass
    raise SystemExit(exit_code)
