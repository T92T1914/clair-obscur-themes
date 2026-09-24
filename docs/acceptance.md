# Acceptance scope

This record distinguishes implementation from application acceptance for the 0.1.1 preview. Source contracts and component fixtures can establish useful facts without proving that a running client consumes every style as intended. The same native gates remain open for both Clair and Obscur.

## Current state

| Item | Established | Remaining gate |
| --- | --- | --- |
| Clair and Obscur for Chrome | Native color-theme generators and package validation are implemented | Install each in ordinary Chrome and verify native frame states and rollback |
| Clair and Obscur for Equicord | Standalone CSS generators, local font aliases and matching-base gates are implemented | Load each in Equibop with Equicord and inspect actual host surfaces and rollback |
| Local application versions | Chrome 153.0.8010.53 and Equibop 3.3.1.0 were identified | These versions are test targets, not passed compatibility claims |
| Rendered Inter faces | The retained 0.1.0 fixture resolved six Inter faces. The 0.1.1 Windows strict rerun failed to resolve any local Inter alias, despite the local files and font registrations remaining present. Its fallback fixture rendered Segoe UI | Resolve the current local font availability discrepancy and verify actual Equibop glyphs and preserved code/icon/language fallback |
| Native installation | No completed installation result is recorded for either target application | Both application checks remain **not verified** |
| Physical display and comfort | User-reported baseline is recorded in the design document | Physical viewing, captured-media comparison and subjective comfort remain **not verified** |

The identified application versions are Windows test targets. Other operating systems, Discord clients and browser derivatives are not covered by a native compatibility claim. No theme rejection or successful native installation is established by the missing result. Detailed private environment and capture records stay outside the public source.

The strict font assertion remains enabled with `THEME_REQUIRE_INTER=1`. Ordinary CI skips that assertion when the required local faces are unavailable and tests fallback separately. A skipped font assertion is not a passed typography check. An independent headless diagnostic reproduced the local-name lookup failure and rendered all six expected glyph faces from the same files supplied as in-memory bytes. That narrows the issue to local font discovery, not a malformed font file or alias spelling, but its cause remains unresolved. The product still uses local fonts only. No font installation, cache reset or system setting change was made to force a pass.

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
