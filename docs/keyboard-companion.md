# Clair and Obscur keyboard companion 0.1.0

This companion contains optional Gboard background images and separate manual recipes for Gboard, Samsung Keyboard and a Samsung system palette. The website illustrations are design references. The ZIP and palette JSON are not native theme imports, an installable keyboard, a font installer or a complete Samsung system theme.

The companion version is independent of artwork 0.27.0 and the Clair/Obscur icon APKs. It does not change or apply those products.

## Included files

- `backgrounds/Clair-Gboard-Background.png`: opaque RGB, 2048 × 1024, pure white, SHA-256 `da5f4f92115ed5453a57c61d30221782246cec7de9ba70cdf8efeaa5da05f347`.
- `backgrounds/Obscur-Gboard-Background.png`: opaque RGB, 2048 × 1024, pure black, SHA-256 `633b9b88e1d2967c755519a84b1845f0d0ba8f392a4cca0715ac77df773b19d6`.
- `palette-reference.json`: intended monochrome roles from the maintained shared tokens. Apply only settings your native version exposes.
- This guide, project license, `manifest.json` and `SHA256SUMS`.

Both PNGs were originally prepared on October 22, 2026 and are reused byte for byte. No illustration, labels, private device record or font binary is included in a background. A solid image remains the same color after cropping. Native dimming, contrast treatment, key backgrounds and other controls may still change the final result.

The published preview includes these files at relative `keyboard/` paths and inside the portable preview kit. Keep the extracted directory together. The companion bundle contains its own exact files and checksums. The current source snapshot contains the maintained generator, guide and two admitted source PNGs. An original release source archive is a different historical download.

Use the external `bundle-SHA256SUMS` to compare the downloaded ZIP. After extraction, `SHA256SUMS` covers six content/manifest files and excludes itself. The ZIP contains seven files in total. It does not contain a copy of itself or its external checksum. Included checksums establish consistency with the captured files, not origin or native compatibility.

## Preserve the baseline first

Before a separately authorized phone session, record the actual phone/One UI, keyboard and module versions, current appearance and saved theme. Preserve default keyboard, languages, learned words, number row, layouts, key borders, correction settings, system font, saved themes and the working icon assignment. Nothing in this companion requires a reset, keyboard-data clearing, root, patched keyboard or changed key arrangement.

Native application remains unverified. Inspect the result on the relevant cover and inner displays. Keep a route back to the recorded selection before saving or applying a new draft.

## Gboard

1. Open Gboard settings, then Theme. Prefer an available native plain light or dark theme when it provides the intended result.
2. For an optional image background, use the matching solid PNG through the available photo route. Review crop/brightness and the existing key-border choice before Apply. The label on the download identifies the image independently of the website appearance.
3. Inspect ordinary and special keys, suggestions, punctuation and long-press symbols in the existing layout. Preserve the number row, languages, font and correction settings. The image does not control key geometry, native legend/suggestion colors, Enter/Search accents, live fonts, predictions or autocorrection.
4. Choose custom photo themes manually where needed. Automatic switching between two custom photo themes and a theme-file importer are not promised.
5. Normally reopen the keyboard and inspect persistence. If unsuitable, restore the recorded theme, photo and border choices. Do not delete learned words or reset the keyboard.

[Google's Gboard theme instructions](https://support.google.com/gboard/answer/6102154?hl=en) establish the theme/photo/color route. They do not establish this companion's phone result or extra per-role controls.

## Samsung Keyboard

1. Keep the current default keyboard and saved layout. Confirm which Theme Park/Keys Cafe modules and controls are available for the actual region/version.
2. Where supported, create a new separate design in Theme Park's Keyboard area, or use Keys Cafe's style controls with Theme Park. Retain the working design. Do not change key positions, effects or sounds to demonstrate colors.
3. Start with the matching field color and opposite legends. Use the palette reference only for exposed background/key colors. Maintain readable boundaries and visible native pressed, selected, disabled and focus cues. State must remain distinguishable through an outline, shape or native indicator, rather than tiny gray changes alone.
4. Inspect suggestions, toolbar, Enter/Search, long-press symbols and ordinary keys before saving/applying. An intended role is not a promise that the installed module offers an independent control for it.
5. Check both relevant displays, normal reopening, switching and restoration to the recorded working design. Retain an exact missing-control or contrast result rather than substituting an unsupported import.

Samsung's [Colombia guide, updated October 8, 2026](https://www.samsung.com/co/support/mobile-devices/change-keyboard-background/) describes Theme Park and Keys Cafe routes. Its [Australian guide, updated September 9, 2026](https://www.samsung.com/au/support/mobile-devices/customise-keyboard-background/) is explicitly regional and describes Keys Cafe with Theme Park. Their paths and screenshots do not establish identical controls on another region or module version. The [Theme Park store listing](https://galaxystore.samsung.com/detail/com.samsung.android.themedesigner) is a module reference, not a keyboard import specification. No supported desktop-generated native import format is claimed here.

## Samsung system palette and Quick panel

Keep this configuration reference separate from keyboard styling and icon-pack assignment. [Samsung India's Good Lock guide, updated October 1, 2026](https://www.samsung.com/in/support/mobile-devices/explore-good-lock-and-how-its-applications-enhance-your-samsung-device/) describes overall Theme Park colors and independent Quick Setting themes for notification-panel buttons and the brightness bar. Availability remains region/version dependent.

For Clair, aim for a white field, black foreground and neutral gray secondary information. For Obscur, aim for a black field, white foreground and neutral gray secondary information. Keep native active/selected indicators and sufficient text/boundary contrast. Apply only the actual exposed controls. Check buttons, brightness, selected/unselected and disabled states individually before retaining a separate draft. Restore the prior theme if required state information disappears.

The recipe does not establish control over every application, notification, lock-screen element or accent. It is not a Galaxy Store product, a complete native system theme or a device-wide font replacement.

## Font and correction limits

The controlled browser reference requests genuine locally installed Inter faces with a usable system fallback. It does not distribute fonts or establish Inter on a phone. Native Gboard/System default is not evidence that Inter is selected. Inter still needs authentic compatible provenance, actual supported selection and observed live key-label, suggestion, symbol and fallback glyphs.

An earlier bounded font-listing search did not establish a compatible Inter listing. That does not prove global unavailability. Do not substitute a different font, patch software or install an unqualified font package to satisfy the reference.

Appearance work does not fix or validate prediction/autocorrection. Preserve that separate unresolved question and the current correction settings and learned words.

## Illustrative role map

The browser's keys are noninteractive illustration elements. Field, ordinary key, primary/secondary legend, suggestions/toolbar, Enter/Search, pressed/selected, boundary/focus and disabled-legend roles come from `tokens-monochrome.json`. The JSON names the intended roles. Gboard's photo route maps only the field image. Samsung background/key color controls are version dependent. Other roles remain design targets until exposed native controls and actual rendering establish them.

| Role | Gboard image route | Samsung Keyboard |
| --- | --- | --- |
| Field | Supported background pixels | Background control documented, conditional on installed module |
| Ordinary key colors | Native theme owns them | Per-key colors documented, editors vary |
| Secondary labels, suggestions, toolbar, Enter legend | Native-owned | Individual editors not established here, design-only unless exposed |
| Pressed/selected, disabled, focus | Preserve native states | Preserve native states, independent editors not promised |
| Font, layout, correction | Separate settings, preserve them | Separate settings, preserve them |

The illustration preserves a familiar example row order to compare appearances. It is not an instruction to change a user's key positions, touch targets or layouts, and it does not measure typing speed, comfort or physical luminance.
