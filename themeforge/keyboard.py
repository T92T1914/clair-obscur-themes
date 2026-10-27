"""A manual keyboard companion, separate from native theme packages."""
from __future__ import annotations

import html

from themeforge.build import _digest, _json_bytes, _zip_bytes
from themeforge.tokens import validate

VERSION = '0.1.0'
ARCHIVE = f'Clair-Obscur-Keyboard-Companion-{VERSION}.zip'
BACKGROUNDS = {
    'Clair': ('Clair-Gboard-Background.png', 7973, 'da5f4f92115ed5453a57c61d30221782246cec7de9ba70cdf8efeaa5da05f347'),
    'Obscur': ('Obscur-Gboard-Background.png', 6177, '633b9b88e1d2967c755519a84b1845f0d0ba8f392a4cca0715ac77df773b19d6'),
}
ROLES = {
    'keyboard_field': 'canvas', 'ordinary_key': 'control', 'legend': 'text',
    'secondary_legend': 'muted', 'suggestion_toolbar': 'panel',
    'enter_search': 'accent', 'enter_search_legend': 'on_accent',
    'pressed': 'hover', 'selected': 'selected', 'boundary': 'border',
    'focus': 'focus', 'disabled_legend': 'disabled',
}


def render_keyboard(document: dict, backgrounds: dict[str, bytes], guide: bytes, license_bytes: bytes) -> dict[str, bytes]:
    """Pin reused assets; derive design values from the shared monochrome roles."""
    validate(document)
    if set(backgrounds) != set(BACKGROUNDS):
        raise ValueError('Expected exactly the Clair and Obscur keyboard backgrounds')
    files = {}
    for appearance, (filename, size, digest) in BACKGROUNDS.items():
        payload = backgrounds[appearance]
        if len(payload) != size or _digest(payload) != digest:
            raise ValueError(f'{appearance}: keyboard background differs from the accepted original')
        if document['themes'][appearance]['canvas'] != ('#ffffff' if appearance == 'Clair' else '#000000'):
            raise ValueError('Keyboard backgrounds require the accepted pure monochrome canvas')
        files[f'backgrounds/{filename}'] = payload
    files['installation.md'] = guide
    files['LICENSE.txt'] = license_bytes
    files['palette-reference.json'] = _json_bytes({
        'schema_version': 1, 'version': VERSION,
        'kind': 'manual configuration reference, not a native import file',
        'themes': {name: {role: values[token] for role, token in ROLES.items()}
                   for name, values in document['themes'].items()},
        'support': {
            'Gboard': 'Optional background pixels only; native theme and controls take precedence.',
            'Samsung Keyboard': 'Manual Theme Park/Keys Cafe controls vary by region and module version.',
            'Samsung system': 'Separate manual Theme Park palette/Quick panel reference; not device-wide coverage.',
        },
    })
    files['manifest.json'] = _json_bytes({
        'schema_version': 1, 'generator': 'clair-obscur-keyboard-companion', 'version': VERSION,
        'tokens_sha256': _digest(_json_bytes(document)),
        'status': 'maintained assets and manual recipes; native application unverified',
        'backgrounds': {name: {
            'path': f'backgrounds/{spec[0]}', 'bytes': spec[1], 'sha256': spec[2],
            'dimensions': [2048, 1024], 'mode': 'RGB', 'opaque': True,
            'color': document['themes'][name]['canvas'],
            'provenance': 'Original solid background prepared 2026-10-22, reused byte for byte',
        } for name, spec in BACKGROUNDS.items()},
        'files': {path: {'bytes': len(data), 'sha256': _digest(data)} for path, data in sorted(files.items())},
        'font_binaries_included': False, 'native_import_included': False,
    })
    files['SHA256SUMS'] = ''.join(f'{_digest(data)}  {path}\n' for path, data in sorted(files.items())).encode()
    files[ARCHIVE] = _zip_bytes(files)
    files['bundle-SHA256SUMS'] = f'{_digest(files[ARCHIVE])}  {ARCHIVE}\n'.encode()
    return files


def keyboard_section(document: dict) -> str:
    """Static platform/appearance routes survive without the optional chooser."""
    validate(document)
    cards = []
    for platform in ('Gboard', 'Samsung Keyboard'):
        platform_id = 'gboard' if platform == 'Gboard' else 'samsung'
        for appearance in ('Clair', 'Obscur'):
            slug = appearance.lower()
            rows = []
            for row in ('1234567890', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
                row_class = (' keyboard-row-home' if row == 'asdfghjkl' else
                             ' keyboard-row-numbers' if row == '1234567890' else '')
                keys = ''.join(f'<span class="keyboard-key">{letter}</span>' for letter in row)
                if row == 'zxcvbnm':
                    keys = '<span class="keyboard-key keyboard-modifier" data-keyboard-modifier="shift">⇧</span>' + keys + '<span class="keyboard-key keyboard-modifier" data-keyboard-modifier="backspace">⌫</span>'
                rows.append(f'<div class="keyboard-row{row_class}">{keys}</div>')
            figure = (f'<figure class="keyboard-reference" data-palette="{appearance}">'
                f'<div role="img" aria-label="Illustrative {appearance} keyboard with number row, an example selected suggestion, Shift, Backspace, numeric/symbol mode, Space, punctuation and Enter. Not a native screenshot or typing control.">'
                '<div class="keyboard-drawing" aria-hidden="true"><div class="keyboard-toolbar"><span>Tools</span><span>Design reference</span><span>Settings</span></div>'
                '<div class="keyboard-suggestions"><span>quiet</span><span class="keyboard-suggestion-current">clear</span><span>simple</span></div>'
                + ''.join(rows) + '<div class="keyboard-row"><span class="keyboard-key keyboard-modifier keyboard-mode" data-keyboard-modifier="mode">123</span><span class="keyboard-key">,</span>'
                '<span class="keyboard-key keyboard-space">Space</span><span class="keyboard-key">.</span><span class="keyboard-key keyboard-action" data-keyboard-modifier="enter">↵</span></div>'
                '<div class="keyboard-state-samples"><span class="keyboard-state keyboard-pressed">Pressed</span><span class="keyboard-state keyboard-selected">Selected</span>'
                '<span class="keyboard-state keyboard-focused">Focus</span><span class="keyboard-state keyboard-disabled">Unavailable</span></div></div></div>'
                '<figcaption>Illustrative selected suggestion, with no automatic correction implied. Native layout, touch targets and typography stay unchanged.</figcaption></figure>')
            if platform_id == 'gboard':
                filename = BACKGROUNDS[appearance][0]
                action = (f'<p><img class="keyboard-background" src="keyboard/backgrounds/{filename}" width="2048" height="1024" alt="Solid {"white" if appearance == "Clair" else "black"} optional background" data-keyboard-background="{slug}"></p>'
                    f'<a class="button" data-keyboard-download="{slug}" href="keyboard/backgrounds/{filename}" download>Download {appearance} background PNG</a>'
                    f'<p class="keyboard-asset-status" data-keyboard-asset-status="{slug}" role="status">Optional opaque 2048 × 1024 background. Native plain themes are preferred when suitable.</p>'
                    '<p>The image controls background pixels only. Key shapes, suggestions, Enter accents, live fonts and correction remain Gboard-owned.</p>')
            else:
                action = ('<p>Manual recipe only. Use available Theme Park/Keys Cafe color controls. Individual key, background and state controls depend on module version.</p>'
                    '<p>No Samsung theme file or importer is included. Keep the existing layout, effects and sounds.</p>')
            cards.append(f'<article class="keyboard-card" data-keyboard-platform="{platform_id}" data-keyboard-appearance="{appearance}" id="keyboard-{platform_id}-{slug}">'
                f'<h3>{platform}: {appearance}</h3>{figure}{action}<p><a href="#keyboard-{platform_id}-recipe">{platform} setup and restoration recipe</a></p></article>')
    swatches = []
    for appearance in ('Clair', 'Obscur'):
        values = document['themes'][appearance]
        items = ''.join(f'<li><span>{html.escape(role.replace("_", " "))}</span> <code translate="no">{values[token]}</code></li>' for role, token in ROLES.items())
        swatches.append(f'<details class="keyboard-palette"><summary>{appearance} design values and state roles</summary><ul>{items}</ul></details>')
    return ('<section id="keyboards" aria-labelledby="keyboards-heading"><p class="eyebrow">Keyboard companion 0.1.0</p>'
        '<h2 id="keyboards-heading">A matching keyboard, within its own controls.</h2>'
        '<p class="lead">Choose a platform and compare Clair and Obscur. These are design references and manual recipes, separate from the icon packs and page appearance.</p>'
        '<p class="status">Illustrations, not native screenshots. The browser requests locally installed Inter and keeps its fallback. Neither establishes a phone font, typing performance or completed theme application.</p>'
        '<p>Letters carry the main visual weight in this reference. The quieter number row and outlined utility keys stay readable, while bold text and an underline identify an example suggestion. These are illustration choices, not extra Gboard or Samsung controls. <a href="https://github.com/T92T1914/clair-obscur-themes/blob/main/docs/art-direction.md">Design decisions and platform limits</a>.</p>'
        '<form id="keyboard-chooser" class="paper" hidden><div class="chooser-controls">'
        '<label for="keyboard-platform">Keyboard platform<select id="keyboard-platform"><option value="gboard">Gboard</option><option value="samsung">Samsung Keyboard</option></select></label>'
        '<label for="keyboard-appearance">Keyboard design appearance<select id="keyboard-appearance"><option value="both">Compare both</option><option value="Clair">Clair</option><option value="Obscur">Obscur</option></select></label></div>'
        '<p id="keyboard-choice-status" role="status"></p></form>'
        '<noscript><p>All four platform/appearance references and their fixed download links remain available. Page appearance does not change an asset.</p></noscript>'
        '<div class="keyboard-grid">' + ''.join(cards) + '</div>' + ''.join(swatches) +
        '<p>Illustrative state samples combine labels and outlines with fills. Preserve native focus and semantic states. The illustration is not an interactive keyboard. Apply only controls your host exposes.</p>'
        '<table class="keyboard-support"><caption>Supported controls and design-only roles</caption><thead><tr><th scope="col">Role</th><th scope="col">Gboard</th><th scope="col">Samsung Keyboard</th></tr></thead><tbody>'
        '<tr><th scope="row">Field background</th><td>Supported native theme or optional photo pixels.</td><td>Documented background control, conditional on installed module.</td></tr>'
        '<tr><th scope="row">Ordinary key colors</th><td>Native theme-owned. The photo does not set individual key colors.</td><td>Documented per-key colors. Available editors vary by version.</td></tr>'
        '<tr><th scope="row">Secondary labels, suggestions, toolbar, Enter legend</th><td>Native-owned, outside this asset.</td><td>Individual editors not established here. Reference-only unless exposed.</td></tr>'
        '<tr><th scope="row">Pressed, selected, focus, disabled</th><td>Preserve native states.</td><td>Preserve native states. Independent editors not promised.</td></tr>'
        '<tr><th scope="row">Font, layout, correction</th><td colspan="2">Separate native settings. Preserve the existing choices and learned words.</td></tr></tbody></table>'
        '<div class="keyboard-recipes">'
        '<article id="keyboard-gboard-recipe"><h3>Gboard: native theme first</h3><ol><li>Record the current theme, key-border, font and layout choices. Preserve language, number row, learned words and correction settings.</li>'
        '<li>Open Gboard settings, then Theme. Prefer an available native plain light or dark theme. For an optional custom background, use the matching solid PNG and the photo route, then inspect before Apply.</li>'
        '<li>Check the existing keyboard on both relevant displays. Manual selection may be needed between custom photo themes. Restore the recorded theme and borders if unsuitable. Do not clear keyboard data.</li></ol>'
        '<p><a href="https://support.google.com/gboard/answer/6102154?hl=en">Google: change Gboard theme</a>. No theme-file importer or automatic custom-photo switching is promised.</p></article>'
        '<article id="keyboard-samsung-recipe"><h3>Samsung Keyboard: a separate draft</h3><ol><li>Record module/One UI versions, current keyboard theme and saved layouts. Keep the default keyboard, key positions, effects and sounds unchanged.</li>'
        '<li>Where available, use Theme Park Keyboard to create a new separate design, or Keys Cafe style controls with Theme Park. Set background and key colors using the reference values your version exposes. Keep readable native state cues.</li>'
        '<li>Inspect legends, suggestions, special keys, pressed/selected states and both displays before saving or applying. Retain the working theme and restore it if unsuitable.</li></ol>'
        '<p>Samsung regional guides differ: <a href="https://www.samsung.com/co/support/mobile-devices/change-keyboard-background/">Colombia, October 8, 2026</a> and <a href="https://www.samsung.com/au/support/mobile-devices/customise-keyboard-background/">Australia, September 9, 2026</a>. Exact routes and control coverage depend on region/version.</p></article>'
        '<article id="keyboard-system-recipe"><h3>Samsung system palette: configuration reference</h3>'
        '<p>Keep this separate from icon assignment and keyboard styling. Where your Theme Park version exposes an overall palette or independent Quick panel theme, start with the matching light/dark canvas and opposite foreground, neutral gray boundaries and visible native active/focus cues. Inspect notification-panel buttons and brightness controls individually.</p>'
        '<p>This is a manual target, not a complete Samsung theme or guarantee across applications, notifications or lock screens. <a href="https://www.samsung.com/in/support/mobile-devices/explore-good-lock-and-how-its-applications-enhance-your-samsung-device/">Samsung India describes Theme Park and Quick Setting themes</a>. Restore the recorded theme if any necessary state loses distinction.</p></article></div>'
        '<p>Font and correction remain separate. Inter needs authentic compatible provenance, actual selection and observed live glyphs. A prior bounded search did not establish a compatible listing, which does not prove global unavailability. Appearance work does not fix or validate autocorrection.</p>'
        f'<p class="chooser-actions"><a id="keyboard-bundle" class="button" href="keyboard/{ARCHIVE}" download>Download companion 0.1.0 bundle</a>'
        '<a href="keyboard/bundle-SHA256SUMS" download>Bundle checksum</a><a href="keyboard/installation.md">Complete setup and restoration guide</a><a href="keyboard/SHA256SUMS" download>Extracted files checksums</a><a href="keyboard/manifest.json">Companion manifest</a>'
        '<a href="#current-source">Current maintained source</a></p>'
        '<p class="muted">The ZIP contains backgrounds and manual references, not a native keyboard/system-theme import or font installer. Phone application, switching, restart and restoration remain unverified.</p></section>')
