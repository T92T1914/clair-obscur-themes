# Install, switch and remove

Each target below has its own prerequisites, installation, switching, removal, font and troubleshooting guidance. Read [platform portability](platform-portability.md) before testing them. The original Chrome and Equicord instructions below remain applicable to their unchanged 0.1.1 files. No native app installation or settings change is performed by the builder.

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

The first command generates thirteen distinct download files for seventeen choices. The second regenerates into a temporary staging directory and compares every output byte without rewriting `dist`. Both commands operate on files only. Neither installs a theme, opens an application or publishes anything.

The output includes `dist/artifact-manifest.json` and `dist/SHA256SUMS`. Keep them with their corresponding artifacts. The builder rejects an output tree containing foreign, modified or incomplete files instead of overwriting them. If a check reports a difference after a source edit, build into a new output directory and inspect the change. Do not manually patch generated CSS or manifests.

An interruption while switching the generated directory restores the previous build when its files and the destination remain intact. This includes a normal Ctrl+C and an error reported after a rename has taken effect. Intervening foreign files or a failed restore are preserved for inspection, with a recovery note on the original error. Do not remove a retained `.previous-*` directory or its contents before checking them. Once installation returns successfully, the new complete output remains available even if removal of the old temporary copy is interrupted. This recovery does not cover forced process termination, power loss or repeated interruptions during cleanup.

## Equibop with Equicord

### Prerequisites and status

Use an already installed Equibop client with Equicord's local theme loader. The unchanged 0.1.1 files have limited native Clair and Obscur loading, mode-gate and restoration evidence. Full client coverage, four native font faces, restart persistence and physical reading acceptance remain open. No client installation is part of this guide.

### Install

1. In the running Equibop client, privately record the current native appearance, enabled local/online themes, their activation modes, zoom/chat size and relevant font-plugin settings. Preserve existing QuickCSS separately without replacing its live contents. Do not export account or session data.
2. In Equicord's Themes settings, use **Open Themes Folder** to locate the actual loader directory. Copy the desired `.theme.css` file into that folder. If a file with the same name exists, compare its version and preserve it before replacement. Upstream also provides **Load missing Themes** to refresh the list. If your client does not show these controls, stop before guessing a folder. The labels are established by the [upstream controls](https://github.com/Equicord/Equicord/blob/957307d5f034028bb31ab0ac52ea1a6e90b6d43a/src/components/settings/tabs/themes/QuickActions.tsx), not by completed native acceptance here. Do not install BetterDiscord or switch clients.
3. Choose native **Dark** appearance for Obscur or **Light** appearance for Clair. Temporarily disable only conflicting color themes, then enable one of the family files. Do not combine Clair and Obscur with other full color themes for acceptance testing.
4. If the installed theme card offers **Dark only** or **Light only**, assign the matching mode. The CSS also gates itself to the correct native base. An opposite base should retain its native palette rather than become a partly converted interface.
5. Read existing non-sensitive messages, search results, settings, code, links and a selected passage. Check keyboard focus and checked/unchecked switches before keeping the theme enabled. No test message or private conversation is required. Repeat with increased native chat size or zoom, without changing Windows scaling or display calibration. Test Obscur first and give Clair the same coverage.

### Switch

To switch, disable the current family file, select the matching native appearance and enable the other file. Switch back once to check both directions.

### Remove and restore

To remove, disable both family files and restore the previous native appearance, theme choices, activation modes, zoom and any font settings you changed. Confirm that the original appearance returns. Delete only the copied Clair/Obscur files if they are no longer needed. The theme does not need to occupy or replace QuickCSS.

### Fonts

For Inter, use the official [Inter distribution](https://rsms.me/inter/) and the supported [Windows font installation procedure](https://support.microsoft.com/en-us/windows/experience/personalization/manage-fonts-in-windows). The CSS looks for installed Regular, SemiBold and Bold faces plus their italic companions. Installation of a font is separate from installation of this theme. Copying a font file or finding a registry entry does not prove that the current application can use it. Confirm it appears in Windows' font settings, then reopen the affected client when convenient if its font list is stale. Verify actual rendered text rather than trusting a family-name field.

An absent face uses fallback fonts so the interface remains readable. That fallback does not satisfy Inter acceptance. The [strict installed-font check](development.md) and [investigation record](acceptance.md#installed-font-investigation) keep those outcomes separate. Do not remove working fonts or clear global caches merely because a specimen falls back.

A font plugin can override the theme. Compare its current settings with the intended local-font configuration. Do not defeat a plugin by adding a universal `!important` font rule. Keep any temporary change recoverable. Code, icons and other writing systems must remain legible regardless of whether Inter is installed.

### Troubleshooting

If the theme is missing, confirm the downloaded file still ends in `.theme.css`, the actual loader folder and the **Load missing Themes** control. If colors do not change, check the matching native base and other full themes. If fonts differ, preserve and inspect the existing font-plugin settings. Disable only this candidate and compare the same surface with the recorded baseline. Keep QuickCSS intact. Retain the client version, package hash and exact loader error rather than installing another client.

## Ordinary Google Chrome

### Prerequisites and status

Use standard desktop Google Chrome. Obscur 0.1.1 has installation-only native evidence. Clair installation, both interface journeys, switching, Reset to default and test-profile cleanup remain incomplete. The local ZIPs are development candidates, without Chrome Web Store approval.

Use a [separate local test profile](https://support.google.com/chrome/answer/2364824?hl=en) in standard Google Chrome for the first installation. Add it from the profile menu, continue without signing in and keep sync off. Do not import or copy data from the everyday profile. Record the test profile's initial appearance. This isolates the theme change from existing browser choices.

### Install

1. Extract one Chrome ZIP to a permanent folder outside the repository's managed `dist/` directory. If building from source, copy the generated theme folder to that separate installation location. Locate the folder containing `manifest.json`.
2. Open `chrome://extensions` in the test profile, enable **Developer mode**, choose **Load unpacked** and select that folder. This is Chrome's [development installation route](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked), not a consumer store installation. If Chrome rejects the package or the control is unavailable, retain the exact error. Do not change browser policy or switch to another browser to obtain a pass.
3. Inspect **Settings > Appearance** and the real browser frame. Begin with Obscur, then give Clair the same checks. Test active/inactive tabs, multiple windows, the address bar and suggestions, bookmarks, tab groups, downloads and Incognito recognition.
4. Try windowed, split-screen and maximized sizes. Use normal browser zoom for page content when needed. Page zoom does not establish a change to Chrome's native UI font or frame scaling.

### Switch

Installing the other package should switch the active theme in that profile. Confirm the resulting appearance instead of treating the click as proof. Switch back once to test both directions.

### Remove and restore

To remove it, use **Settings > Appearance > Reset to default**, Chrome's [documented removal path](https://support.google.com/chrome_webstore/answer/148695). Confirm the candidate is gone, restore any test-profile color choice recorded earlier and close the test windows. Do not delete a profile containing data you want to keep. Keep the everyday profile untouched until the preview has passed the intended checks.

Remove only a remaining Clair or Obscur development entry if the extensions page exposes it, then return Developer mode to its recorded setting. Do not delete a live installation folder before removing its candidate.

### Fonts

These themes do not recolor ordinary websites, replace the new-tab page, change search or select a browser font. Chrome derives some component colors itself. A readable preview webpage does not prove that address-bar suggestions or inactive windows render correctly.

### Troubleshooting

Keep the installation folder separate from generated output. During the recorded native test, the loaded theme directory acquired `Cached Theme.pak`. The build validator correctly rejected that extra file. Do not delete files from a live theme installation or weaken the validator to make a rebuild pass. Build to a fresh output directory when the original is in use.

On a loading error, confirm that the selected extracted folder directly contains `manifest.json` and matches the chosen package. Record the error and stop if the supported developer control is unavailable. Do not change browser policy or signature enforcement. Use Reset to default to compare a suspect surface with the recorded baseline.

## Firefox

### Prerequisites and status

Use already installed desktop Firefox 128 or later and a disposable, unsynced profile. Record its current theme before testing. The 0.2.0 XPIs are unsigned static-theme candidates. Native loading, surfaces, switching and restoration remain unverified. A normal persistent installation requires Mozilla signing, which these packages do not have.

### Install

1. Save the chosen XPI. An XPI is a ZIP archive. Make a separate copy with a `.zip` extension and extract it to a test folder, retaining the original download and license. Locate `manifest.json` directly inside the extracted folder.
2. Open `about:debugging`, select **This Firefox**, choose **Load Temporary Add-on**, and select that `manifest.json`. This is Mozilla's temporary developer route. It lasts until removal or a Firefox restart. [Temporary installation](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/) and [XPI packaging](https://extensionworkshop.com/documentation/publish/package-your-extension/).
3. Confirm the selected Clair or Obscur identity and inspect tabs, address suggestions, focused fields, popups, sidebar selection and private-window recognition. A temporary load does not establish signed distribution or ordinary restart persistence.

### Switch

Remove the current temporary candidate in **This Firefox**, then load the other appearance's extracted manifest using the same route. Confirm the effective appearance and switch back once. Keep the system website-appearance preference recorded earlier. The two packages are manual choices, without an automatic light/dark pair.

### Remove and restore

Remove only Clair and Obscur temporary entries from `about:debugging`. In `about:addons` > **Themes**, enable the recorded original theme. If a candidate remains listed there, use its own three-dot menu and **Remove**. Confirm the original appearance returns. A normal Firefox restart also ends temporary installation, but it does not prove the previous custom theme was restored. [Mozilla theme removal](https://support.mozilla.org/en-US/kb/disable-or-remove-add-ons).

### Fonts

Firefox retains its native interface font. These packages contain no fonts and do not select Inter. Website fonts remain host and page choices. Missing Inter in this preview uses a system sans-serif fallback and is not a Firefox defect.

### Troubleshooting

If Firefox refuses the normal XPI installation, its unsigned status is expected. Use only the temporary developer route above. On a temporary-load error, check Firefox's version, the selected manifest location and exact error. Retain the package hash. Do not disable signature verification, modify `userChrome.css`, change policy or install a website restyler. Stop and restore the original theme if a native control is unreadable.

## Microsoft Edge

### Prerequisites and status

Use already installed desktop Edge with a separate recoverable profile, without signing in or syncing test changes. Record Edge's version, original theme, native Light/Dark/system choice and Developer mode setting. Both choices reuse the exact Chrome 0.1.1 ZIP with its deliberate Chrome filename. Edge loading, branded surfaces, switching and restoration remain unverified. No Edge store package is supplied.

### Install

1. Extract the chosen Chrome ZIP to a permanent test folder outside managed build output. Locate the folder containing `manifest.json`.
2. In Edge, open **Extensions** > **Manage extensions** (`edge://extensions`), enable **Developer mode**, choose **Load unpacked** and select that folder. These controls come from [Microsoft's local sideloading guide](https://learn.microsoft.com/en-us/microsoft-edge/extensions/getting-started/extension-sideloading). The general route does not establish that this color theme works in Edge.
3. Confirm the package identity in Edge's appearance settings. Inspect tabs, address suggestions, favorites, sidebar, active/inactive windows and InPrivate recognition. Record unchanged Edge-owned surfaces rather than recoloring them with extra CSS.

### Switch

Remove the current candidate using the theme removal route below, then load the other appearance's extracted folder. Confirm its identity and effective colors, then repeat in the other direction. Preserve the recorded native appearance choice during the comparison.

### Remove and restore

Open `edge://settings/appearance` and use the custom theme's **Remove** control. This theme-specific route was documented by [Microsoft's Edge program manager](https://techcommunity.microsoft.com/discussions/edgeinsiderannouncements/make-microsoft-edge-your-own-with-themes/2083165) in 2021. Current [Edge appearance documentation](https://support.microsoft.com/en-us/edge/visual-changes-to-microsoft-edge) warns that controls can differ by version. Check that the removal control exists before loading a candidate. If it is absent, stop the test rather than guessing a global reset.

Restore the recorded original theme and native appearance, confirm the baseline returns, and remove only a remaining candidate entry if Manage extensions exposes it. Return Developer mode to its recorded setting after candidate removal. Keep your everyday profile intact.

### Fonts

The reused Chrome color package cannot select Edge's native interface font. No Inter installation is required. Native fonts, scaling and website fonts remain host-owned. The preview's system sans-serif fallback remains readable when Inter is unavailable.

### Troubleshooting

If Load unpacked is unavailable or Edge rejects the theme, preserve the exact error and stop. Do not change managed policy or dismiss required developer warnings through a workaround. Check the selected folder and manifest before retrying. A Chrome pass is not an Edge pass. If colors differ, compare native appearance and host-owned surfaces, then remove this candidate and restore the recorded configuration.

## Brave

### Prerequisites and status

Use already installed desktop Brave with a separate unsynced test profile. Record the version, original theme, Brave Colors/native appearance and Developer mode setting. These choices reuse the exact Chrome 0.1.1 ZIP, without a Brave-specific package or claimed native pass. Loading, private-window distinction, switching and restoration remain unverified.

### Install

1. Extract the chosen Chrome ZIP to a permanent test folder outside managed build output, with `manifest.json` directly inside.
2. Open `brave://extensions`, enable **Developer mode**, choose **Load unpacked** and select that folder. Brave's own [extension control strings](https://github.com/brave/brave-core/blob/master/app/extensions_strings.grdp) establish these controls. This is a source-backed developer candidate route, not completed native theme acceptance.
3. Check the theme's identity and effective palette. Inspect active/inactive tabs and windows, address suggestions, sidebars and private-window recognition. Brave Colors or other host choices can take precedence.

### Switch

Use the theme-specific reset below to stop the current candidate, then load the other appearance's extracted folder. Confirm the resulting palette and switch back once. Record any host preference that takes precedence instead of assuming Chrome behavior transfers.

### Remove and restore

In Brave's **Settings** > **Appearance**, use the theme-specific **Reset to default** control, whose accessibility label is **Reset to default theme** in [Brave's settings source](https://github.com/brave/brave-core/blob/master/app/settings_strings.grdp). Confirm this control exists before installation. Do not use the browser-wide Reset settings operation, which affects unrelated preferences and data.

Restore the recorded original theme, Brave Colors and native appearance. Confirm the baseline returns. Remove only a remaining Clair/Obscur entry if the extensions page exposes it, then return Developer mode to its recorded setting. Keep the extracted folder until candidate removal is complete.

### Fonts

This color package contains no fonts and cannot change Brave's native interface font. Inter is optional for the webpage specimen, with system sans-serif fallback. Website fonts and browser text settings remain native choices.

### Troubleshooting

If the documented controls are absent in this Brave version, or loading is rejected, stop and retain the exact error, version and package hash. Do not modify policy or switch browsers to obtain a pass. If colors do not match, compare Brave Colors and host-owned surfaces, then use only the candidate's theme reset and restore the original choices.

## Vivaldi

### Prerequisites and status

Use already installed desktop Vivaldi 5.0 or later and a separate unsynced test profile. The color-only 0.3.0 settings ZIPs have no native import, derived-color, restart or restoration acceptance. No theme-gallery approval is claimed. Confirm the recovery controls before importing.

### Install

Vivaldi's documented ZIP route uses **Settings > Themes > Library > Open Theme** on desktop version 5.0 or later. Select one settings ZIP, inspect the live preview, and choose **Cancel** to discard it or **Install** only within an authorized test. Record existing theme, accent, transparency, schedule and private-window choices before testing. Check whether this minimal color-only export preserves them. Restore the previously selected theme and any test changes. Do not change global settings to hide an import failure.

The [official ZIP import guide](https://help.vivaldi.com/desktop/appearance-customization/shareable-vivaldi-themes/) supplies that route. Keep the ZIP intact. The exported integer `version: 1` is settings metadata, distinct from package version 0.3.0.

### Switch

Import the other appearance through the same preview route. After installation, select Clair or Obscur in **Settings** > **Themes** > **Library** to apply it, then select the first again. Inspect focus, text selection, tabs, toolbar, suggestions and panels. Preserve the original schedule and private-window theme, which are separate [Vivaldi controls](https://help.vivaldi.com/desktop/appearance-customization/browser-themes/).

### Remove and restore

Select only an imported Clair/Obscur theme in the theme library and use its **minus** deletion control, then select the recorded original theme. Vivaldi's [official 5.0 description](https://vivaldi.com/blog/vivaldi-5-0-desktop-themes-translate-panel/) documents that deletion for user-created or installed themes. Leave built-in and previous themes intact. Restore any changed accent, transparency, schedule and private-window choices and confirm the original appearance. If the installed version does not expose the deletion control, select the original theme to disable the candidate and retain the inactive entry for later removal.

### Fonts

The settings ZIP supplies colors only. It neither selects Inter nor changes the browser font or website fonts. Inter is optional for this preview, which uses system sans-serif fallback when unavailable.

### Troubleshooting

Cancel an unsuitable import preview. On rejection, retain Vivaldi's version, the exact error and package hash. Do not edit the accepted ZIP or change global settings to hide the failure. Vivaldi derives extra colors, and coloring mode or webpage accents can change surfaces. Omitted optional settings are not proof of preservation. Restore the recorded choices if import changes them. `vivaldi:themecolors` is a documented way to inspect effective UI colors, not a native acceptance certificate.

## Opera GX

### Prerequisites and status

Use already installed desktop Opera GX with a separate recoverable, unsynced test profile. One 0.3.0 ZIP pairs Clair Light with Obscur Dark. It is an unpacked developer candidate, without a signed CRX or GX Store approval. Native loading, color limits, effective contrast, switching, restart and restoration remain unverified. Opera One and mobile Opera are separate targets.

### Install

The paired Opera GX ZIP must be extracted to a separate permanent test folder. Its official developer route uses **opera:extensions > Developer mode > Load unpacked**, then shows the candidate in **opera:mods**. Record existing mods, their enabled elements and native appearance first. Test Clair in Light and Obscur in Dark, then disable only this candidate and restore the recorded choices. Keep sounds, music, wallpaper, shaders and website styling absent. The host can limit or derive the supplied colors, so a matching webpage is not proof of the effective palette.

Choose the extracted folder containing `manifest.json`, retaining its icon and license. The [official load procedure](https://github.com/opera-gaming/gxmods#how-to-load-sample-mods) establishes the developer controls. Confirm the candidate's **Clair and Obscur** identity and its theme element in **opera:mods** before judging the palette.

### Switch

Keep the one paired candidate enabled and choose native **Light** for Clair or **Dark** for Obscur in Opera GX's appearance controls. Switch back once. There is no second package to install. The [official mod contract](https://github.com/opera-gaming/gxmods/blob/main/documentation/mods.md) pairs the light and dark entries. Check tabs, address suggestions, private-window recognition and selected/highlighted text in each mode.

### Remove and restore

In `opera:mods`, disable only **Clair and Obscur**, then restore the recorded native appearance and previous mods with their original enabled elements. Confirm the baseline returns. To remove the loaded development entry, use that candidate's **Remove** control in `opera:extensions` if exposed by the installed version. Confirm the disable/removal controls before loading. Return Developer mode to its recorded setting after removal and retain the extracted folder until then. Do not reset all mods or delete unrelated packages.

### Fonts

The mod supplies only HSL accent/base hints and a package icon. It does not select a browser font or bundle Inter. This preview uses local Inter when available and system sans-serif fallback otherwise.

### Troubleshooting

Check the manifest folder if the mod does not appear. On loading rejection or absent controls, stop and retain the exact error, version and package hash. Opera GX derives and can limit the colors. Its [official guidelines](https://github.com/opera-gaming/gxmods/blob/main/documentation/guidelines.md) warn that overly light or dark colors are unavailable. Do not change the accepted hints, weaken security or enable extra visual effects to disguise a mismatch. Disable the candidate and compare the native baseline if contrast is poor.

## Vencord

### Prerequisites and status

Use an already installed Vencord desktop client, Vesktop or supported browser extension with its **Local Themes** loader. Browser, desktop and Vesktop outcomes remain separate and unverified for these 0.2.0 files. Vencord's userscript does not support Themes. Do not install a different client, extension or website restyler to use this guide. These are unofficial client-mod choices, without Discord endorsement or gallery approval.

Record native appearance, enabled themes, activation modes, text size/zoom and font-plugin settings. Preserve QuickCSS and any same-name file before copying. Do not export account/session data.

### Install

1. Open **Settings** > **Vencord** > **Themes** > **Local Themes**. Desktop/Vesktop: use **Open Themes Folder**, copy the downloaded `Clair-Vencord.theme.css` or `Obscur-Vencord.theme.css`, then choose **Load missing Themes**. Browser extension: use **Upload Theme** to select the downloaded CSS, then refresh the local list if needed. These branches come from [Vencord's local loader source](https://github.com/Vendicated/Vencord/blob/main/src/components/settings/tabs/themes/LocalThemesTab.tsx).
2. Use native **Light** for Clair or native **Dark** for Obscur. Disable only conflicting full color themes, enable one family card, and match its Light only/Dark only activation mode if offered. The opposite native base retains its own palette.
3. Check readable messages, inputs, links, code, icons, switch states and keyboard focus, then supported larger text/zoom. A fixture is not a loaded-client pass.

### Switch

Disable the current family card, select the other native appearance, then enable the matching other card. Switch back once. Preserve the recorded activation modes and unrelated theme choices.

### Remove and restore

Disable both family cards. Restore the recorded native appearance, previous themes/activation modes, text size/zoom and any font setting changed during the test. Confirm the baseline returns. Desktop: remove only the copied family files from the actual Themes folder. Browser: use the family card's deletion control to remove only the uploaded candidate. The local loader source implements that per-card removal. Keep QuickCSS and unrelated plugins intact.

### Fonts

Follow the complete [local Inter and safe fallback guidance](#local-client-fonts-and-fallbacks). The package uses installed Regular, SemiBold, Bold and genuine italic companions, with code, icon and language fallbacks. No remote font or binary is bundled.

### Troubleshooting

If the card is absent, verify the `.theme.css` filename, actual Local Themes loader and Load missing Themes control. If browser upload is unavailable, stop rather than pasting CSS into QuickCSS or relying on an online URL. If colors do not change, check native base, other themes and ClientTheme. If text differs, inspect preserved font-plugin settings. Disable only the candidate and restore the baseline. Record the host version, package hash and exact error. The [Themes source](https://github.com/Vendicated/Vencord/blob/main/src/components/settings/tabs/themes/index.tsx) records the userscript limitation.

## BetterDiscord

### Prerequisites and status

Use an already installed desktop BetterDiscord client with its Themes page. The 0.2.0 local CSS files have source/component checks, with native loading, full surfaces, switching, restart and restoration still unverified. They have no gallery approval or Discord endorsement. Do not install or repair a client modification as part of this guide.

Record native appearance, enabled themes, text size/zoom and font/plugin settings. Preserve Custom CSS/QuickCSS and same-name files, without exporting account/session data.

### Install

1. In **Settings** > **BetterDiscord** > **Themes**, choose **Open Themes Folder**. Copy the selected `Clair-BetterDiscord.theme.css` or `Obscur-BetterDiscord.theme.css` into that actual folder without replacing existing files. Return to Themes and enable its card. This is the [official add-on installation route](https://docs.betterdiscord.app/users/guides/installing-addons.html).
2. Select native **Light** for Clair or native **Dark** for Obscur. Enable only one family theme and temporarily disable only conflicting full themes. The opposite native base keeps its baseline.
3. Check messages, inputs, links, code, icons, switches and keyboard focus at normal and increased supported text size/zoom. Keep disabled and critical controls recognizable.

### Switch

Disable the active family card, change to the other native appearance and enable its matching family card. Switch back once and confirm both effective appearances.

### Remove and restore

Disable both family cards. Restore the recorded original appearance, theme selections, text size/zoom and changed font/plugin settings. Confirm that the original appearance returns. Remove only the copied Clair/Obscur files from the actual Themes folder when no longer needed. Leave Custom CSS/QuickCSS and unrelated plugins intact.

### Fonts

Use the [local Inter and safe fallback guidance](#local-client-fonts-and-fallbacks). Installed Regular, SemiBold, Bold and italic companions are optional for readability. Code, icons and other languages retain fallbacks. No font binary, remote import or forced client installation is supplied.

### Troubleshooting

If the card is absent, verify the actual folder and the complete `.theme.css` filename, rather than a `.txt` suffix. Keep the file's metadata and license intact. If colors or fonts differ, check the matching native base and conflicting themes/plugins, then disable only the candidate to compare the original surface. If Themes is unavailable, stop and retain the host version and error. Do not overwrite Custom CSS or reinstall BetterDiscord to make this candidate appear.

## Local client fonts and fallbacks

The preview and client CSS look for installed Inter 400, 600 and 700, plus Regular Italic, SemiBold Italic and Bold Italic. The themes remain readable with system sans-serif fallbacks when Inter or a face is unavailable. Code uses an appropriate monospace fallback. Icon fonts and other writing systems remain host-owned. Fallback readability does not establish Inter acceptance.

Font installation is optional and separate from theme installation. No package downloads fonts. If you choose to install Inter later, use the [official distribution](https://rsms.me/inter/) and your operating system's supported font installation. On Windows, the [normal font procedure](https://support.microsoft.com/en-us/windows/experience/personalization/manage-fonts-in-windows) is documented separately. A stale client font list may need an ordinary reopen when convenient. Do not clear global caches, remove working fonts or add a universal font override.

Confirm actual rendered Regular, SemiBold, Bold and italic faces when the client exposes a supported diagnostic. A font-family field, file on disk or preview face check does not prove the native client uses it. The earlier Windows installation supplied six faces in fresh headless checks, while the native Equibop inspection covered only Regular and Bold. Persistence after a later normal restart and the other native faces remain unverified. Keep existing font-plugin choices recoverable.

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
