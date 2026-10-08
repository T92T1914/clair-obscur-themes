"""Render the selected installation-document sections into the static preview."""
from __future__ import annotations

import html
import re
from pathlib import PurePosixPath


GUIDE_HEADINGS = {
    'chrome': 'Ordinary Google Chrome',
    'equicord': 'Equibop with Equicord',
    'firefox': 'Firefox',
    'edge': 'Microsoft Edge',
    'brave': 'Brave',
    'vivaldi': 'Vivaldi',
    'opera-gx': 'Opera GX',
    'vencord': 'Vencord',
    'betterdiscord': 'BetterDiscord',
}
JOURNEY_HEADINGS = ('Prerequisites and status', 'Install', 'Switch',
                    'Remove and restore', 'Fonts', 'Troubleshooting')
REPOSITORY_DOCS = 'https://github.com/T92T1914/clair-obscur-themes/blob/main/docs/'
INLINE = re.compile(r'`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^\s)]+)\)')


def guide_anchor(platform: str, appearance: str) -> str:
    return f'guide-{platform}-{appearance.lower()}'


def _inline(text: str) -> str:
    parts, cursor = [], 0
    for match in INLINE.finditer(text):
        parts.append(html.escape(text[cursor:match.start()]))
        code, strong, label, href = match.groups()
        if code is not None:
            parts.append(f'<code>{html.escape(code)}</code>')
        elif strong is not None:
            parts.append(f'<strong>{html.escape(strong)}</strong>')
        else:
            if href == '#local-client-fonts-and-fallbacks':
                href = '#guide-client-fonts'
            if re.fullmatch(r'[a-z-]+\.md(?:#[a-z-]+)?', href):
                href = REPOSITORY_DOCS + href
            if href.startswith('https://'):
                parts.append(f'<a href="{html.escape(href, quote=True)}" rel="noreferrer">'
                             f'{html.escape(label)} (online reference)</a>')
            elif re.fullmatch(r'#[a-z0-9-]+', href):
                parts.append(f'<a href="{href}">{html.escape(label)}</a>')
            else:
                raise ValueError('Unsupported installation-guide link')
        cursor = match.end()
    parts.append(html.escape(text[cursor:]))
    return ''.join(parts)


def _markdown(text: str) -> str:
    """Support the reviewed guide subset, escaping text rather than accepting HTML."""
    result = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.splitlines()
        if len(lines) == 1 and lines[0].startswith('### '):
            result.append(f'<h4>{_inline(lines[0][4:])}</h4>')
        elif all(re.match(r'\d+\. ', line) for line in lines):
            result.append('<ol>' + ''.join('<li>' + _inline(line.split('. ', 1)[1]) + '</li>'
                                          for line in lines) + '</ol>')
        elif all(line.startswith('- ') for line in lines):
            result.append('<ul>' + ''.join(f'<li>{_inline(line[2:])}</li>' for line in lines) + '</ul>')
        elif any(line.startswith(('#', '```', '|', '<')) for line in lines):
            raise ValueError('Unsupported installation-guide Markdown block')
        else:
            result.append(f'<p>{_inline(" ".join(lines))}</p>')
    return '\n'.join(result)


def render_guides(document: bytes, manifest: dict) -> str:
    """Use the same captured documentation bytes as the downloadable source archive."""
    pieces = re.split(r'^## (.+)$', document.decode('utf-8').replace('\r\n', '\n'), flags=re.MULTILINE)
    sections = {}
    for heading, body in zip(pieces[1::2], pieces[2::2]):
        if heading in sections:
            raise ValueError(f'Duplicate installation-guide section: {heading}')
        sections[heading] = body
    records = {item['path']: item for item in manifest['files']}
    result = []
    for platform, heading in GUIDE_HEADINGS.items():
        if heading not in sections:
            raise ValueError(f'Missing installation guide: {heading}')
        body = sections[heading]
        for required in JOURNEY_HEADINGS:
            if f'### {required}\n' not in body:
                raise ValueError(f'Incomplete installation guide: {heading}, {required}')
        downloads = [item for item in manifest['downloads'] if item['platform'] == platform]
        if len(downloads) != (1 if platform == 'opera-gx' else 2):
            raise ValueError(f'Installation-guide package choices differ: {platform}')
        appearances = [('Clair', downloads[0]), ('Obscur', downloads[0])] if platform == 'opera-gx' else [
            (item['name'], item) for item in downloads]
        if {name for name, _ in appearances} != {'Clair', 'Obscur'} or len(appearances) != 2:
            raise ValueError(f'Installation-guide package choices differ: {platform}')
        result.append(f'<article class="paper local-guide" id="guide-{platform}" '
                      f'aria-labelledby="guide-{platform}-heading" tabindex="-1">'
                      f'<h3 id="guide-{platform}-heading">{html.escape(heading)}</h3>')
        for appearance, item in appearances:
            record = records[item['path']]
            filename = PurePosixPath(item['path']).name
            result.append(f'<div class="guide-package" id="{guide_anchor(platform, appearance)}" tabindex="-1">'
                          f'<h4>{appearance} for {html.escape(heading)}</h4>'
                          f'<p>Package {html.escape(item["version"])}. '
                          f'<a download href="downloads/{html.escape(item["path"], quote=True)}">'
                          f'{html.escape(filename)}</a>, {record["bytes"]:,} bytes.</p>'
                          f'<p class="package-hash">SHA-256: <code>{record["sha256"]}</code></p>'
                          f'<a href="#guide-{platform}-procedure">Read the {html.escape(heading)} procedure</a></div>')
        result.extend((f'<div id="guide-{platform}-procedure" tabindex="-1">', _markdown(body), '</div>',
                       f'<p><a href="#{platform}-downloads">Return to {html.escape(heading)} downloads</a></p>', '</article>'))
    shared = sections.get('Local client fonts and fallbacks')
    if shared is None:
        raise ValueError('Missing local client font guidance')
    result.append('<article class="paper local-guide" id="guide-client-fonts" tabindex="-1">'
                  '<h3>Local client fonts and fallbacks</h3>' + _markdown(shared) + '</article>')
    return '\n'.join(result)
