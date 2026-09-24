# Install, switch and remove

These are local preview packages. Native Chrome and Equibop acceptance is still pending as described in [acceptance.md](acceptance.md). Keep a recoverable record of existing theme choices before changing them. Do not copy an authenticated browser profile, replace QuickCSS or remove unrelated plugins to try a theme.

## Files

| Target | Clair | Obscur |
| --- | --- | --- |
| Chrome extracted development theme | `dist/chrome/clair/` | `dist/chrome/obscur/` |
| Chrome ZIP | `dist/artifacts/Clair-Chrome-0.1.0.zip` | `dist/artifacts/Obscur-Chrome-0.1.0.zip` |
| Equicord local CSS | `dist/equicord/Clair.theme.css` | `dist/equicord/Obscur.theme.css` |

Use the hashes from the same build as the package. The Chrome ZIP contains `manifest.json`, its icon and the complete MIT grant in `LICENSE.txt`. Each standalone Equicord CSS file carries the same grant in a separate comment after its loader metadata. Retain these notices when sharing a package. A Chrome ZIP is not a signed store installation or evidence of Chrome Web Store approval.

## Build from source

From the project directory, use Python 3.11 or newer:

```powershell
python build.py --tokens tokens.json --output dist
python build.py --tokens tokens.json --output dist --check
```

The first command generates all four theme downloads. The second regenerates into a temporary staging directory and compares every output byte without rewriting `dist`. Both commands operate on files only. Neither installs a theme, opens an application or publishes anything.

The output includes `dist/artifact-manifest.json` and `dist/SHA256SUMS`. Keep them with their corresponding artifacts. The builder rejects an output tree containing foreign, modified or incomplete files instead of overwriting them. If a check reports a difference after a source edit, build into a new output directory and inspect the change. Do not manually patch generated CSS or manifests.

## Equibop with Equicord

1. In the running Equibop client, record the current native appearance, enabled local/online themes and relevant font-plugin settings. Preserve existing QuickCSS. Use Equicord's own **Open Themes Folder** control to locate the correct local folder.
2. Copy the desired `.theme.css` file into that folder and refresh the theme list if required. Do not install BetterDiscord or use a guessed folder for another client.
3. Choose native **Dark** appearance for Obscur or **Light** appearance for Clair. Temporarily disable only conflicting color themes, then enable one of the family files. Do not combine Clair and Obscur with other full color themes for acceptance testing.
4. If the installed theme card offers **Dark only** or **Light only**, assign the matching mode. The CSS also gates itself to the correct native base. An opposite base should retain its native palette rather than become a partly converted interface.
5. Read messages, search results, settings, code, links and a selected passage. Check keyboard focus and checked/unchecked switches before keeping the theme enabled. Repeat with increased native chat size or zoom, without changing Windows scaling or display calibration.

For Inter, use the official [Inter distribution](https://rsms.me/inter/). The CSS looks for installed Regular, SemiBold and Bold faces plus their italic companions. Installation of a font is separate from installation of this theme. An absent face uses fallback fonts. Reopen the client if a newly installed face is not available, and verify rendered text rather than trusting a family-name field.

A font plugin can override the theme. Compare its current settings with the intended local-font configuration. Do not defeat a plugin by adding a universal `!important` font rule. Keep any temporary change recoverable. Code, icons and other writing systems must remain legible regardless of whether Inter is installed.

To switch, disable the current family file, select the matching native appearance and enable the other file. To remove, disable the family file and restore the previous appearance and theme choices. Delete only the copied Clair/Obscur files if they are no longer needed. The theme does not need to occupy or replace QuickCSS.

## Ordinary Google Chrome

Use a separate local test profile in standard Google Chrome for the first installation. Keep sync off in that profile and do not copy cookies or profile data from the everyday profile. This isolates a theme change from existing browser choices.

1. Extract one Chrome ZIP, or use its generated directory directly. Locate the folder containing `manifest.json`.
2. Open `chrome://extensions` in the test profile, enable **Developer mode**, choose **Load unpacked** and select that folder. This is Chrome's [development installation route](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked), not a consumer store installation.
3. Inspect **Settings > Appearance** and the real browser frame. Begin with Obscur, then give Clair the same checks. Test active/inactive tabs, multiple windows, the address bar and suggestions, bookmarks, tab groups, downloads and Incognito recognition.
4. Try windowed, split-screen and maximized sizes. Use normal browser zoom for page content when needed. Page zoom does not establish a change to Chrome's native UI font or frame scaling.

Installing the other package switches the active theme in that profile. To remove it, use **Settings > Appearance > Reset to default**, Chrome's [documented removal path](https://support.google.com/chrome_webstore/answer/148695). Keep the existing everyday profile untouched until the preview has passed the intended checks.

These themes do not recolor ordinary websites, replace the new-tab page, change search or select a browser font. Chrome derives some component colors itself. A readable preview webpage does not prove that address-bar suggestions or inactive windows render correctly.

## If something looks wrong

- Confirm the exact installed package and native base before editing colors. Clair and Obscur are separate files with different mode requirements.
- In Equicord, check for another enabled full theme, QuickCSS or a font plugin. Preserve the original settings while isolating a conflict.
- If text is too small, increase the application's supported text size or zoom first. Do not compensate with a monitor color transform or fixed CSS font sizes.
- Disable the candidate and compare the same state with the native baseline. Record which surface differs, the client version and the package hash.
- Treat missing glyphs, unreadable code, invisible selection or unclear toggle state as an acceptance failure to investigate. A theme should not require losing native functionality to look consistent.

No display brightness, HDR, Auto HDR, ICC association or monitor setting needs to change to install these packages. Physical viewing and comfort remain separate from installation.
