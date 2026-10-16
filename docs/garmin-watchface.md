# Clair and Obscur watch-face candidate

This separate Connect IQ watch-face source targets `fenix9pro47mm`, the fēnix 9 Pro 47 mm AMOLED. It displays local time, an ISO local date and battery percentage. The active view uses the shared Clair or Obscur palette. A separate always-on view clears to true black and draws only the time.

The source is a candidate pending exact-target compilation and runtime acceptance. Host Python checks do not execute Monkey C. No simulator, watch installation, store submission or battery-life claim follows from those checks. Existing desktop packages and their versions remain separate.

## Supported setup

Use Garmin's [SDK download](https://developer.garmin.com/connect-iq/sdk/) and [Getting Started](https://developer.garmin.com/connect-iq/connect-iq-basics/getting-started/) instructions. Complete the official SDK Manager's private Garmin Connect sign-in, acquire SDK 9.2.0 and the exact `fenix9pro47mm` device package with fonts, and select that SDK as active. The inspected official setup does not establish a fresh noninteractive download route. Do not substitute an unofficial downloader, guessed endpoint or another device identifier.

The [command-line setup](https://developer.garmin.com/connect-iq/reference-guides/monkey-c-command-line-setup/) requires Java 11 or newer. A verified vendor runtime archive can be kept local to the build without changing system PATH. The build command below selects its Java directory for the compiler process only.

Garmin also requires an RSA 4096-bit developer key to sign compiled programs. Keep the private key outside this repository and its build outputs. Follow Garmin's key-generation instructions and retain the key privately for future updates. Do not commit, copy into a source archive or export an existing key for this build.

## Generate and compile

The palette generator maps the validated semantic roles in `tokens.json` to Monkey C constants. It does not modify the desktop tokens or `dist/`.

```powershell
python -m themeforge.garmin
python -m themeforge.garmin --check
python garmin/build.py --sdk C:/path/to/installed-sdk --java-bin C:/path/to/runtime/bin --key C:/private/developer_key.der --output-dir outputs/garmin-build-01
```

Use a new output directory for each build. The wrapper preserves previous output, checks the generated palette, selects only `fenix9pro47mm`, captures compiler diagnostics and records a nonempty program's checksum after a successful compiler result. It does not download packages, generate keys, install an app or launch a simulator. A program's file size is not its runtime memory use.

Add `--tests` to compile the annotated Monkey C tests. That includes tests in a program without running them. Garmin's [unit-test framework](https://developer.garmin.com/connect-iq/core-topics/unit-testing/) executes in its simulator. Simulator execution requires a separately suitable environment and must not silently launch on an occupied desktop.

## Appearance and rendering

The system Watch Face configuration menu offers Clair and Obscur. Both it and the declared application setting use the same persistent `appearance` property. The default is Obscur. Invalid or unavailable read values use Obscur, and invalid menu selections do not overwrite the saved choice. Settings changes request a fresh drawing.

Time follows the device's 12/24-hour preference. The date and time share one local Gregorian snapshot so an update cannot mix opposite sides of midnight. Battery percentages are truncated to whole percentages, and invalid or unavailable values display `--%`. The candidate uses platform fonts. It does not bundle Inter or claim that Inter is available on the watch.

Every drawing clears the previous frame. Sleep callbacks and the actual display mode gate the low-power view. An off display or mismatched geometry produces black. Unknown modes use the sparse view. The always-on time is clipped to at most 144 by 64 pixels, moves among bounded minute positions and has no date, battery, label or bright active background. If the target font does not fit that box, it remains black until a later update rather than spilling outside the bound. Font fit and readable placement still need exact-target runtime inspection.

The public [device reference](https://developer.garmin.com/connect-iq/articles/device-reference/fenix9pro47mm.html) documents a 454 by 454 round display and a 131,072-byte watch-face memory budget. The admitted 144 by 64 rectangle is a conservative source-level bound below 10% of the round visible area, even if every admitted pixel were lit. The host geometry check uses actual pixel centers within the circle. It does not measure native text pixels or runtime luminance.

The desktop Obscur canvas is `#090909`. The always-on canvas is separately `#000000`. Garmin's [detailed AMOLED guidance](https://developer.garmin.com/connect-iq/articles/connect-iq-faq/How_Do_I_Make_a_Watch_Face_for_AMOLED_Products.html) distinguishes older pixel-protection rules from later-device luminance rules. The conservative pixel requirement here does not establish the exact target's firmware enforcement, burn-in flag or aging interval. Those remain part of target qualification.

## Acceptance still required

Compile the normal and test programs with the identified compiler and exact installed device package. In a suitable simulator, run the annotated tests and inspect both active appearances, 12/24-hour transitions, midnight and year changes, invalid data and settings, saved selection after application restart, menu cancellation, sleep/wake/off transitions and worst-case time widths. Inspect AOD clearing, clipping and placement, then measure runtime memory against the watch-face budget. Record the installed device package, compiler and resources with the result.

Hardware acceptance, always-on behavior under the watch's settings, restoration, power use and physical readability are separate. Do not infer them from a build, a host geometry calculation or the desktop theme's earlier native observations.
