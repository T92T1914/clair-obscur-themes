# Clair and Obscur watch-face candidate

This separate Connect IQ watch-face source targets `fenix9pro47mm`, the fēnix 9 Pro 47 mm AMOLED. Version 0.4.0 adds an original analog dial beside the retained digital layout. Both show local time, a compact English weekday and date, two selectable information fields and watch battery percentage. Clair and Obscur use `tokens-monochrome.json`: white backgrounds with black primary lettering in Clair, black backgrounds with white primary lettering in Obscur, and neutral gray for supporting information. Earlier programs remain separate and unchanged. A separate always-on view clears to true black and draws only the digital time, regardless of the active layout.

The current 0.4.0 normal and test-enabled programs compiled for the exact target with Connect IQ SDK 9.2.0 and device package `ee244507b073c52779d26e77dc69b690d79098bd`. The test build includes 20 annotated test groups. They have not run for 0.4.0. The separate 0.3.0 and 0.2.0 simulator results remain below. Compilation does not establish native rendering, settings persistence, runtime memory, physical-watch installation, store acceptance or battery life. Earlier local candidates and all desktop package identities remain separate.

## Supported setup

Use Garmin's [SDK download](https://developer.garmin.com/connect-iq/sdk/) and [Getting Started](https://developer.garmin.com/connect-iq/connect-iq-basics/getting-started/) instructions. Complete the official SDK Manager's private Garmin Connect sign-in, acquire SDK 9.2.0 and the exact `fenix9pro47mm` device package with fonts, and select that SDK as active. The inspected official setup does not establish a fresh noninteractive download route. Do not substitute an unofficial downloader, guessed endpoint or another device identifier.

The [command-line setup](https://developer.garmin.com/connect-iq/reference-guides/monkey-c-command-line-setup/) requires Java 11 or newer. A verified vendor runtime archive can be kept local to the build without changing system PATH. The build command below selects its Java directory for the compiler process only.

Garmin also requires an RSA 4096-bit developer key to sign compiled programs. Keep the private key outside this repository and its build outputs. Follow Garmin's key-generation instructions and retain the key privately for future updates. Do not commit, copy into a source archive or export an existing key for this build.

## Generate and compile

The palette generator maps the validated semantic roles in `tokens-monochrome.json` to Monkey C constants. It does not modify the desktop tokens or `dist/`. Explicit `--tokens tokens.json --output NEW_FILE` can generate the earlier palette colors for inspection without replacing the current generated source.

```powershell
python -m themeforge.garmin
python -m themeforge.garmin --check
python garmin/build.py --sdk C:/path/to/installed-sdk --java-bin C:/path/to/runtime/bin --key C:/private/developer_key.der --output-dir outputs/garmin-build-01
```

Use a new output directory for each build. The wrapper preserves previous output, checks the generated palette, selects only `fenix9pro47mm`, captures compiler diagnostics and records a nonempty program's checksum after a successful compiler result. Its Java process uses headless mode, limits the heap to 1 GiB and sets the JVM's active processor count to two. It does not download packages, generate keys, install an app or launch a simulator. A program's file size is not its runtime memory use.

Add `--tests` to compile the annotated Monkey C tests. That includes tests in a program without running them. Garmin's [unit-test framework](https://developer.garmin.com/connect-iq/core-topics/unit-testing/) executes in its simulator. Simulator execution requires a separately suitable environment and must not silently launch on an occupied desktop.

## Appearance and rendering

The system Watch Face configuration menu offers Appearance, Layout, Left data and Right data. Its appearance submenu and the declared application setting use the same persistent `appearance` property: 0 for Clair and 1 for Obscur. The default is Obscur. Layout uses its own persistent `layout` property: 0 for Analog, the new default, and 1 for Digital. Missing or invalid layout values use Analog. Existing appearance and information choices keep their property names and values. Invalid menu selections do not overwrite a saved choice. Choosing an item saves it and returns to the face. Back cancels the highlighted choice. Settings changes request a fresh drawing. These are source contracts pending current-version native interaction and restart checks.

Time follows the device's 12/24-hour preference, with AM/PM on the compact calendar line when needed. Date and time share one local Gregorian snapshot so an update cannot mix opposite sides of midnight. Battery percentages are truncated to whole percentages, and invalid or unavailable values display `--%`. The target runtime required an explicit NaN rejection before numeric conversion. That reproduced defect and its regression remain part of the candidate.

The digital layout requests Garmin's native Bionic Bold for time and data values, Roboto Medium for calendar and battery, and Roboto Condensed for field labels and detail. The analog layout uses Roboto Medium for values, date and charge, with Roboto Condensed for labels and detail. The view reads the device's 0.80 to 1.35 font-scale preference and caches fonts for the selected layout only. It includes scaled platform-font fallbacks when a requested face is unavailable. Every selection measures width and height before clipped drawing. Analog information fields choose all three row fonts together so the complete group fits its smaller band. If no measured combination fits, that field stays blank. Exact glyph fit and unavailable-field visibility still need current-version native inspection. No font binaries are bundled. Inter is not claimed to be available on the watch.

The analog dial uses original baton markers, a double marker at twelve, a quiet minute track and distinct hour and minute hands. The hour hand advances with the minutes. Date sits above the center, information fields below it, and watch charge near six. Hands draw last with an opposing edge so time remains legible when a hand crosses text. Inner readings can be temporarily obscured by a hand. Digital remains available when uninterrupted data reading matters more than an analog dial. There is no seconds hand or added one-second timer.

The visual direction uses a clear time hierarchy and restrained secondary information. The original digital references included the [MoMA Max Bill kitchen clock](https://www.moma.org/collection/works/139247), [Braun AW10](https://braun-clocks.com/products/aw-10-classic-watch-with-leather-strap) and [Hamilton Khaki Field](https://www.hamiltonwatch.com/en-us/h69439931-khaki-field-mechanical.html). The analog design also draws on the legibility priorities described for the [Rolex Explorer](https://www.rolex.com/watches/explorer/features), the simple indices of the [Oyster Perpetual](https://www.rolex.com/watches/oyster-perpetual/features), [Omega's black-dial Aqua Terra](https://press.omegawatches.com/a-classic-in-three-sizes-introducing-the-seamaster-aqua-terra-black-dial/) and the restrained display of the [IWC Mark XX](https://www.iwc.com/us-en/watches/pilot-watches/iw328201-pilots-watch-mark-xx). These are manufacturer descriptions of design features, not a comparative legibility study. The face uses its own geometry and no manufacturer logos or dial artwork. No universal best-design or endorsement claim is made.

## Information fields

Each field independently selects Weather, Steps or Body Battery. The defaults are Weather on the left and Steps on the right. The persistent `leftData` and `rightData` values use 0, 1 and 2 respectively. Missing or invalid choices fall back to that field's default.

- Weather reads Garmin's cached current conditions. It converts Celsius once when Fahrenheit is selected and shows the cache age. Observations older than two hours are marked stale by this face's policy. This is not a promise about Garmin's refresh interval. Missing, future or invalid timestamps remain age unknown.
- Steps reads the native activity-monitor count and an available positive goal. A real zero remains zero. Missing or invalid data shows an unavailable state.
- Body Battery reads the native Garmin complication provider. It subscribes only when a field selects it, retains the callback while subscribed and unregisters it when deselected or the app stops. It remains labeled as a Garmin score, separate from the watch's charge.

The manifest adds only `ComplicationSubscriber` for this data access. It does not request direct sensor or sensor-history access. The APIs are described in Garmin's [Complications](https://developer.garmin.com/connect-iq/api-docs/Toybox/Complications.html), [ActivityMonitor](https://developer.garmin.com/connect-iq/api-docs/Toybox/ActivityMonitor.html) and [Weather](https://developer.garmin.com/connect-iq/api-docs/Toybox/Weather.html) references. Always-on and Off drawing return before active field reads.

Every drawing clears the previous frame. Watch-face low-power callbacks and the actual display mode gate the sparse view. An off display or mismatched geometry produces black. Unknown modes use the sparse view. The always-on time is clipped to at most 192 by 64 pixels, moves among bounded minute positions and has no date, battery, label or bright active background. It tries a smaller platform font if the first does not fit. If neither fits, it remains black until a later update rather than spilling outside the bound.

The public [device reference](https://developer.garmin.com/connect-iq/articles/device-reference/fenix9pro47mm.html) documents a 454 by 454 round display and a 131,072-byte watch-face memory budget. The installed exact-target metadata confirms those values. The admitted 192 by 64 rectangle is a conservative source-level bound below 10% of the round visible area, even if every admitted pixel were lit. The host geometry check counts pixel centers within an ideal circle and obtains an upper bound of about 7.59%. It does not measure native text pixels or runtime luminance.

The current watch Obscur canvas and the separate always-on canvas are both `#000000`. Their rendering paths remain distinct. The preserved desktop packages retain their earlier `#090909` canvas. Garmin's [detailed AMOLED guidance](https://developer.garmin.com/connect-iq/articles/connect-iq-faq/How_Do_I_Make_a_Watch_Face_for_AMOLED_Products.html) distinguishes older pixel-protection rules from later-device luminance rules. The conservative pixel requirement here does not establish the exact target's firmware enforcement, burn-in flag or aging interval. Those remain part of target qualification.

## Current 0.4.0 qualification

On October 19, 2026, normal and test-enabled 0.4.0 programs compiled for the exact target without compiler warnings. An initial compile rejected three explicitly typed local declarations. The correction uses inferred local types and preserves the font-selection logic. Four new annotated test groups cover analog geometry, minute and marker positions, all 720 minute positions in a twelve-hour cycle, and layout-setting validation. They are compiled tests, not executed simulator results.

Host checks separately bind the analog geometry and resource settings to source, preserve the existing digital layout checks and verify that the complete always-on function remains unchanged from 0.3.0. These checks do not render Garmin fonts. Current-version simulator rendering, all 20 test groups, menu operation, layout and appearance persistence, font scales, hand and information overlap, missing providers and runtime memory remain unexecuted. The existing 0.3.0 program, transfer record and simulator evidence remain intact. No 0.4.0 program has been installed on the physical watch by this change.

## Preserved 0.3.0 qualification

On October 19, 2026, the normal and test-enabled 0.3.0 programs compiled for the exact target without compiler warnings. All 16 annotated test groups passed in that target's simulator. Bounded native observations exercised active Obscur, switching to Clair, Clair to Always-On, returning to active Clair, and switching back to Obscur. The always-on state displayed only a small time on black, without date, battery or information fields. The host-owned configuration menu retained Garmin's own colors.

The final active status sample was 19.2 kB against the displayed 123.9 kB budget. Menu samples were 20.4 and 21.3 kB. These are observed samples, not a peak or sustained memory measurement. The simulator was left in Obscur with Weather and Steps, battery 50 percent and High Power before closing. No pre-test persistent-property backup was captured, so this does not establish exact restoration of every earlier simulator setting. A new 0.3.0 normal-restart trial and physical-watch acceptance remain open.

The normal 0.3.0 program was copied to the physical watch and read back with an exact SHA-256 match. The user later reported having the watch face on the Garmin. That is a user report of presence, separate from inspecting its exact displayed version, appearance switching, low-power behavior, persistence or power use. Returning the transfer USB mode from MTP to its previous Garmin setting remains outstanding.

## Preserved 0.2.0 simulator checks and remaining acceptance

The accepted 0.2.0 simulator history below does not establish a new 0.3.0 runtime pass. The 16 simulator test groups cover the original time, calendar, invalid-value, appearance and geometry cases, plus field formatting, font-scale validation, data settings and layout bounds. The first native execution exposed the battery NaN conversion failure. Its explicit rejection was verified before the expanded candidate passed. Pure test groups do not themselves execute every provider lifecycle or inspect pixels.

Native simulator observations covered both active appearances at scale 1.35, 12/24-hour switching, a return to scale 1.00, Weather cache-age labels, Steps and a changing Body Battery value. Appearance selection returned to the face. Canceling a highlighted Weather choice retained the previously saved Body Battery field. A complete simulator exit and relaunch of the same program retained Obscur and both selected fields.

High Power to Always-On removed all active information and showed only time on black. Observed minute changes moved the time. Always-On to Off cleared the display, and Off to High Power restored the selected fields. The simulator's separate Sleep Mode preference left the face active under explicit High Power. That observation does not establish that a watch-face low-power callback fired. Hardware sleep/wake behavior remains open.

Observed runtime memory was 19.5 kB with a 23.6 kB peak against the simulator's displayed 123.9 kB budget. A fresh simulator process showed 19.2 kB with a 21.1 kB peak. The memory inspector reported zero new resource allocations in its sampled last update. These bounded samples do not establish long-term leak freedom or power consumption.

The scoped simulator settings were restored to Obscur, 12-hour time, font scale 1.00, High Power, Sleep Mode unchecked and watch battery 50 percent. The new fields were returned to their Weather and Steps defaults. Peak detection was unchecked in the fresh process, menus were closed, and the simulator and memory inspector were closed. SDK resources and unrelated applications were retained.

Rebuild with the identified compiler and exact device package after source changes. Worst-case native glyph widths, every field combination, missing live providers, language coverage, full low-power callback behavior and sustained memory behavior are not exhaustively qualified. The package's simulator metadata declares screen-protection support, but this does not establish firmware enforcement, physical aging or burn-in prevention.

Hardware acceptance, always-on behavior under the watch's settings, restoration, power use and physical readability are separate. Do not infer them from a build, a host geometry calculation or the desktop theme's earlier native observations.
