# Clair and Obscur

Two appearances, built for ordinary Google Chrome and Equibop with Equicord. Clair uses warm paper surfaces and dark text. Obscur uses near-black layers, clear text and restrained blue emphasis. Both come from the visual identity of [Tornado Atlas](https://github.com/T92T1914/tornado-atlas), with the host application's layout and scaling left in place.

This is an experimental preview. Both themes have passed limited native Equibop checks for loading, matching and opposite appearance modes, switching and restoration. Obscur also installed in an isolated ordinary Chrome profile. Full interface and typography acceptance remains open, including Clair's Chrome installation and Chrome switching, restoration and cleanup. The webpage specimen is not a screenshot of either application's interface. See the [compatibility and acceptance record](docs/acceptance.md) for the inspected surfaces and remaining checks.

## Choose your theme

Open the [live preview and downloads](https://t92t1914.github.io/clair-obscur-themes/) to compare Clair and Obscur and choose a package for your application. The page includes installation and restoration steps, source and checksums. All four downloads are labeled as previews while native acceptance remains open.

| Application | Clair | Obscur | Typography |
| --- | --- | --- | --- |
| Google Chrome | Warm light browser colors | Deep neutral browser colors | Chrome keeps its native UI font |
| Equibop with Equicord | Use with native Light appearance | Use with a native dark appearance | Installed Inter 400, 600 and 700, with genuine italics |

The Chrome downloads are native color themes, not replacement browsers or website restylers. The Equicord downloads are self-contained local CSS files. They preserve code fonts, icons, emoji and language fallbacks. Neither platform's theme downloads fonts, runs scripts or collects data.

## Build and try the preview

Python 3.11 or newer is enough to build all four artifacts. From this project directory:

```powershell
python build.py
python build.py --check
python preview.py --output outputs/preview-0.1.1
```

Open `outputs/preview-0.1.1/index.html` to compare both palettes and download the matching Chrome ZIP or Equicord CSS. These commands generate a local copy. They do not update the published preview.

| Artifact | Output |
| --- | --- |
| Clair for Chrome | `dist/artifacts/Clair-Chrome-0.1.1.zip` |
| Obscur for Chrome | `dist/artifacts/Obscur-Chrome-0.1.1.zip` |
| Clair for Equicord | `dist/equicord/Clair.theme.css` |
| Obscur for Equicord | `dist/equicord/Obscur.theme.css` |
| Integrity records | `dist/SHA256SUMS` and `dist/artifact-manifest.json` |

Start with Obscur in a separate Chrome test profile or a recoverable Equicord configuration, then give Clair the same checks. In Chrome, extract the ZIP and use **Load unpacked** in `chrome://extensions`. In Equibop, use Equicord's **Open Themes Folder** control and copy the CSS there. Do not paste it over QuickCSS or install another Discord client.

The [installation and removal guide](docs/installation.md) covers the exact steps, theme conflicts, Inter, switching and restoration. Chrome uses **Settings > Appearance > Reset to default** for removal. Equicord restoration means disabling the candidate and restoring the appearance and theme selections recorded before the test. No monitor, HDR or color-profile changes are required.

## How it is built

[tokens.json](tokens.json) holds one shared palette with named roles for text, surfaces, focus and control states. Small Python generators map those roles to Chrome's native theme fields and Equicord's host variables. The build produces deterministic packages, verifies their contents and refuses to overwrite an output tree that contains unexpected or edited files.

The browser specimen exercises readable components, local font resolution, keyboard interaction, larger text and fallback behavior. It uses an isolated headless browser profile. Those tests help find mistakes in the supplied CSS and preview, but they cannot certify Chrome's tab strip, Equibop's full interface or physical HDR appearance.

Inter verification checks the actual rendered Regular, SemiBold and Bold faces and their genuine italic counterparts. Windows' normal per-user installation has now restored all six faces, and the latest strict checks passed with zero skips. Actual Equibop settings text rendered Inter Regular and Bold under both themes. The other four faces and native code/language fallback remain unverified. An earlier session activation failed after the next normal restart. Persistence after the native installation remains unverified until another normal restart is checked before any repair. The [acceptance record](docs/acceptance.md#installed-font-investigation) preserves these results and the remaining native-application checks. A readable fallback is a separate result, not a passed Inter check. The released theme files are unchanged.

See [development and verification](docs/development.md) for reproducible commands, [design](docs/design.md) for the color and typography choices, and [research](research/research.md) for the source-backed concerns behind the native checks. The [publication guide](docs/publication.md) separates a downloadable preview, native acceptance and store approval.

## Report a problem

Include the theme and application versions, native Light or Dark setting, the affected surface and the steps that reproduce it. For Equicord, mention relevant theme or font overrides without exporting your full settings. Crop private names and messages from any screenshots. A missing glyph, unreadable code block or ambiguous switch state is useful evidence even when the rest of the interface looks right.

Original source, documentation and generated theme assets use the [MIT license](LICENSE). Inter is installed separately from its [official distribution](https://rsms.me/inter/). No third-party theme implementation or font binary is bundled.
