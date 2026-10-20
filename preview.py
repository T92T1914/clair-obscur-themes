"""Build the static specimen and its verified downloads into a new directory."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from themeforge.build import (
    CLAIR_EQUICORD_FOCUS_PATH, _cleanup_scope, _digest, _inventory, _json_bytes, _linked, _output_lock, _retire_stage,
    _safe_destination, _verify_owned, _zip_bytes, build_release,
)
from themeforge.equicord import FACES
from themeforge.guides import guide_anchor, render_guides
from themeforge.icons import render_icons
from themeforge.terminal import ANSI_FIELDS, ARCHIVE as TERMINAL_ARCHIVE, FRAGMENT as TERMINAL_FRAGMENT, render_terminal
from themeforge.legal import normalize_license
from themeforge.tokens import load

ROOT = Path(__file__).resolve().parent
WEB_ASSETS = frozenset({'index.html', 'preview.css', 'preview.js'})
REPOSITORY_URL = 'https://github.com/T92T1914/clair-obscur-themes'
PORTABLE_ARCHIVE = 'Clair-Obscur-portable-preview.zip'
PORTABLE_CHECKSUMS = 'portable-SHA256SUMS'
ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.10.0.zip'
EVERYDAY_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.9.0.zip'
BROAD_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.8.0.zip'
COMPANION_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.7.0.zip'
MONOCHROME_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.6.0.zip'
THIRD_APP_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.5.0.zip'
SECOND_APP_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.4.0.zip'
FIRST_APP_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.3.0.zip'
PREVIOUS_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.2.0.zip'
LEGACY_ICON_ARCHIVE = 'icons/Clair-Obscur-SVG-Icons-0.1.0.zip'
ICON_CHECKSUMS = 'icons/SVG-SHA256SUMS'
GARMIN_SOURCE_FILES = (
    'garmin/build.py', 'garmin/watchface/manifest.xml', 'garmin/watchface/monkey.jungle',
    'garmin/watchface/resources/settings/properties.xml',
    'garmin/watchface/resources/settings/settings.xml',
    'garmin/watchface/resources/strings/strings.xml',
    'garmin/watchface/resources/drawables/drawables.xml',
    'garmin/watchface/resources/drawables/launcher.svg',
    'garmin/watchface/source/ClairObscurApp.mc',
    'garmin/watchface/source/ClairObscurView.mc',
    'garmin/watchface/source/FaceData.mc',
    'garmin/watchface/source/FaceModel.mc', 'garmin/watchface/source/FaceSettings.mc',
    'garmin/watchface/source/GeneratedPalette.mc',
    'garmin/watchface/tests/FaceDataTests.mc',
    'garmin/watchface/tests/FaceLayoutTests.mc',
    'garmin/watchface/tests/FaceModelTests.mc',
)


def site_manifest(files: dict[str, bytes], source: dict, release: dict, distribution: dict) -> bytes:
    """Hash the actual directory members without a self-referential digest."""
    return _json_bytes({
        'schema_version': 2, 'generator': 'clair-obscur-preview',
        'source': source, 'release': release, 'distribution': distribution,
        'files': {name: _digest(data) for name, data in sorted(files.items())},
    })


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
        'README.md', 'AGENTS.md', 'LICENSE', 'CHANGELOG.md', 'tokens.json', 'tokens-monochrome.json', 'build.py', 'preview.py',
        'verify_preview.py',
        'package.json', 'package-lock.json', '.gitignore', '.gitattributes',
        'tools/export-icons.mjs',
    )]
    # Only the reviewed project files belong in the public source snapshot.
    # SDKs, keys, compiled programs and debug XML stay outside this inventory.
    paths.extend(root / name for name in GARMIN_SOURCE_FILES)
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

    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith('GIT_')
    }
    environment.update(GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')

    def git(*arguments: str) -> bytes:
        try:
            result = subprocess.run(
                ['git', '--no-optional-locks', '--no-replace-objects',
                 '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
                 '-C', str(root), *arguments],
                capture_output=True, timeout=15, env=environment,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
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
    identity_document = load(root / 'tokens-monochrome.json')
    identity_digest = _digest(_json_bytes(identity_document))
    tokens_digest = _digest(_json_bytes(document))
    manifest = build_release(root / 'tokens.json', artifacts, check=True)
    if manifest['tokens_sha256'] != tokens_digest:
        raise ValueError('Token snapshot changed during artifact verification')
    # Keep the exact verified snapshot. Later edits cannot replace bytes already
    # captured here, and a concurrent newer complete build has a different manifest.
    with _output_lock(artifacts):
        snapshot = _verify_owned(artifacts)
        if json.loads(snapshot.get('artifact-manifest.json', b'null')) != manifest:
            raise ValueError('Artifact snapshot changed after verification')
    if {p.name for p in (root / 'web').iterdir()} != WEB_ASSETS:
        raise ValueError('Unreviewed web assets must not enter the public preview')
    files = {name: read_source(root, root / 'web' / name) for name in sorted(WEB_ASSETS)}
    labels = {'chrome': 'Google Chrome', 'equicord': 'Equibop + Equicord',
              'edge': 'Microsoft Edge', 'firefox': 'Firefox', 'vencord': 'Vencord',
              'betterdiscord': 'BetterDiscord', 'brave': 'Brave',
              'vivaldi': 'Vivaldi', 'opera-gx': 'Opera GX'}
    kinds = {'chrome': 'Native theme ZIP', 'equicord': 'Standalone CSS',
             'edge': 'Original Chromium ZIP, reused candidate', 'firefox': 'Unsigned static-theme XPI',
             'vencord': 'Standalone CSS', 'betterdiscord': 'Standalone CSS',
             'brave': 'Original Chromium ZIP, reused candidate',
             'vivaldi': 'Native settings JSON ZIP', 'opera-gx': 'Paired native color-hint ZIP'}
    groups = {platform: [] for platform in labels}
    for download in manifest['downloads']:
        name, platform, path = download['name'], download['platform'], download['path']
        label, kind = labels[platform], kinds[platform]
        version = download['version']
        record = next(r for r in manifest['files'] if r['path'] == path)
        appearances = ('Clair', 'Obscur') if platform == 'opera-gx' else (name,)
        guide_links = ' '.join(
            f'<a class="guide-link" href="#{guide_anchor(platform, appearance)}">'
            f'{appearance} installation, switching and removal</a>' for appearance in appearances)
        groups[platform].append(
            f'<article id="{platform}-{"paired" if platform == "opera-gx" else name.lower()}" class="download-card" data-package-bytes="{record["bytes"]}"><p class="eyebrow">Preview {version}</p>'
            f'<h4>{name}</h4><a class="button" download href="downloads/{path}">'
            f'Download {name} for {label}</a><small>{kind}, {record["bytes"]:,} bytes. '
            f'Native acceptance pending.</small><p>{guide_links}</p></article>'
        )
    sources = source_files(root)
    if _digest(_json_bytes(json.loads(sources['tokens.json'].decode('utf-8')))) != tokens_digest:
        raise ValueError('Source tokens differ from the verified artifact snapshot')
    if _digest(_json_bytes(json.loads(sources['tokens-monochrome.json'].decode('utf-8')))) != identity_digest:
        raise ValueError('Source monochrome tokens differ from the preview identity snapshot')
    license_text = normalize_license(sources['LICENSE'])
    license_bytes = license_text.encode('utf-8')
    license_comment = ('/*\n' + license_text + '*/\n').encode('utf-8')
    for name in ('Clair', 'Obscur'):
        if (snapshot[f'chrome/{name.lower()}/LICENSE.txt'] != license_bytes
                or license_comment not in snapshot[f'equicord/{name}.theme.css']):
            raise ValueError('Source license differs from the verified theme package grants')
        if (snapshot[f'firefox/{name.lower()}/LICENSE.txt'] != license_bytes
                or any(license_comment not in snapshot[f'{client}/{name}-{label}.theme.css']
                       for client, label in (('vencord', 'Vencord'), ('betterdiscord', 'BetterDiscord')))):
            raise ValueError('Source license differs from the portability package grants')
    for path in ('vivaldi/LICENSE.txt', 'opera-gx/LICENSE.txt'):
        if snapshot[path] != license_bytes:
            raise ValueError('Source license differs from the browser candidate grants')
    if license_comment not in snapshot[CLAIR_EQUICORD_FOCUS_PATH]:
        raise ValueError('Source license differs from the verified Clair focus package grant')
    icon_files = render_icons(identity_document)
    icon_manifest = json.loads(icon_files['manifest.json'])
    catalog = icon_manifest['catalog']
    identifiers = [entry['id'] for entry in catalog]
    if (identifiers != icon_manifest['functions'] or len(identifiers) != len(set(identifiers))
            or any(entry.get('kind') not in ('app', 'function') or not entry.get('label') for entry in catalog)
            or {path for path in icon_files if path.endswith('.svg')} != {
                f'{appearance}/{identifier}.svg' for appearance in ('Clair', 'Obscur') for identifier in identifiers}):
        raise ValueError('Icon catalog differs from the rendered artwork inventory')
    icon_license_comment = b'<!--\n' + license_bytes + b'\n-->'
    for path, payload in icon_files.items():
        if path.endswith('.svg') and icon_license_comment not in payload:
            raise ValueError('Source license differs from the generated icon grant')
        files[f'icons/{path}'] = payload
    icon_files['LICENSE.txt'] = sources['LICENSE']
    files['icons/LICENSE.txt'] = sources['LICENSE']
    files[ICON_ARCHIVE] = _zip_bytes(icon_files)
    for revision, archive in (('0.9.0', EVERYDAY_ICON_ARCHIVE), ('0.8.0', BROAD_ICON_ARCHIVE), ('0.7.0', COMPANION_ICON_ARCHIVE), ('0.6.0', MONOCHROME_ICON_ARCHIVE), ('0.5.0', THIRD_APP_ICON_ARCHIVE), ('0.4.0', SECOND_APP_ICON_ARCHIVE), ('0.3.0', FIRST_APP_ICON_ARCHIVE),
                              ('0.2.0', PREVIOUS_ICON_ARCHIVE), ('0.1.0', LEGACY_ICON_ARCHIVE)):
        retained_icons = render_icons(identity_document if revision in ('0.6.0', '0.7.0', '0.8.0', '0.9.0') else document, version=revision)
        for path, payload in retained_icons.items():
            if path.endswith('.svg') and icon_license_comment not in payload:
                raise ValueError('Source license differs from the generated icon grant')
        retained_icons['LICENSE.txt'] = sources['LICENSE']
        files[archive] = _zip_bytes(retained_icons)
    files[ICON_CHECKSUMS] = (
        ''.join(f'{_digest(files[path])}  {Path(path).name}\n'
                for path in (ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                             PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE)).encode()
    )
    icon_cards = {'app': [], 'function': []}
    for entry in catalog:
        function, label, kind = entry['id'], entry['label'], entry['kind']
        figures = ''.join(
            f'<figure><img src="icons/{appearance}/{html.escape(function, quote=True)}.svg" '
            f'alt="{html.escape(appearance + " " + label + " icon", quote=True)}" '
            f'width="512" height="512" decoding="async">'
            f'<figcaption>{appearance}</figcaption></figure>'
            for appearance in ('Clair', 'Obscur')
        )
        assignment = (
            f'<p class="muted"><a href="{html.escape(entry["store_url"], quote=True)}" rel="noreferrer">'
            f'Google Play listing</a><br><code>{html.escape(entry["android_package"])}</code></p>'
            if kind == 'app' else ''
        )
        icon_cards[kind].append(
            f'<article class="icon-card" data-icon-function="{html.escape(function, quote=True)}" '
            f'data-icon-kind="{kind}"><h4>{html.escape(label)}</h4>'
            f'<div class="icon-pair">{figures}</div>{assignment}</article>'
        )
    icon_gallery = ''.join(
        f'<section aria-labelledby="icons-{kind}-heading"><h3 id="icons-{kind}-heading">{heading}</h3>'
        f'<div class="icon-gallery">{"".join(icon_cards[kind])}</div></section>'
        for kind, heading in (('app', 'Named apps'), ('function', 'General functions'))
    )
    identity = source_identity(root, sources, expected_revision)
    terminal_files = render_terminal(document)
    if terminal_files['LICENSE.txt'] != license_bytes:
        raise ValueError('Source license differs from the generated Terminal grant')
    files.update({f'terminal/{name}': payload for name, payload in terminal_files.items()})
    files['terminal/installation.md'] = sources['docs/windows-terminal.md']
    terminal_cards = []
    foreground_exceptions = json.loads(terminal_files['manifest.json'])['foreground_exceptions']
    for name, scheme in zip(('Clair', 'Obscur'), json.loads(terminal_files[TERMINAL_FRAGMENT])['schemes']):
        samples = []
        for index, field in enumerate(ANSI_FIELDS):
            label = ('Bright ' + field[6:].lower()) if field.startswith('bright') else field.title()
            partner = ('black' if name == 'Clair' else 'white') if field in foreground_exceptions[name] else None
            background = scheme[partner] if partner else scheme['background']
            context = f'on {partner}' if partner else 'on default'
            samples.append(
                f'<div class="terminal-slot" data-ansi="{field}"><p>{index}: {label}</p>'
                f'<code style="color:{scheme[field]};background:{background}">Aa 0123</code>'
                f'<small>{context}</small></div>'
            )
        terminal_cards.append(
            f'<article class="terminal-palette" data-palette="{name}" '
            f'style="background:{scheme["background"]};color:{scheme["foreground"]}">'
            f'<h3>{name}</h3><p>Scheme: <code>{html.escape(scheme["name"])}</code></p>'
            f'<div class="terminal-swatches">{"".join(samples)}</div></article>'
        )
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
            .replace('{{SOURCE_DESCRIPTION}}', source_description)
            .replace('{{ICON_GALLERY}}', icon_gallery)
            .replace('{{ICON_ARCHIVE}}', ICON_ARCHIVE)
            .replace('{{EVERYDAY_ICON_ARCHIVE}}', EVERYDAY_ICON_ARCHIVE)
            .replace('{{BROAD_ICON_ARCHIVE}}', BROAD_ICON_ARCHIVE)
            .replace('{{COMPANION_ICON_ARCHIVE}}', COMPANION_ICON_ARCHIVE)
            .replace('{{MONOCHROME_ICON_ARCHIVE}}', MONOCHROME_ICON_ARCHIVE)
            .replace('{{THIRD_APP_ICON_ARCHIVE}}', THIRD_APP_ICON_ARCHIVE)
            .replace('{{SECOND_APP_ICON_ARCHIVE}}', SECOND_APP_ICON_ARCHIVE)
            .replace('{{FIRST_APP_ICON_ARCHIVE}}', FIRST_APP_ICON_ARCHIVE)
            .replace('{{PREVIOUS_ICON_ARCHIVE}}', PREVIOUS_ICON_ARCHIVE)
            .replace('{{LEGACY_ICON_ARCHIVE}}', LEGACY_ICON_ARCHIVE)
            .replace('{{ICON_CHECKSUMS}}', ICON_CHECKSUMS)
            .replace('{{TERMINAL_SPECIMENS}}', '\n'.join(terminal_cards))
            .replace('{{TERMINAL_ARCHIVE}}', f'terminal/{TERMINAL_ARCHIVE}')
            .replace('{{TARGET_OPTIONS}}', '\n'.join(
                f'<option value="{html.escape(platform, quote=True)}">{html.escape(label)}</option>'
                for platform, label in labels.items() if groups[platform]))
            .replace('{{LOCAL_GUIDES}}', render_guides(sources['docs/installation.md'], manifest)))
    for platform, cards in groups.items():
        text = text.replace('{{' + platform.upper().replace('-', '_') + '_CARDS}}', '\n'.join(cards))
    files['index.html'] = text.encode()
    css = []
    for weight, style, full, postscript in FACES:
        css.append(f'@font-face {{font-family:"Clair Obscur Inter";src:local("{full}"),local("{postscript}");font-weight:{weight};font-style:{style};font-display:swap;}}')
    for name, tokens in identity_document['themes'].items():
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
    files['LICENSE'] = sources['LICENSE']
    files['verify_preview.py'] = sources['verify_preview.py']
    files['portable-verification.md'] = sources['docs/portable-verification.md']
    files['source.zip'] = _zip_bytes(sources)
    source_digest = hashlib.sha256(files['source.zip']).hexdigest()
    files['source-SHA256SUMS'] = f'{source_digest}  source.zip\n'.encode()
    # GitHub release assets share one flat directory. The build-tree checksums
    # remain separate because their nested paths would not verify those downloads.
    release_hashes = {}
    for item in manifest['downloads']:
        name = Path(item['path']).name
        digest = hashlib.sha256(snapshot[item['path']]).hexdigest()
        if name in release_hashes and release_hashes[name] != digest:
            raise ValueError('Distinct downloads must not collide in a flat release directory')
        release_hashes[name] = digest
    release_hashes['artifact-manifest.json'] = hashlib.sha256(files['downloads/artifact-manifest.json']).hexdigest()
    release_hashes['source.zip'] = source_digest
    files['release-SHA256SUMS'] = ''.join(
        f'{digest}  {name}\n' for name, digest in sorted(release_hashes.items())
    ).encode()
    source = {**identity, 'archive': 'source.zip', 'sha256': source_digest}
    release = {'version': version, 'source_url': f'{release_url}/source.zip',
               'checksums_url': f'{release_url}/release-SHA256SUMS'}
    # Finish the extracted directory before hashing its external archive. Its
    # own page has no download link to an archive deliberately absent inside it.
    portable = dict(files)
    portable_text = text.replace('{{PORTABLE_DELIVERY}}',
        '<p id="portable-delivery" class="muted">This is the extracted portable preview. '
        'Open <code>index.html</code> and keep the complete directory together when moving it. '
        'Theme files are already included at the local paths shown beside each package. '
        'Use those files for the target procedure. A browser may save a local archive but '
        'display a CSS file instead of downloading another copy. Return to this page after viewing it. '
        'Palette specimens and target procedures remain local. '
        'Online references need a network connection. '
        'Optional directory verification needs Python 3.11 or later: '
        '<code>python -I -S -B &quot;verify_<wbr>preview.<wbr>py&quot; &quot;.&quot;</code>. '
        'Read <a href="portable-verification.md">portable verification instructions</a> '
        'for named discrepancies and the limits of included-manifest consistency. '
        '<a href="site-manifest.json">Portable directory manifest</a>.</p>')
    for path in sorted({item['path'] for item in manifest['downloads']}):
        local_path = html.escape('downloads/' + path, quote=True)
        pattern = rf'(<a\b[^>]*\bdownload\b[^>]*href="{re.escape(local_path)}"[^>]*>)([^<]*)(</a>)'
        portable_text = re.sub(pattern, lambda match: (
            match[1] + match[2].replace('Download ', 'Open included ', 1) + match[3]
            + f'<small class="local-package-path">Included file: <code>{local_path}</code>.</small>'
        ), portable_text)
    portable['index.html'] = portable_text.encode()
    portable['site-manifest.json'] = site_manifest(portable, source, release, {'kind': 'portable-kit'})
    files[PORTABLE_ARCHIVE] = _zip_bytes(portable)
    portable_digest = _digest(files[PORTABLE_ARCHIVE])
    files[PORTABLE_CHECKSUMS] = f'{portable_digest}  {PORTABLE_ARCHIVE}\n'.encode()
    files['index.html'] = text.replace('{{PORTABLE_DELIVERY}}',
        f'<p id="portable-delivery" class="muted"><a id="portable-preview" href="{PORTABLE_ARCHIVE}" download>'
        'Download the portable preview kit</a> <span aria-hidden="true">/</span> '
        f'<a id="portable-checksums" href="{PORTABLE_CHECKSUMS}" download>Kit checksum</a>. '
        'Extract the complete ZIP, then open <code>index.html</code>. Keep the extracted directory '
        'together when moving it. The specimens, theme files and target procedures work offline. '
        'Python is optional and needed only for directory verification. '
        'The included <code>verify_<wbr>preview.<wbr>py</code> command needs Python 3.11 or later. '
        '<a href="portable-verification.md">Portable verification instructions</a> explain '
        'how to check an extracted copy against its included manifest. '
        'The kit follows the current preview source and does not change theme package versions '
        'or the original release.</p>').encode()
    files['site-manifest.json'] = site_manifest(files, source, release, {
        'kind': 'published-preview', 'portable_kit': {
            'archive': PORTABLE_ARCHIVE, 'checksums': PORTABLE_CHECKSUMS,
            'sha256': portable_digest, 'bytes': len(files[PORTABLE_ARCHIVE]),
        },
    })
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
    with _cleanup_scope(lambda: _retire_stage(stage), 'Preview staging cleanup'):
        for name, data in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'dist')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs' / 'preview')
    parser.add_argument('--expected-revision', help='Require clean source at this complete Git commit ID')
    args = parser.parse_args()
    try:
        build_preview(ROOT, args.artifacts, args.output, args.expected_revision)
    except (ValueError, OSError) as error:
        notes = ''.join(f'{note}\n' for note in getattr(error, '__notes__', ()))
        parser.exit(1, f'Preview build failed: {error}\n{notes}')
    print('Built static specimen, platform downloads, source archive and portable preview kit')


if __name__ == '__main__':
    main()
