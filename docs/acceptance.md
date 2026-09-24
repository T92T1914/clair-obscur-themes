# Acceptance scope

This record distinguishes implementation from application acceptance for the 0.1.1 preview. Source contracts and component fixtures can establish useful facts without proving that a running client consumes every style as intended. The same native gates remain open for both Clair and Obscur.

## Current state

| Item | Established | Remaining gate |
| --- | --- | --- |
| Clair and Obscur for Chrome | Native color-theme generators and package validation are implemented | Install each in ordinary Chrome and verify native frame states and rollback |
| Clair and Obscur for Equicord | Standalone CSS generators, local font aliases and matching-base gates are implemented | Load each in Equibop with Equicord and inspect actual host surfaces and rollback |
| Local application versions | Chrome 153.0.8010.53 and Equibop 3.3.1.0 were identified | These versions are test targets, not passed compatibility claims |
| Rendered Inter faces | After a scoped Windows session repair, the strict headless check resolves all six required installed Inter faces with actual glyphs. The earlier failure and its direct-byte control are retained separately | Verify persistence after a future normal restart and actual Equibop glyphs, including preserved code/icon/language fallback |
| Native installation | No completed installation result is recorded for either target application | Both application checks remain **not verified** |
| Physical display and comfort | User-reported baseline is recorded in the design document | Physical viewing, captured-media comparison and subjective comfort remain **not verified** |

The identified application versions are Windows test targets. Other operating systems, Discord clients and browser derivatives are not covered by a native compatibility claim. No theme rejection or successful native installation is established by the missing result. Detailed private environment and capture records stay outside the public source.

The strict font assertion remains enabled with `THEME_REQUIRE_INTER=1`. Ordinary CI skips that assertion when the required local faces are unavailable and tests fallback separately. A skipped font assertion is not a passed typography check. Each expected PostScript face must have a positive glyph count in its own specimen. A family declaration or an expected face with zero glyphs does not pass.

## Installed-font investigation

On September 24, 2026, the same Windows Chrome version and unchanged font declarations passed, then failed after an intervening Windows restart. The six files and current-user registry entries still existed, but Windows font enumeration omitted Inter. Fresh isolated processes reproduced the following results. All six weights/styles were tested in each row.

| Path | Before repair | After repair |
| --- | --- | --- |
| Generated local aliases | No Inter glyphs | All six expected Inter faces rendered |
| Ordinary `Inter` family with explicit weight/style | System fallback | All six expected Inter faces rendered |
| Individual full-name and PostScript `local()` lookups read from the files | All twelve lookups failed | All twelve resolved and rendered their expected face |
| Diagnostic-only direct-byte control | All six expected faces rendered | All six expected faces rendered |
| Intentionally unavailable local font | System fallback | System fallback |

The repair activated the six already-installed, hash-verified files through Windows' documented [AddFontResourceW](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourcew) API and sent its font-change notification. Fresh processes then resolved the unchanged local names, and the strict test passed without a skip. Font files, registry entries, desktop font choices, browser profiles and display settings were not rewritten. No global cache was cleared, service restarted or font binary added to the product.

This establishes a runtime font-availability failure and a successful repair in the tested Windows session. It does not establish why the saved per-user installation failed to become available after that restart, or prove that the repair survives another restart. The direct-byte control bypasses installed-name discovery. Its success alone never establishes that a `local()` alias works. Here, the independent post-repair local lookups supply that evidence.

The original failing result remains part of the evidence. The current pass covers the isolated Chrome specimen, not typography in a running Equibop client. Native installation, switching and restoration remain open for all four variants. The published 0.1.1 theme files did not need an artifact change for this machine-local repair.

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
