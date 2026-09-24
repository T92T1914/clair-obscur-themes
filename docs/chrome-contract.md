# Native Chrome contract

Clair and Obscur are separate native themes for ordinary Google Chrome. Each generated directory contains a Manifest V3 `manifest.json`, an original 128-pixel PNG icon and `LICENSE.txt` with the complete MIT grant from the repository's canonical license. The browser backgrounds use flat colors. There is no page script, service worker, permission, font file, remote asset, new-tab replacement or search change in either package. Chrome's [theme documentation](https://developer.chrome.com/docs/extensions/develop/ui/themes) describes native themes as packages without HTML or JavaScript.

## Supported mapping

The implementation uses the color keys in Chromium's `kOverwritableColorTable`, the reference linked by Chrome's theme documentation. The reviewed source is [browser_theme_pack.cc at 8646dc6](https://chromium.googlesource.com/chromium/src/+/8646dc6a8ca2e0277caa01f06300e3c170033aac/chrome/browser/themes/browser_theme_pack.cc), inspected on September 24, 2026. Its decoded UTF-8 source SHA-256 was `a79a7c720ec767f3458c2cb34dd227441ac26e7fabf8e1094a63904cef60bfa2`. This records a source contract, not a claim that a particular installed Chrome version rendered every key.

| Native Chrome field | Shared design role |
| --- | --- |
| `frame` | Canvas |
| `frame_inactive` | Control |
| `background_tab` | Control |
| `background_tab_inactive` | Selected surface |
| `toolbar` | Panel |
| `tab_text`, `toolbar_text`, `bookmark_text` | Primary text |
| `tab_background_text`, `tab_background_text_inactive` | Secondary text |
| `toolbar_button_icon` | Primary text |
| `button_background`, `omnibox_background` | Control |
| `omnibox_text` | Primary text |
| `ntp_background`, `ntp_text` | Canvas and primary text |
| `ntp_link`, `ntp_header` | Accent and divider |

Active tabs use Chrome's toolbar relationship. The family separates that panel from the surrounding frame and inactive tabs. Window inactivity receives a different surface while retaining readable secondary text. Chrome also derives colors and states. Focus rings, hovered icons, suggestion results, tab-group indicators, security indicators and operating-system titlebar controls need application checks. They are not separate promises of exact token control.

The packages deliberately omit Incognito color overrides and preserve native Incognito controls. Omission does not prove that every Incognito surface stays unchanged because Chrome can derive colors. Check recognition in the actual browser. There are no theme fields for arbitrary UI fonts, tab geometry, website styling or Reading mode typography in the reviewed contract. Inter remains the proportional font on surfaces the project controls. Chrome retains its native browser fonts.

## Build boundary

`build_theme(name, tokens, destination, version)` returns `destination/name.lower()`. Names are restricted to Clair and Obscur. The function validates the consumed semantic colors, accepts only six-digit RGB hex values, and converts them into integer RGB arrays. Unmapped tokens are not serialized into the manifest.

Versions follow Chrome's [version rules](https://developer.chrome.com/docs/extensions/reference/manifest/version): one to four integer components, each no larger than 65535, without leading zeroes and not all zero. Invalid input fails before output creation. Existing directories containing unrelated files or a different manifest are rejected. Individual files use temporary writes followed by replacement. A repeated build with identical inputs produces identical bytes in the tested environment.

The small icon is an original page emblem drawn from the same tokens. It has a 96 by 96 pixel face within a 128 by 128 transparent canvas and an sRGB PNG marker. It contains no text, font, private metadata or third-party artwork. Chrome documents [128-pixel icons for themes and extensions](https://developer.chrome.com/docs/extensions/reference/manifest/icons). This icon identifies the package. It does not recolor website favicons or replace browser controls.

## Local installation and rollback

Use an isolated test profile in the installed stable Google Chrome. Do not copy an everyday profile or its authentication data. Extract the native theme ZIP, then open `chrome://extensions`, enable Developer mode in that test profile, choose **Load unpacked**, and select the directory containing `manifest.json`. This uses Chrome's documented [unpacked development workflow](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked). An extracted developer package is not a one-click store installation.

Inspect `chrome://settings/appearance` and the actual frame after installation. Test Obscur first, then Clair with equal coverage. For rollback, use **Settings > Appearance > Reset to default**, the [documented theme removal route](https://support.google.com/chrome_webstore/answer/148695). Installing a theme replaces the active theme in that profile. Testing in isolation avoids replacing a user's existing choice or syncing a candidate to another computer.

Record the exact browser version, package hash, active profile, installed-theme confirmation and removal result. Exercise active/inactive tabs, bookmarks, the address bar and suggestion list, new tabs, multiple windows, window focus changes, tab groups, downloads, and Incognito recognition. Test windowed, split-screen and maximized sizes. A webpage screenshot cannot establish native frame appearance. Headless package checks cannot establish physical OLED rendering or reading comfort.

## Reading mode comparison

Chrome's [Reading mode help](https://support.google.com/chrome/answer/14218344?hl=en) documents font and size controls, color presets, line height, letter spacing, links and images. On Windows it can open through **More tools > Reading mode** or `Alt+Shift+R`. The help also warns that extraction is unsuitable for some interactive pages. It does not establish that arbitrary installed Inter faces, exact custom hex colors or a numerical reading width can be selected.

The installed browser must settle those questions. Open a public or synthetic article with headings, emphasis, links and code. Inspect the actual font and color menus. Compare extracted text and source order, inspect representative rendered fonts where diagnostics permit, resize the reading view, and test selected text on a page without useful extraction. Preserve the original page and keep read-aloud controls inactive during a visual check.

No companion is justified by documentation alone. If native Reading mode meets the requirement, use it. If actual inspection establishes a meaningful gap, record the missing capability before building the separately scoped optional reader. A reader's font or palette would apply to its own surface and would not alter these native themes.

## Store preparation and remaining gates

The release ZIP puts `manifest.json` at its root, alongside the icon and `LICENSE.txt`. Chrome's [preparation instructions](https://developer.chrome.com/docs/webstore/prepare) also require a concise description and increasing version numbers for updates. The ZIP is a development/upload artifact until the store accepts it.

An existing authorized publisher account can be reused. A new account requires registration, agreement acceptance and a one-time fee according to the [registration documentation](https://developer.chrome.com/docs/webstore/register). Developer accounts also need [2-Step Verification](https://developer.chrome.com/docs/webstore/program-policies/two-step-verification) before publication. This project does not pay fees, accept new agreements or change account security as part of a build.

Prepare an original 440 by 280 promotional image and at least one actual product screenshot at 1280 by 800 or 640 by 400, following the [store image requirements](https://developer.chrome.com/docs/webstore/images). Label ordinary previews as SDR captures. Never replace a missing native frame capture with a browser imitation. Listing text, privacy declarations, upload, review and public availability are distinct steps in the [publication process](https://developer.chrome.com/docs/webstore/publish).

The source and package tests establish the fields and bytes produced by this generator. Application acceptance, exact installed Reading mode behavior, publisher-account eligibility, store review, hardware viewing and participant comfort require their own recorded evidence. None is implied by the presence of these files.
