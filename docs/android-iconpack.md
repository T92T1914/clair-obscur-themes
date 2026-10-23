# Obscur Android icon-pack candidate

The separate 0.1.7 Android candidate prepares the 0.24.0 Obscur artwork for icon-pack consumers. It contains 292 original 512-pixel drawings and 1,332 explicit component mappings. Those mappings cover 256 of the 268 named app packages and 14 public system-app package identities across 13 general functions. Twelve named packages still have no qualified alias in this candidate. A package hint alone is not an automatic assignment.

This version refines Dunkin, Samsung Pass, Sonic and VA without adding apps or aliases. The retained 0.1.6 update refined Proton Pass as artwork 0.23.0. The retained 0.1.5 update refined Threads, Evernote, MyRadar and Goodreads as artwork 0.22.0. The retained 0.1.4 update refined seven other drawings as artwork 0.21.0. All 1,332 component mappings and the public package-query scope remain unchanged. The retained 0.1.3 video-editing update added ten drawings and 22 exact component declarations from the same pinned Lawnicons source. Those historical upstream declarations and the separately dated launcher observations do not establish the phone's current launcher identities. The updated APK still needs its own local coverage and Theme Park check. The original 0.1.0, 0.1.1, 0.1.2, 0.1.3, 0.1.4, 0.1.5 and 0.1.6 APKs and earlier artwork packages remain separate retained versions.

This is an Obscur pack. Earlier icon collections remain unchanged. The pack adds no wallpaper, keyboard behavior, system font, notification service or theme engine. It does not replace the manual PNG bundle or publish a Galaxy Store product.

## Inputs and build

Use Python 3.11 or newer, a full JDK 17, Android SDK platform 36 and Build Tools 36.1.0. Select their paths explicitly. The build uses AAPT2, javac, D8, zipalign and, when signing is requested, apksigner. It does not install an SDK, alter PATH, start an emulator or contact a device.

The current 0.24.0 candidate uses the qualified PNG export with manifest SHA-256 `40fe3a771b39d9e73adf583dd060f660ef85c88ff961f80a3e3b3635e0f11cb2`. Independent readback hashed and parsed all 584 SVGs and decoded all 1,168 PNGs. Eight SVGs and 16 PNGs change for the four selected drawings. The other 576 SVGs and 1,152 PNGs retain their exact 0.23.0 bytes. Actual saved images were inspected at 24, 32, 48, 64 and 128 pixels in both appearances, following the complete catalog review and private comparisons. These asset checks are separate from APK resource readback, recognition, launcher masking and phone acceptance.

The retained 0.1.6 candidate used the qualified PNG export with manifest SHA-256 `2a773020fed10ddb2cd7c47d1c462cedfa6071240d2b0e94565cd599428cb8e8`. Independent readback hashed and parsed all 584 SVGs and decoded all 1,168 PNGs. Two SVGs and four PNGs change for Proton Pass. The other 582 SVGs and 1,164 PNGs retain their exact 0.22.0 bytes. Actual saved images were inspected at 24, 32, 48, 64 and 128 pixels in both appearances. These source and asset checks are separate from APK resource readback, recognition, launcher masking and phone acceptance.

The retained 0.1.5 candidate used the qualified PNG export with manifest SHA-256 `9b2fcc10732f4af1489bb20300a08702575d09f92b40f86d3956bb27dc97b303`. Independent readback hashed and parsed all 584 SVGs and decoded all 1,168 PNGs. Eight SVGs and 16 PNGs change for the four selected drawings. The other 576 SVGs and 1,152 PNGs retain their exact 0.21.0 bytes. Actual saved images were inspected at 24, 32, 48, 64 and 128 pixels in both appearances. These source and asset checks are separate from the APK build, recognition, launcher masking and phone acceptance.

The retained 0.1.4 candidate used the qualified 0.21.0 PNG export with manifest SHA-256 `9851eb483c8588db4712bdabbe73248f43ba8749fd59193da96680c99ce7c636`. Independent readback hashed and parsed all 584 SVGs and decoded all 1,168 PNGs. Exactly fourteen SVGs and 28 PNGs changed for the seven selected drawings. The other 570 SVGs and 1,140 PNGs retain their exact 0.20.0 bytes. Actual saved images were inspected at 24, 32, 48, 64 and 128 pixels in both appearances. These source and asset checks are separate from the APK build, recognition, launcher masking and phone acceptance.

The retained 0.1.3 candidate used the 0.20.0 PNG export whose `manifest.json` has SHA-256 `8c7a1f9b76413ecc8886b8cc66244096b42ccba0ad116d40ef626a50a23cf47a`. All 1,168 saved images were independently decoded and checked against their hashes, dimensions, transparent margins and neutral pixel values. All 1,128 previous PNGs retain their exact 0.19.0 bytes. The 40 added PNGs supply ten new drawings in both appearances and both export sizes. The saved 512-pixel images were inspected at 24, 32, 48, 64 and 96 pixels in both appearances. These asset checks do not establish recognition, masking or readability on a phone. The Android build and actual consumer checks remain separate. The generator checks the SVG source identities, catalog and complete PNG inventory before copying artwork. An export from another browser can have different raster bytes and is not silently admitted. Qualify that export explicitly before changing the source pin.

The retained 0.1.2 candidate used the qualified 0.19.0 export with manifest SHA-256 `728c13ef9aaf57afaa3291e740900dbba59bb916cefbc4a02bc9688be9620662`. All 1,128 saved images were independently decoded and checked against their hashes, dimensions, transparent margins and neutral pixel values. Its 1,124 previous PNGs retained their exact 0.18.0 bytes. The 0.1.1 candidate used the 0.18.0 export with manifest SHA-256 `0731e00b9922ada5537f5258fa9d24ea9f50b7eec6a43098fdc911a4c4bc23aa`. These pins and the earlier 0.17.0 artwork remain historical identities.

From the repository root, with local paths substituted:

```powershell
python android/build.py --png-dir "C:/work/qualified-0.24/png" --sdk "C:/tools/android-sdk" --java-bin "C:/tools/jdk-17/bin" --output-dir "C:/work/builds/android-iconpack-01"
```

The default result is unsigned and cannot be installed as a new Android app. For a signed candidate, provide an existing private Android keystore outside the repository and the name of an environment variable containing its password:

```powershell
python android/build.py --png-dir "C:/work/qualified-0.24/png" --sdk "C:/tools/android-sdk" --java-bin "C:/tools/jdk-17/bin" --output-dir "C:/work/builds/android-iconpack-signed-01" --keystore "C:/private/obscur-icons.jks" --ks-pass-env OBSCUR_KEYSTORE_PASSWORD
```

Keep the same private key for later updates. Never commit or redistribute it, use a watch developer key, or put its password in a command argument. This command reads the named environment variable. It does not create or export a key.

Every attempt needs a fresh output directory outside the repository. Existing output, linked paths, managed package output and source collisions are refused. Logs, intermediate files and `build.json` remain available after a failed attempt. The builder bounds Java memory and workers, disables GUI use and annotation processing, and selects the supplied SDK rather than an ambient command on PATH.

The generated project contains exact artwork copies, both XML and asset forms of `appfilter.xml`, a manual drawing index and the supported public package catalog. AAPT2 runs with PNG crunching disabled. Final checks compare all 292 APK PNGs and packaged assets with the prepared project, read the compiled component mappings and package identity, and verify alignment. A signed build also runs apksigner verification. These are local packaging checks, not phone acceptance or store approval. The tool contracts are documented by [AAPT2](https://developer.android.com/tools/aapt2), [D8](https://developer.android.com/tools/d8), [zipalign](https://developer.android.com/tools/zipalign) and [apksigner](https://developer.android.com/tools/apksigner).

## Apply through the actual consumer

The Android package is `io.github.t92t1914.obscuricons`, labeled Obscur Icons, with version code 8, minimum API 26 and target API 36. It declares no permissions. An installation still requires the device owner's approved Android installation path. Do not change security settings or replace an unrelated application to force installation.

After installation, open the installed Theme Park version's Icon editor and its Iconpack chooser. If Obscur Icons appears under third-party packs, select it, inspect the preview and save a new local theme. Record the previous selection before applying. Retain the existing theme for restoration. Inspect cover and inner screens, the app drawer, folders, label readability and several mapped apps. Recognition, automatic assignment, masking and persistence must be observed on the actual phone. If the chooser does not recognize the pack, retain that result rather than treating a successful APK build as consumer acceptance.

The pack supplies explicit component-to-drawing mappings. It does not guess a `MainActivity`, replace every unmatched app with one generic picture, or promise to cover every app in a store. Dynamic icons and launcher-specific extensions are not implemented. An app update or alias change can leave a previously known package unmapped. [Component sources and limits](android-iconpack-sources.md).

## Local coverage check

The launchable app explains how to apply the pack and offers Check icon coverage. That button compares visible launcher components only within the public supported package list. The manifest's narrow package queries are generated from that same list. It does not request `QUERY_ALL_PACKAGES` or enumerate unrelated packages.

The check displays counts and any visible supported components lacking an exact mapping. It does not upload, log or save those observations, and it starts no persistent service. No visible launcher entry can mean a package is absent or has no visible entry. The result cannot prove which pictures Theme Park applied. Preserve any device observations privately and use only the missing non-sensitive component facts needed for a deliberate later mapping change.

The public source snapshot explicitly includes the app, build command, mapping table and license notices. SDKs, signing keys, compiled APKs and local build outputs stay outside that inventory. Existing desktop packages, SVG archives and release gates are unchanged.
