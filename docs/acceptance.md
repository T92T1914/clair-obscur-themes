# Acceptance scope

This record distinguishes implementation from application acceptance for the 0.1.1 preview. Source contracts and component fixtures can establish useful facts without proving that a running client consumes every style as intended. Partial native Equibop results and the remaining gates are recorded separately below.

## Platform adapter increment

The 0.2.0 Firefox, Vencord and BetterDiscord candidates add explicit platform mappings while retaining the original four 0.1.1 download hashes. Edge reuses the exact Chrome ZIP. [Platform portability](platform-portability.md) records the mappings, source contracts, manual native acceptance scenarios and distribution limits.

Both Firefox static manifests passed Mozilla `web-ext` 10.7.0 with `addons-linter` 10.13.0, warnings treated as errors and configuration discovery disabled. Each returned zero errors, warnings and notices. This is schema and package validation. Firefox was not installed or launched, and neither XPI is signed.

On Windows, isolated headless Chrome 154.0.8037.95 with Playwright 1.63.0 passed all 13 browser checks with no skips. The actual glyph checks established all six local Inter faces in the specimen. Synthetic Vencord and BetterDiscord component models checked matching and opposite host modes, paired brand and switch colors, keyboard focus, reduced motion, disabled behavior and unchanged geometry. All twelve download choices saved the expected bytes in separate six-choice Clair and Obscur journeys. No real Discord client or browser theme was installed by that suite.

The first twelve-click burst test stopped producing a download event after ten saved files. Chromium's [implementation at the observed browser revision](https://github.com/chromium/chromium/blob/05d469856e75794131cc2e5d9b2f6b6f10a70388/third_party/blink/renderer/core/frame/local_frame.cc#L284) defines that burst limit. The corrected chooser tests keep browser safeguards unchanged and preserve byte verification. This finding concerns the harness's rapid bulk-download scenario. It is not a product performance result or a guarantee about every browser's download behavior.

Native Firefox, Edge, browser Vencord, desktop Vencord, Vesktop and BetterDiscord loading, full surfaces, restart persistence and restoration remain unverified. Native typography, physical displays and mobile-native theme availability remain separate questions. No signing, store or gallery approval is claimed.

## Browser candidate increment

The 0.3.0 increment adds separate color-only Vivaldi settings ZIPs and one Opera GX package pairing Clair Light with Obscur Dark. Brave choices reuse the exact Chrome 0.1.1 ZIPs. All ten earlier download hashes remain unchanged, including the Firefox, Vencord and BetterDiscord 0.2.0 files. Seventeen choices now refer to thirteen distinct files. The [platform guide](platform-portability.md) records each native route and the limits of its color mapping.

On October 3, 2026, Windows Python 3.11.8 ran all 125 unit tests with zero failures and one existing skip because this host cannot create a symlink without additional privilege. No privilege was changed to remove that skip. A fresh build, byte-for-byte rebuild check and preview generation each completed successfully. The added tests inspect Vivaldi identities and original color fields, paired canonical GX hints, original icon pixels and PNG integrity, deterministic archive contents, preservation of earlier files and refusal of unwanted capabilities or layout settings.

Isolated headless Chrome 154.0.8037.95 with Playwright 1.63.0 and Node 24.16.0 passed all 11 checks in `tests/browser/preview.test.mjs` with zero skips. This count covers that actual executed file. Other unchanged browser test files were not rerun solely to increase it. The six Inter glyph faces, system fallback, existing client state fixtures, keyboard interaction, larger text and no-JavaScript delivery remained usable. The new browser sections were readable and navigable at 390 pixels with touch-oriented interaction. The page saved all seventeen choices with matching SHA-256 values in separate eight-choice Clair and Obscur journeys and one paired Opera GX journey. This is emulated page evidence, not a physical phone or native theme installation result.

The jobs retained source fingerprints and logs, completed within their fixed bounds and reported zero owned processes after retirement. The first monitored unit attempt was interrupted by a temporary-directory observation race and remains an incomplete run. The successful run used a separately reviewed correction to that observer. No theme assertion was weakened, and no browser download safeguard was changed.

No Vivaldi or Opera GX native schema validator was run. The tests enforce the project's inspected format contract, not an official certification. Vivaldi's acceptance of omitted optional fields and its effective selection colors remain unknown. Opera GX's documented limits on overly light or dark hints, resulting palette and contrast remain unverified. Brave loading and branded surfaces also remain unverified. Installation, switching, ordinary restart, disable/restoration and store or gallery decisions are separately pending for each new desktop target. No mobile-native theme compatibility is claimed.

## Current state

| Item | Established | Remaining gate |
| --- | --- | --- |
| Clair and Obscur for Chrome | Native color-theme generators and package validation are implemented. Obscur installed through Load unpacked in an isolated ordinary Chrome profile | Install Clair, complete both native interface checks, then verify switching, rollback and cleanup |
| Clair and Obscur for Equicord | Both themes loaded in Equibop, applied on matching native bases, retained the native palette on opposite bases and restored the recorded configuration. October 14 checks added ordinary client surfaces, larger text and smaller windows in both variants | Complete the uninspected host surfaces, typography and interaction checks listed below |
| Local application versions | September checks identified Chrome 153.0.8010.53 and Equibop 3.3.1.0. October checks identified Chrome 155.0.8059.79 and a newer Equicord client build, recorded below | Results apply only to the recorded versions, configuration and inspected scope |
| Rendered Inter faces | All six installed faces rendered in the October 14 later-boot headless check. September native checks identified Regular and Bold in both variants. October native checks identified Regular and Bold on Obscur and SemiBold and SemiBold Italic in both appearances | Verify Regular Italic, Bold Italic, complete face coverage across both variants and native code/language fallback. The later-boot result does not establish continuous or permanent persistence |
| Native restoration | September and October Equibop checks restored their respective recorded appearance, theme, sync, FontLoader and QuickCSS state | Chrome restoration and test-profile cleanup remain incomplete |
| Physical display and comfort | User-reported baseline is recorded in the design document | Physical viewing, captured-media comparison and subjective comfort remain **not verified** |

The identified application versions are Windows test targets. Other operating systems, Discord clients and browser derivatives are not covered by a native compatibility claim. Obscur's installation confirmation does not establish complete Chrome acceptance. Detailed private environment and capture records stay outside the public source.

The strict font assertion remains enabled with `THEME_REQUIRE_INTER=1`. Ordinary CI skips that assertion when the required local faces are unavailable and tests fallback separately. A skipped font assertion is not a passed typography check. Each expected PostScript face must have a positive glyph count in its own specimen. A family declaration or an expected face with zero glyphs does not pass.

## Installed-font investigation

On September 24, 2026, the same Windows Chrome version and unchanged font declarations passed, then failed after an intervening Windows restart. The six files and current-user registry entries still existed, but Windows font enumeration omitted Inter. Fresh isolated processes reproduced the following results. All six weights/styles were tested in each row.

| Path | Before session activation | After session activation |
| --- | --- | --- |
| Generated local aliases | No Inter glyphs | All six expected Inter faces rendered |
| Ordinary `Inter` family with explicit weight/style | System fallback | All six expected Inter faces rendered |
| Individual full-name and PostScript `local()` lookups read from the files | All twelve lookups failed | All twelve resolved and rendered their expected face |
| Diagnostic-only direct-byte control | All six expected faces rendered | All six expected faces rendered |
| Intentionally unavailable local font | System fallback | System fallback |

The repair activated the six already-installed, hash-verified files through Windows' documented [AddFontResourceW](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourcew) API and sent its font-change notification. Fresh processes then resolved the unchanged local names, and the strict test passed without a skip. Font files, registry entries, desktop font choices, browser profiles and display settings were not rewritten. No global cache was cleared, service restarted or font binary added to the product.

The next normal Windows restart on September 24, 2026 reproduced the failure. Before any activation or installation attempt, a fresh process again omitted Inter from its installed-font enumeration. At revision `d40013db242af104e75102694e476c3338db3f10`, the unchanged strict check failed all six local faces with zero skips. The intentional missing-font control passed separately. All six required files retained their expected hashes and current-user registrations.

The separate diagnostic reproduced the same pattern after that restart: generated aliases and ordinary family selection supplied no Inter glyphs, all twelve metadata-derived local lookups failed, and the same six files rendered correctly through the direct-byte control. These results establish that the previous activation restored only the tested session. They do not identify why Windows failed to load the persisted per-user installation. The direct-byte control bypasses installed-name discovery and cannot satisfy the local-font requirement.

After that failure, Windows Explorer's normal per-user **Install** operation was used on the same six official, hash-verified TTF files. This installation did not use **Install for all users**, scripted resource activation, cache deletion or service restarts. Fresh isolated Chrome 153.0.8010.53 processes then passed the required six-face check and the missing-font control at revision `4db349fa349ae3a46b20a6befbf8d99187834f90`, both with zero skips. Each expected PostScript face rendered a positive glyph count. A separate diagnostic using published artifact revision `303c5dbdc54430d5a3d57dbd574ed230eb9a8c4a` resolved all six faces through generated aliases, ordinary family selection, full names and PostScript names. The direct-byte control still rendered all six faces, and the intentionally missing font still used system fallback.

This establishes current-session availability after native installation. At that stage, persistence after the installation remained **not verified**, and the next normal Windows restart still needed a check before any repair or activation. The earlier restart failure remains evidence of the session activation's limit, and its cause is still unresolved. Microsoft documents [temporary resource loading](https://learn.microsoft.com/en-us/windows/win32/gdi/font-installation-and-deletion) separately from its [normal font installation procedure](https://support.microsoft.com/en-us/windows/experience/personalization/manage-fonts-in-windows).

The September 24 required installed-font check passed. The partial native Equibop typography results below do not establish all six native faces. Native Chrome acceptance remains open. The published 0.1.1 theme files are unchanged.

### Later-boot installed-font observation

On October 14, 2026, the existing strict installed-face and missing-font checks ran against source revision `b799eef4cc4f715fc4c2ae0f8a2059cf205d9e6a` in isolated headless ordinary Chrome 155.0.8059.79 on Windows. The recorded Windows boot occurred after the September 24 installation session. No font installation, resource activation, cache repair, service restart or forced computer restart preceded the checks in this continuation. All six installed files still matched both the official Inter 4.1 preparation hashes and the retained post-install file hashes.

Both selected tests passed with zero skips. Each expected installed face rendered a positive glyph count:

| Installed face | Glyph count |
| --- | ---: |
| `Inter-Regular` | 157 |
| `Inter-SemiBold` | 29 |
| `Inter-Bold` | 26 |
| `Inter-Italic` | 41 |
| `Inter-SemiBoldItalic` | 16 |
| `Inter-BoldItalic` | 12 |

The code specimen used Consolas for 13 glyphs. The deliberately unavailable local-font control used Segoe UI for 157 glyphs, with no network font request. These are installed-font and fallback observations in the existing webpage specimen. They do not establish Chrome frame typography or the remaining native Equibop faces.

The first attempt stopped at a Windows temporary-output rename refusal before browser launch and font collection. The unchanged-source retry used task-owned temporary storage and completed both tests. The initial failure remains retained separately from the successful font result.

This establishes installed-face availability after a later Windows boot, before intervention in this task. It does not establish an uninterrupted history without intervening installation or activation, identify the cause of the older restart failures, or prove permanent persistence. The September failures remain part of the investigation. Theme package bytes and all native application acceptance gaps remain unchanged by this check.

## Partial native Equibop results

On September 24, 2026, native checks loaded the published 0.1.1 CSS through Equicord's actual theme loader, located with **Open Themes Folder**. The observed client reported Stable 619060 (`3bd5565`), Equicord `957307d5f` Standalone, Electron 43.7.1 and Chromium 150.0.7871.250. The retained installed-file hashes match the published CSS artifacts.

Obscur applied on native Dark and Clair applied on native Light. Both variants kept the inspected settings, theme gear menus, enabled/disabled controls and icons readable. The built-in Accessibility message preview showed readable text, a link, emoji and a button under both palettes. Native 16 px text size and default density were left unchanged. These observations do not cover ordinary message histories or the full client interface.

The actual client's embedded DevTools **Rendered Fonts** view identified these local faces with positive glyph counts:

| Variant | Regular 400 description paragraph | Bold 700 theme card title |
| --- | --- | --- |
| Obscur | `Inter-Regular`, 169 glyphs | `Inter-Bold`, 6 glyphs |
| Clair | `Inter-Regular`, 169 glyphs | `Inter-Bold`, 5 glyphs |

At that stage, SemiBold and all three italic faces remained uninspected in the native client. Native code and language fallback were also unverified. The headless six-face pass did not fill those gaps.

Both opposite-mode gates were exercised. Clair enabled on Dark retained the native dark palette, and Obscur enabled on Light retained the native light palette. Switching from Clair to Obscur worked. Disabling each theme returned its corresponding native palette.

Restoration completed after the checks. The original theme and native appearance returned, and the saved appearance settings matched the baseline. QuickCSS, FontLoader settings and original theme files remained unchanged. The original sync choices were restored, settings were closed and the client was minimized through its native control. Display settings were not changed.

These are partial native results. Channel lists, ordinary message history, search results, popouts, extended keyboard/interaction states, increased text size or zoom, smaller windows and physical viewing were outside that September inspection. Full native Equibop acceptance remains open.

### October 14 native continuation

Agent-operated checks at source revision `f2cdbed8950a8e3b2bc4502c8bbd7b0ce96667e1` used Equibop 3.3.1.0, Stable 636431 (`a5d0242`), Equicord `e0e85c8d4` Standalone, Electron 43.7.1 and Chromium 150.0.7871.250. The installed 0.1.1 CSS remained unchanged. The native client's embedded DevTools Rendered Fonts view identified these actual local faces:

| Appearance | Native surface | Rendered face | Glyphs |
| --- | --- | --- | ---: |
| Obscur on Dark | Open Themes Folder button | `Inter-Regular` | 18 |
| Obscur on Dark | Obscur theme card title | `Inter-Bold` | 6 |
| Clair on Light | Accessibility example-message header descendants | `Inter-SemiBold` | 12 |
| Clair on Light | The same header descendants | `Inter-SemiBoldItalic` | 7 |

These are four observed faces across the listed appearances, not all six faces in each variant. The host's 500-weight Theme Management heading separately rendered Inter Regular for 16 glyphs.

Both matching appearances and opposite native bases remained readable in the inspected settings. Switching from Obscur to Clair and back worked through the actual theme controls, with each outgoing theme disabled before the other was enabled. Clair's native chat text was increased from 16 px to 20 px, then restored to 16 px. The message grew and its link wrapped. Other enlarged-preview controls were not independently exercised. Default density, chat display, message spacing and 100% zoom were preserved.

Clair's channel list, ordinary messages, reply and mention blocks, member list and composer were inspected in a 1440 by 2512 maximized window and a 1283 by 735 smaller window. The native search filter/history popover was inspected without entering or submitting a query. The restored Obscur view also showed the original channel, message, member and composer surfaces. No message was sent or edited, and the preexisting composer draft was preserved. Search results, popouts and complete keyboard-focus coverage remain unverified.

Restoration returned the original Obscur-enabled configuration, Sync with computer selection and synchronization setting. The recorded appearance fields, FontLoader fields and QuickCSS hash matched their fresh baseline. Text size returned to 16 px, the original maximized channel view returned, and settings, search popover and DevTools were closed. This establishes restoration of the recorded state, not byte identity of the entire client settings file. Fonts and display settings were not changed.

Later agent-operated checks at source revision `9048af23966f1da23243184d9ef00b161c6cad52` used the same client build and unchanged installed CSS. Under Obscur with Sync with computer retained, the actual native document reported `theme-dark theme-darker`, 16 px text, Default density and 100% zoom. Rendered Fonts identified local `Inter-SemiBold` for 12 glyphs and local `Inter-SemiBoldItalic` for 7 glyphs in the built-in Accessibility example header descendants. This adds those two faces under Obscur. The header's own computed 400 weight does not establish its descendants' exact faces.

Obscur's ordinary channel, message, reaction and member surfaces were inspected at 1283 by 735. Its native Theme Preview drawer was opened and returned to settings without changing the theme. The Accessibility example was increased from 16 px to 20 px, then restored to a separately confirmed 16 px. Text enlarged, the link wrapped and the Example Button remained visible. Default density and chat display, 16 px message-group spacing and saturation were preserved. These are observations of the visible surfaces, not complete layout or keyboard-focus coverage.

The native Language & Time dropdown displayed readable Thai, Chinese, Japanese and Korean labels under Obscur. English and the existing time format remained selected. Opening the inspector and activating its picker closed that transient menu, so no actual fallback face or glyph count was established for those labels. This is a scoped visual observation, not an exact fallback-font or all-language pass. The native Changelog was also inspected, but neither it nor the Theme Preview drawer supplied a suitable genuine italic or code sample.

The follow-up returned the selected native view and its original maximized geometry, with settings, diagnostics and the language menu closed. Recorded appearance and FontLoader fields matched the fresh starting baseline. QuickCSS matched the retained empty-file hash, and both installed theme files retained their accepted hashes. Whole settings-file byte identity and exact conversation scroll-position identity are not claimed. No message, composer, reaction, plugin, update or subscription action was performed. Chrome's separate controller stop and cleanup obligation remain unresolved.

Regular Italic, Bold Italic, complete face coverage across both variants, native code and language fallback, independent restart behavior and other unvisited surfaces remain unverified. The earlier partial results remain valid within their original scope. Full native Equibop acceptance remains open.

## Native Chrome installation result

On September 24, 2026, ordinary Chrome 153.0.8010.53 installed the Obscur 0.1.1 package through **Load unpacked** in a new isolated profile. Chrome's native infobar confirmed **Installed theme "Obscur"**. The everyday profile was not used or modified.

This establishes installation only. The native session was interrupted before the remaining browser-interface checks, Clair installation, switching, **Reset to default** and cleanup. The isolated test window remained open with Obscur installed at the end of the recorded run. Restoration is **not verified**. Chrome's native interface font remains outside the theme's control.

On October 14, 2026, the retained isolated profile was reopened in ordinary Chrome 155.0.8059.79. Its actual Profile Path was confirmed on `chrome://version` before any theme change. The controller then stopped navigation to Appearance because it could not determine the current browser URL with enough confidence to enforce policy. No new theme installation, switching, reset or settings change was performed. Current theme identity, Developer mode and cleanup remain unverified. The test Chrome and task-owned file-browser windows were left open at that stop. The September installation remains historical evidence, and the controller block is not a product defect.

## Evidence levels

| Evidence | What it can establish | What it cannot establish |
| --- | --- | --- |
| Token validation | Schema, declared opaque color pairs and configured contrast thresholds | Every inherited application state, physical luminance or comfort |
| Unit and package checks | Generated fields, deterministic bytes, archive contents and rejected invalid inputs | Successful installation, store approval or renderer behavior |
| Headless component fixture | The tested DOM, font faces and keyboard/viewport behavior in that fixture | Native Chrome controls or complete Equibop compatibility |
| Actual application check | Observed behavior at the recorded host version and configuration | Other clients, all plugins or future host versions |
| Physical viewing check | Recorded impressions under the preserved display setup | A universal readability or eye-health conclusion |
| SDR screenshot or recording | The inspected capture's appearance | The monitor's live HDR appearance or physical luminance |

Executed check results should identify the source revision or working-tree identity, exact command, tool versions, duration, exit status and retained log. A list of available tests is not evidence that all of them ran. Later source changes require the affected checks to run again.

Preserve who performed a native check. A user's manual installation and restoration can establish useful acceptance evidence when the version, steps and result are recorded. Label it user-performed. Separately identify any screenshots or recordings inspected by someone else. Do not relabel that evidence as an automated or agent-controlled test.

## Native acceptance checklist

Run Obscur first and repeat the same coverage for Clair. Record the package hash, native base, application version and outcome for each scenario. Preserve configuration and use harmless or synthetic content for captures.

**Equibop with Equicord**

- Enable the local theme through the actual loader, confirm its identity and verify disable/restore behavior.
- Read channel lists, message history, search results, settings, popouts and menus. Check primary and secondary text, empty states, selected text and links.
- Inspect inline and fenced code, syntax colors, emoji, icons and representative non-Latin text. Check actual Regular 400, SemiBold 600, Bold 700 and italic faces in surfaces intended to use them.
- Exercise keyboard focus, enabled/disabled buttons, checked/unchecked switches, hover, focus and validation feedback. State must not depend solely on color.
- Repeat at increased native text size or zoom and smaller window sizes. Check the opposite native base and confirm that the mode gate avoids partial conversion.
- Record conflicting theme, QuickCSS or FontLoader influence separately. Do not silently change unrelated settings to produce a pass.

**Google Chrome**

- Install the extracted native package in an isolated standard Chrome profile. Confirm theme identity and Reset to default behavior.
- Inspect active/inactive tabs, focused/unfocused windows, address-bar text and suggestions, bookmarks, tab groups, downloads and the new-tab surface.
- Confirm that Incognito remains recognizable and native security indicators remain usable. Omitted Incognito overrides alone do not prove this.
- Compare maximized, windowed and split-screen use. Check browser-derived hover/focus states and keyboard navigation.
- Keep page typography separate from native browser fonts. Do not use a webpage imitation as evidence of the frame.

**Reading and display**

- Preserve the existing HDR, SDR brightness, Auto HDR, monitor mode and color-profile associations. Record inspected facts separately from reported settings.
- Read a sustained passage in both variants, then inspect selection, code and a dense control surface. Record discomfort or ambiguity as feedback, not as a medical finding.
- Label captures by their actual capture/export path. Do not apply a hidden transform to make screenshots imitate the physical display.

Completion means all four native variants have the relevant recorded results, remaining limitations are explicit, and removal works. It does not mean every Discord plugin, Chrome version or monitor has been certified.
