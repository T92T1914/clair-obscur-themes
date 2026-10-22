# Obscur Android icon-pack candidate

The separate 0.1.2 Android candidate prepares the 0.19.0 Obscur artwork for icon-pack consumers. It contains 282 original 512-pixel drawings and 1,310 explicit component mappings. Those mappings cover 246 of the 258 named app packages and 14 public system-app package identities across 13 general functions. Twelve named packages still have no qualified alias in this candidate. A package hint alone is not an automatic assignment.

Gboard adds one original drawing and four exact component declarations from the same pinned Lawnicons source. All 1,306 previous mappings remain unchanged, including the 11 launcher aliases observed on October 21, 2026. Those observations retain their separate source and date. The four Gboard declarations may include historical, setup or reactivation entries, so their presence does not establish the phone's current launcher identity. The updated APK needs another local coverage and Theme Park check. The original 0.1.0 and 0.1.1 APKs and earlier artwork packages remain separate retained versions.

This is an Obscur pack. Earlier icon collections remain unchanged. The pack adds no wallpaper, keyboard behavior, system font, notification service or theme engine. It does not replace the manual PNG bundle or publish a Galaxy Store product.

## Inputs and build

Use Python 3.11 or newer, a full JDK 17, Android SDK platform 36 and Build Tools 36.1.0. Select their paths explicitly. The build uses AAPT2, javac, D8, zipalign and, when signing is requested, apksigner. It does not install an SDK, alter PATH, start an emulator or contact a device.

The input is the qualified 0.19.0 PNG export whose `manifest.json` has SHA-256 `728c13ef9aaf57afaa3291e740900dbba59bb916cefbc4a02bc9688be9620662`. All 1,128 saved images were independently decoded and checked against their hashes, dimensions, transparent margins and neutral pixel values. All 1,124 previous PNGs retain their exact 0.18.0 bytes. The generator checks the SVG source identities, catalog and complete PNG inventory before copying artwork. An export from another browser can have different raster bytes and is not silently admitted. Qualify that export explicitly before changing the source pin.

The previous 0.1.1 candidate used the 0.18.0 export with manifest SHA-256 `0731e00b9922ada5537f5258fa9d24ea9f50b7eec6a43098fdc911a4c4bc23aa`. That pin and the earlier 0.17.0 artwork are historical identities, not accepted inputs for the current candidate.

From the repository root, with local paths substituted:

```powershell
python android/build.py --png-dir "C:/work/qualified-0.19/png" --sdk "C:/tools/android-sdk" --java-bin "C:/tools/jdk-17/bin" --output-dir "C:/work/builds/android-iconpack-01"
```

The default result is unsigned and cannot be installed as a new Android app. For a signed candidate, provide an existing private Android keystore outside the repository and the name of an environment variable containing its password:

```powershell
python android/build.py --png-dir "C:/work/qualified-0.19/png" --sdk "C:/tools/android-sdk" --java-bin "C:/tools/jdk-17/bin" --output-dir "C:/work/builds/android-iconpack-signed-01" --keystore "C:/private/obscur-icons.jks" --ks-pass-env OBSCUR_KEYSTORE_PASSWORD
```

Keep the same private key for later updates. Never commit or redistribute it, use a watch developer key, or put its password in a command argument. This command reads the named environment variable. It does not create or export a key.

Every attempt needs a fresh output directory outside the repository. Existing output, linked paths, managed package output and source collisions are refused. Logs, intermediate files and `build.json` remain available after a failed attempt. The builder bounds Java memory and workers, disables GUI use and annotation processing, and selects the supplied SDK rather than an ambient command on PATH.

The generated project contains exact artwork copies, both XML and asset forms of `appfilter.xml`, a manual drawing index and the supported public package catalog. AAPT2 runs with PNG crunching disabled. Final checks compare all 282 APK PNGs and packaged assets with the prepared project, read the compiled component mappings and package identity, and verify alignment. A signed build also runs apksigner verification. These are local packaging checks, not phone acceptance or store approval. The tool contracts are documented by [AAPT2](https://developer.android.com/tools/aapt2), [D8](https://developer.android.com/tools/d8), [zipalign](https://developer.android.com/tools/zipalign) and [apksigner](https://developer.android.com/tools/apksigner).

## Apply through the actual consumer

The Android package is `io.github.t92t1914.obscuricons`, labeled Obscur Icons, with version code 3, minimum API 26 and target API 36. It declares no permissions. An installation still requires the device owner's approved Android installation path. Do not change security settings or replace an unrelated application to force installation.

After installation, open the installed Theme Park version's Icon editor and its Iconpack chooser. If Obscur Icons appears under third-party packs, select it, inspect the preview and save a new local theme. Record the previous selection before applying. Retain the existing theme for restoration. Inspect cover and inner screens, the app drawer, folders, label readability and several mapped apps. Recognition, automatic assignment, masking and persistence must be observed on the actual phone. If the chooser does not recognize the pack, retain that result rather than treating a successful APK build as consumer acceptance.

The pack supplies explicit component-to-drawing mappings. It does not guess a `MainActivity`, replace every unmatched app with one generic picture, or promise to cover every app in a store. Dynamic icons and launcher-specific extensions are not implemented. An app update or alias change can leave a previously known package unmapped. [Component sources and limits](android-iconpack-sources.md).

## Local coverage check

The launchable app explains how to apply the pack and offers Check icon coverage. That button compares visible launcher components only within the public supported package list. The manifest's narrow package queries are generated from that same list. It does not request `QUERY_ALL_PACKAGES` or enumerate unrelated packages.

The check displays counts and any visible supported components lacking an exact mapping. It does not upload, log or save those observations, and it starts no persistent service. No visible launcher entry can mean a package is absent or has no visible entry. The result cannot prove which pictures Theme Park applied. Preserve any device observations privately and use only the missing non-sensitive component facts needed for a deliberate later mapping change.

The public source snapshot explicitly includes the app, build command, mapping table and license notices. SDKs, signing keys, compiled APKs and local build outputs stay outside that inventory. Existing desktop packages, SVG archives and release gates are unchanged.
