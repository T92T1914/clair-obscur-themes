# Install, switch and remove

These are local preview packages. Native Chrome and Equibop acceptance is still pending as described in [acceptance.md](acceptance.md). Keep a recoverable record of existing theme choices before changing them. Do not copy an authenticated browser profile, replace QuickCSS or remove unrelated plugins to try a theme.

## Files

| Target | Clair | Obscur |
| --- | --- | --- |
| Chrome extracted development theme | `dist/chrome/clair/` | `dist/chrome/obscur/` |
| Chrome ZIP | `dist/artifacts/Clair-Chrome-0.1.1.zip` | `dist/artifacts/Obscur-Chrome-0.1.1.zip` |
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

1. In the running Equibop client, privately record the current native appearance, enabled local/online themes, their activation modes, zoom/chat size and relevant font-plugin settings. Preserve existing QuickCSS separately without replacing its live contents. Do not export account or session data.
2. In Equicord's Themes settings, use **Open Themes Folder** to locate the actual loader directory. Copy the desired `.theme.css` file into that folder. If a file with the same name exists, compare its version and preserve it before replacement. Upstream also provides **Load missing Themes** to refresh the list. If your client does not show these controls, stop before guessing a folder. The labels are established by the [upstream controls](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/components/settings/tabs/themes/QuickActions.tsx), not by completed native acceptance here. Do not install BetterDiscord or switch clients.
3. Choose native **Dark** appearance for Obscur or **Light** appearance for Clair. Temporarily disable only conflicting color themes, then enable one of the family files. Do not combine Clair and Obscur with other full color themes for acceptance testing.
4. If the installed theme card offers **Dark only** or **Light only**, assign the matching mode. The CSS also gates itself to the correct native base. An opposite base should retain its native palette rather than become a partly converted interface.
5. Read existing non-sensitive messages, search results, settings, code, links and a selected passage. Check keyboard focus and checked/unchecked switches before keeping the theme enabled. No test message or private conversation is required. Repeat with increased native chat size or zoom, without changing Windows scaling or display calibration. Test Obscur first and give Clair the same coverage.

For Inter, use the official [Inter distribution](https://rsms.me/inter/) and the supported [Windows font installation procedure](https://support.microsoft.com/en-us/windows/experience/personalization/manage-fonts-in-windows). The CSS looks for installed Regular, SemiBold and Bold faces plus their italic companions. Installation of a font is separate from installation of this theme. Copying a font file or finding a registry entry does not prove that the current application can use it. Confirm it appears in Windows' font settings, then reopen the affected client when convenient if its font list is stale. Verify actual rendered text rather than trusting a family-name field.

An absent face uses fallback fonts so the interface remains readable. That fallback does not satisfy Inter acceptance. The [strict installed-font check](development.md) and [investigation record](acceptance.md#installed-font-investigation) keep those outcomes separate. Do not remove working fonts or clear global caches merely because a specimen falls back.

A font plugin can override the theme. Compare its current settings with the intended local-font configuration. Do not defeat a plugin by adding a universal `!important` font rule. Keep any temporary change recoverable. Code, icons and other writing systems must remain legible regardless of whether Inter is installed.

To switch, disable the current family file, select the matching native appearance and enable the other file. Switch back once to check both directions. To remove, disable both family files and restore the previous native appearance, theme choices, activation modes, zoom and any font settings you changed. Confirm that the original appearance returns. Delete only the copied Clair/Obscur files if they are no longer needed. The theme does not need to occupy or replace QuickCSS.

## Ordinary Google Chrome

Use a [separate local test profile](https://support.google.com/chrome/answer/2364824?hl=en) in standard Google Chrome for the first installation. Add it from the profile menu, continue without signing in and keep sync off. Do not import or copy data from the everyday profile. Record the test profile's initial appearance. This isolates the theme change from existing browser choices.

1. Extract one Chrome ZIP, or use its generated directory directly. Locate the folder containing `manifest.json`.
2. Open `chrome://extensions` in the test profile, enable **Developer mode**, choose **Load unpacked** and select that folder. This is Chrome's [development installation route](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked), not a consumer store installation. If Chrome rejects the package or the control is unavailable, retain the exact error. Do not change browser policy or switch to another browser to obtain a pass.
3. Inspect **Settings > Appearance** and the real browser frame. Begin with Obscur, then give Clair the same checks. Test active/inactive tabs, multiple windows, the address bar and suggestions, bookmarks, tab groups, downloads and Incognito recognition.
4. Try windowed, split-screen and maximized sizes. Use normal browser zoom for page content when needed. Page zoom does not establish a change to Chrome's native UI font or frame scaling.

Installing the other package should switch the active theme in that profile. Confirm the resulting appearance instead of treating the click as proof. Switch back once to test both directions. To remove it, use **Settings > Appearance > Reset to default**, Chrome's [documented removal path](https://support.google.com/chrome_webstore/answer/148695). Confirm the candidate is gone, restore any test-profile color choice recorded earlier and close the test windows. Do not delete a profile containing data you want to keep. Keep the everyday profile untouched until the preview has passed the intended checks.

These themes do not recolor ordinary websites, replace the new-tab page, change search or select a browser font. Chrome derives some component colors itself. A readable preview webpage does not prove that address-bar suggestions or inactive windows render correctly.

## If something looks wrong

- Confirm the exact installed package and native base before editing colors. Clair and Obscur are separate files with different mode requirements.
- In Equicord, check for another enabled full theme, QuickCSS or a font plugin. Preserve the original settings while isolating a conflict.
- If text is too small, increase the application's supported text size or zoom first. Do not compensate with a monitor color transform or fixed CSS font sizes.
- Disable the candidate and compare the same state with the native baseline. Record which surface differs, the client version and the package hash.
- Treat missing glyphs, unreadable code, invisible selection or unclear toggle state as an acceptance failure to investigate. A theme should not require losing native functionality to look consistent.

No display brightness, HDR, Auto HDR, ICC association or monitor setting needs to change to install these packages. Physical viewing and comfort remain separate from installation.

## Record a useful native result

For each theme and application, record the application version, theme version or hash, whether it loaded, whether switching worked and whether restoration worked. Name any unreadable or ambiguous control. The [acceptance checklist](acceptance.md#native-acceptance-checklist) supplies the remaining scenarios.

Human-operated checks are recorded as user-performed tests. Inspected screenshots are separate evidence of the visible state they capture. Where the client already exposes supported DevTools, inspect actual rendered font faces for non-sensitive regular, semibold, bold and italic samples. A declared `font-family` or resemblance to Inter does not establish the rendered face. Missing diagnostics leave that font check unverified.
