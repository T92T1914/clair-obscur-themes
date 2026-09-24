"""Build the static specimen and its verified downloads into a new directory."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import tempfile

from themeforge.build import (
    _inventory, _linked, _output_lock, _remove_owned_tree, _safe_destination,
    _verify_owned, _zip_bytes, build_release,
)
from themeforge.equicord import FACES
from themeforge.tokens import load

ROOT = Path(__file__).resolve().parent
WEB_ASSETS = frozenset({'index.html', 'preview.css', 'preview.js'})
REPOSITORY_URL = 'https://github.com/T92T1914/clair-obscur-themes'


def read_source(root: Path, path: Path) -> bytes:
    """Reject linked files and directories before opening selected public input."""
    path.relative_to(root)
    for item in (path, *path.parents):
        if _linked(item):
            raise ValueError(f'Linked source input is not publishable: {path.name}')
    if not path.is_file():
        raise ValueError(f'Missing source file: {path.name}')
    return path.read_bytes()


def source_files(root: Path) -> dict[str, bytes]:
    """Package reviewed source categories, never a broad workspace archive."""
    paths = [root / name for name in (
        'README.md', 'AGENTS.md', 'LICENSE', 'CHANGELOG.md', 'tokens.json', 'build.py', 'preview.py',
        'package.json', 'package-lock.json', '.gitignore', '.gitattributes',
    )]
    for folder, endings in (
        ('themeforge', {'.py'}), ('tests', {'.py', '.mjs'}),
        ('web', {'.html', '.css', '.js'}), ('docs', {'.md'}),
        ('research', {'.md', '.json', '.csv'}), ('.github', {'.yml', '.md'}),
    ):
        pending = [root / folder]
        while pending:
            directory = pending.pop()
            if _linked(directory):
                raise ValueError('Linked source directories are not publishable')
            for entry in directory.iterdir():
                if _linked(entry):
                    raise ValueError('Linked source entries are not publishable')
                if entry.is_dir():
                    if entry.name != '__pycache__':
                        pending.append(entry)
                elif entry.is_file() and entry.suffix in endings:
                    paths.append(entry)
    result = {}
    for path in sorted(paths):
        result[path.relative_to(root).as_posix()] = read_source(root, path)
    return result


def source_identity(root: Path, sources: dict[str, bytes], expected_revision: str | None = None) -> dict:
    """Identify the captured public source, without requiring Git in source exports."""
    if expected_revision is not None and not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', expected_revision):
        raise ValueError('Expected revision must be a complete lowercase Git commit ID')
    if not (root / '.git').exists():
        if expected_revision is not None:
            raise ValueError('Expected revision requires a Git checkout')
        return {'revision': None, 'state': 'unavailable'}

    def git(*arguments: str) -> bytes:
        try:
            result = subprocess.run(['git', '-C', str(root), *arguments], capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError('Cannot inspect the source Git checkout') from error
        if result.returncode != 0:
            raise ValueError('Cannot inspect the source Git checkout')
        return result.stdout

    revision = git('rev-parse', '--verify', 'HEAD').decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision):
        raise ValueError('Git returned an invalid source revision')
    if expected_revision is not None and revision != expected_revision:
        raise ValueError('Source HEAD differs from the expected revision')
    # Compare the captured bytes themselves with committed blobs. A clean status
    # alone would miss a source edit captured just before the file was restored.
    committed = {}
    for entry in git('ls-tree', '-rz', revision).split(b'\0'):
        if entry:
            metadata, path = entry.split(b'\t', 1)
            mode, kind, digest = metadata.split(b' ')
            if kind == b'blob' and mode in (b'100644', b'100755'):
                committed[path.decode('utf-8')] = digest.decode('ascii')
    algorithm = 'sha1' if len(revision) == 40 else 'sha256'
    changed = any(
        hashlib.new(algorithm, b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != committed.get(path)
        for path, data in sources.items()
    )
    tracked_changes = bool(git('status', '--porcelain', '--untracked-files=no'))
    if git('rev-parse', '--verify', 'HEAD').decode('ascii').strip() != revision:
        raise ValueError('Source HEAD changed while building the preview')
    if expected_revision is not None and (changed or tracked_changes):
        raise ValueError('Expected revision requires unchanged committed source')
    return {'revision': revision, 'state': 'modified' if changed or tracked_changes else 'clean'}


def preview_files(root: Path, artifacts: Path, expected_revision: str | None = None) -> dict[str, bytes]:
    document = load(root / 'tokens.json')
    manifest = build_release(root / 'tokens.json', artifacts, check=True)
    # Keep the exact verified snapshot. Later edits cannot replace bytes already
    # captured here, and a concurrent newer complete build has a different manifest.
    with _output_lock(artifacts):
        snapshot = _verify_owned(artifacts)
        if json.loads(snapshot.get('artifact-manifest.json', b'null')) != manifest:
            raise ValueError('Artifact snapshot changed after verification')
    if {p.name for p in (root / 'web').iterdir()} != WEB_ASSETS:
        raise ValueError('Unreviewed web assets must not enter the public preview')
    files = {name: read_source(root, root / 'web' / name) for name in sorted(WEB_ASSETS)}
    groups = {'chrome': [], 'equicord': []}
    for download in manifest['downloads']:
        name, platform, path = download['name'], download['platform'], download['path']
        label = 'Google Chrome' if platform == 'chrome' else 'Equibop + Equicord'
        kind = 'Native theme ZIP' if platform == 'chrome' else 'Standalone CSS'
        record = next(r for r in manifest['files'] if r['path'] == path)
        groups[platform].append(
            f'<article id="{platform}-{name.lower()}" class="download-card"><p class="eyebrow">Preview {document["version"]}</p>'
            f'<h4>{name}</h4><a class="button" download href="downloads/{path}">'
            f'Download {name} for {label}</a><small>{kind}, {record["bytes"]:,} bytes. '
            'Native acceptance pending.</small></article>'
        )
    sources = source_files(root)
    identity = source_identity(root, sources, expected_revision)
    version = document['version']
    release_url = f'{REPOSITORY_URL}/releases/download/v{version}'
    if identity['revision'] is None:
        source_description = 'Revision unavailable in this source copy.'
    else:
        revision = identity['revision']
        revision_link = f'<a href="{REPOSITORY_URL}/tree/{revision}" rel="noreferrer">{revision}</a>'
        source_description = (f'Built from {revision_link}.' if identity['state'] == 'clean'
                              else f'Based on {revision_link} with local source changes.')
    text = (files['index.html'].decode().replace('{{VERSION}}', html.escape(version))
            .replace('{{RELEASE_URL}}', html.escape(release_url, quote=True))
            .replace('{{SOURCE_DESCRIPTION}}', source_description))
    for platform, cards in groups.items():
        text = text.replace('{{' + platform.upper() + '_CARDS}}', '\n'.join(cards))
    files['index.html'] = text.encode()
    css = []
    for weight, style, full, postscript in FACES:
        css.append(f'@font-face {{font-family:"Clair Obscur Inter";src:local("{full}"),local("{postscript}");font-weight:{weight};font-style:{style};font-display:swap;}}')
    for name, tokens in document['themes'].items():
        # :where keeps system-color media overrides stronger than this selector.
        css.append(f':where(:root[data-theme="{name}"], [data-palette="{name}"]) {{')
        css.extend(f'--{key.replace("_", "-")}:{value};' for key, value in tokens.items())
        css.append(f'color-scheme:{"light" if name == "Clair" else "dark"};}}')
    files['tokens.css'] = ('\n'.join(css) + '\n').encode()
    for record in manifest['files']:
        path = record['path']
        files[f'downloads/{path}'] = snapshot[path]
    for name in ('SHA256SUMS', 'artifact-manifest.json'):
        files[f'downloads/{name}'] = snapshot[name]
    files['LICENSE'] = read_source(root, root / 'LICENSE')
    files['source.zip'] = _zip_bytes(sources)
    source_digest = hashlib.sha256(files['source.zip']).hexdigest()
    files['source-SHA256SUMS'] = f'{source_digest}  source.zip\n'.encode()
    # GitHub release assets share one flat directory. The build-tree checksums
    # remain separate because their nested paths would not verify those downloads.
    release_hashes = {
        Path(item['path']).name: hashlib.sha256(snapshot[item['path']]).hexdigest()
        for item in manifest['downloads']
    }
    release_hashes['artifact-manifest.json'] = hashlib.sha256(files['downloads/artifact-manifest.json']).hexdigest()
    release_hashes['source.zip'] = source_digest
    files['release-SHA256SUMS'] = ''.join(
        f'{digest}  {name}\n' for name, digest in sorted(release_hashes.items())
    ).encode()
    files['site-manifest.json'] = (json.dumps({
        'schema_version': 2, 'generator': 'clair-obscur-preview',
        'source': {**identity, 'archive': 'source.zip', 'sha256': source_digest},
        'release': {'version': version, 'source_url': f'{release_url}/source.zip',
                    'checksums_url': f'{release_url}/release-SHA256SUMS'},
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }, indent=2, sort_keys=True) + '\n').encode()
    return files


def build_preview(root: Path, artifacts: Path, output: Path, expected_revision: str | None = None) -> None:
    output = _safe_destination(output)
    files = preview_files(root, artifacts, expected_revision)
    if output.exists():
        existing, _ = _inventory(output)
        if existing != files:
            raise ValueError('Preview output differs. Choose a fresh output directory to preserve existing files')
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.preview-stage-', dir=output.parent))
    try:
        for name, data in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        stage.rename(output)
    finally:
        if stage.exists():
            created, _ = _inventory(stage)
            _remove_owned_tree(stage, created)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'dist')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs' / 'preview')
    parser.add_argument('--expected-revision', help='Require clean source at this complete Git commit ID')
    args = parser.parse_args()
    try:
        build_preview(ROOT, args.artifacts, args.output, args.expected_revision)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Preview build failed: {error}\n')
    print('Built static specimen, four theme downloads and source archive')


if __name__ == '__main__':
    main()
