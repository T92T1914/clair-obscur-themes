# Shared roles, explicit platform mappings

This conceptual diagram shows named color/focus roles becoming versioned packages
through explicit host adapters. An inspectable webpage specimen and a matching
package hash do not establish native loading, typography, switching or removal.
Those checks belong to each application's accepted version and recorded scope.

The current preview/icon identity uses `tokens-monochrome.json`, whose provenance
records accepted source `f945342eda3196864f325312e61e3904e21e3258`. Earlier desktop
packages retain `tokens.json` and their own accepted bytes. For example, black
canvas and white text in the current Obscur specimen do not change Chrome's native
UI font. This diagram does not rebuild or recolor historical packages.

The [platform contracts](platform-portability.md) and [acceptance record](acceptance.md)
remain authoritative. New page appearance choices use optional browser storage
under `clair-obscur-preview-appearance`. First visit and no-JavaScript content
remain Obscur. Explicit Auto follows the system preference, while Clair/Obscur
remain explicit until changed. Appearance changes only presentation and preserve
filters, package selections and local-file inspection state.

## Rebuild the graphic

The editable source is [mechanism.json](mechanism.json) and
[tools/render_mechanism.py](../tools/render_mechanism.py). Install the optional
[figure requirements](requirements-figures.txt) in an isolated authoring environment.
They are not application dependencies. Supply genuine Inter Regular 400,
SemiBold 600 and Bold 700 static TTF files from one release. No font files or
machine paths are distributed.

```console
python -m pip install -r docs/requirements-figures.txt
python tools/render_mechanism.py --font-dir /path/to/Inter/extras/ttf
python tools/render_mechanism.py --check
```

`OBSCUR_FONT_DIR` is an optional alternative to the argument. The renderer checks
actual font names, weights and Latin glyph coverage, exports opaque 1800 x 800
wide and 960-pixel-wide narrow PNG/SVG editions, and rejects labels outside the canvas.
The narrow height follows actual font bounds. The current recorded edition is 960 x 1210.
Labels use at least 30 points at 100 dpi. SVG labels are outlines from those same
files. Adjacent HTML/Markdown supplies selectable text and source links.

The generated `mechanism-rendering.json` records source/adapter hashes, font
hashes, renderer versions, layout and all four output hashes. `--check` compares
committed inputs and outputs without importing the application, downloading fonts
or silently regenerating missing files. A new presentation render is not a new
application or scientific execution. Actual receiving-page image selection,
readability and visitor font fallback remain separate checks.

