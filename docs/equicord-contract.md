# Equibop and Equicord styling contract

Clair and Obscur are local CSS themes for Equibop with Equicord. They use the client's existing layout, theme loader and settings. They do not install a different client, modify application binaries or add account behavior. Actual application acceptance is recorded separately from the generated CSS and component fixture.

## Native base mode and installation

Use native Light appearance for Clair and native Dark appearance for Obscur. The files deliberately gate their rules to the matching native mode. Loading Clair over Dark does not turn Dark into a complete light appearance. Matching the native base preserves host-owned syntax highlighting, imagery and component states that a color file cannot comprehensively replace.

In Equicord's theme settings, use its own Open Themes Folder control. Copy the desired `.theme.css` there and refresh the local list. Disable conflicting color themes temporarily and enable one family file. Keep the original enabled-theme choices and QuickCSS so they can be restored. Do not replace QuickCSS with the distribution file. Switching back consists of disabling the family file and restoring the previous native appearance and theme choices. The exact local folder is determined by the running client, not a BetterDiscord path copied from a tutorial.

Current upstream Equicord also offers per-theme activation modes. When that control exists in the installed version, Light only and Dark only can prevent accidental cross-mode activation. The CSS gate remains effective without that feature. Activation is manual by default. No time-of-day or system-theme script is included.

## Typography and preserved behavior

Six local-only font-face aliases name Inter Regular, SemiBold and Bold, each with a genuine italic companion. Their full and PostScript names were read from official Inter 4.1 static faces. This resolves the separate Windows legacy SemiBold family without downloading a font when the theme loads. The stack falls back to installed Inter, then system UI, Segoe UI and sans-serif. The output includes no font binaries and no network font URLs.

The generator maps `--font-primary`, `--font-display` and `--font-headline`. It leaves `--font-code`, native font size, chat scaling, density, zoom and interface geometry alone. Narrow message and composer rules preserve regular body weight, strong emphasis and italic markup. The code font remains the host's monospace stack. No icon, emoji, image or language font is replaced through a universal descendant rule.

The local aliases support 400, 600 and 700. The optional 450 reading weight is not offered because these builds use verified static faces. Optical sizing is left at `auto`, which does not create a variable optical-size axis in a static font. A successful font-name query or computed font-family is not proof of actual rendered glyphs. Rendered-face inspection is an acceptance requirement.

FontLoader and similar plugins can override font variables. The inspected upstream FontLoader uses universal important declarations and can request Google Fonts. The theme does not override that plugin with a stronger universal rule or silently change its settings. A remaining plugin override must be recorded during the actual application check. Requests caused by a preexisting plugin are separate from this file's own behavior.

## Compatibility map

| Mechanism | Purpose | Maintenance boundary |
| --- | --- | --- |
| Native `.theme-light`, `.theme-dark`, `.theme-darker`, `.theme-midnight` classes | Matching mode gates | Host classes can change. Check matching and opposite native modes after Discord changes. |
| Current `--background-base-*`, `--background-surface-*`, `--text-*`, `--interactive-*` variables | Surfaces, text and controls | Public host properties are implementation interfaces, not a promised third-party theme API. |
| Retained `--background-primary`, `--background-secondary`, `--bg-*`, legacy button and mention variables | Components still using older tokens | Unused variables are harmless. They do not establish that every host component consumes them. |
| `[id^="message-content-"]` | Message emphasis and code treatment | Structural ID prefix is volatile. No mangled class substring selectors are used. |
| Contenteditable textbox role | Composer font | Semantic role is more stable than a translated label. Does not move or resize the composer. |
| `.vc-switch-*` and `--switch-*` | Equicord toggles | Confirmed in the installed Equicord renderer CSS and current upstream. Host owns checkmarks, position and disabled behavior. |
| `.vc-btn-*` and `--control-primary-*`, `--control-secondary-*` | Equicord settings buttons | Current upstream contract. Small and medium text buttons use actual 600 weight. Native danger/positive filled-button pairs remain intact. |
| `:focus-visible` | Visible keyboard focus | Existing native focus remains. The theme adds a two-pixel outline to semantic controls. |
| Forced colors and reduced motion media queries | System colors and no toggle transition | Not proof that every Discord animation or every OS accessibility setting is covered. |

Status, role and user-content colors are not globally converted to the family palette. Semantic feedback retains separate success, warning and error tokens. Essential controls use borders and native checkmarks as well as color. Code syntax highlighting remains host-owned and must be checked with the matching base mode.

## Source inspection

Inspected on 2026-09-24. These records establish source contracts and reported behavior, not successful application acceptance.

- [Equibop upstream](https://github.com/Equicord/Equibop) describes Equicord as bundled. That author description does not identify a locally installed version.
- Equicord revision `957307d5f034028bb31ab0ac52ea1a6e90b6d43a`, [theme metadata parser](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/main/themes/index.ts), reads the initial comment's name, author, description and version fields. The generated metadata uses those fields.
- The same revision's [theme application code](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/api/Themes.ts) loads enabled local files through the client's custom protocol and applies styles to supported popouts. Its own import wrapper is distinct from a theme file importing remote resources.
- Its [theme card](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/components/settings/tabs/themes/ThemeCard.tsx) exposes Always on, Light only and Dark only activation choices.
- Its [switch stylesheet](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/components/Switch.css) uses separate selected, hover, border and thumb variables. A read-only inspection of the installed renderer stylesheet found those same properties. This generator maps the variables rather than copying the component implementation.
- Its [button stylesheet](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/components/Button.css) consumes paired control background/text properties and `--font-primary`. Filled critical and positive action colors remain paired as supplied by the host.
- Its [FontLoader implementation](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/equicordplugins/fontLoader/index.tsx) establishes the override and remote-request caveat above.
- [Issue 906](https://github.com/Equicord/Equicord/issues/906), opened 2026-03-12 and closed as not planned, reports saturated toggles with a particular theme in Equibop while stock Equibop and themed Vesktop looked different. That is a firsthand report about another theme. It motivates checked, unchecked, hovered, focused and disabled toggle checks here. It does not prove this project reproduces or fixes that report.
- Public Discord app HTML was accessible during research. Direct retrieval of its linked stylesheet returned HTTP 403. No access restriction was bypassed. Current mappings are supported by Equicord source and the installed renderer's references, with remaining host coverage assessed in the application.

No upstream theme implementation was imported. These are original token mappings and scoped rules. The standalone output is declarative CSS without scripts, telemetry, remote imports or image filters.

## Acceptance boundary

Automated checks cover deterministic output, metadata structure, rejected malformed tokens, local font-face declarations, mode gates and intended preservation rules. They do not certify live message lists, search, popouts, settings, voice controls or all plugins. Check those in the actual Equibop installation using harmless settings and synthetic content, retaining private account data outside public captures. Keep missing live checks, physical HDR viewing and subjective reading comfort explicit.
