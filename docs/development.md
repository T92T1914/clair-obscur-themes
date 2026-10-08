# Build and verification

Python 3.11 or later builds the original four downloads and the new platform candidates using the standard library. Node 24 and the locked Playwright development dependency run the separate browser specimen tests. The new adapters and their native limits are described in [platform portability](platform-portability.md).

```powershell
py -3.11 -X utf8 -m unittest discover -s tests -v
py -3.11 -X utf8 build.py
py -3.11 -X utf8 build.py --check
npm ci --ignore-scripts --no-audit --no-fund
$env:THEME_REQUIRE_INTER = '1'
npm run test:browser
py -3.11 -X utf8 preview.py --output outputs\preview-0.1.1
```

Use `python` instead of `py -3.11` where the Windows launcher is unavailable. The exact Inter check requires all six local static faces. Without that requirement, an environment missing those faces reports the face-specific test as skipped and still tests system fallback. The browser suite never opens a visible browser or uses an ordinary profile. It defaults to installed Google Chrome. CI uses the Ubuntu 24.04 runner's installed Google Chrome in an isolated headless profile and logs its version. That still cannot replace the native Chrome check.

The runner explicitly keeps the Chromium sandbox enabled and mutes audio. It records the requested launch configuration and observed browser process version. The Inter check requests every declared face, records load failures, waits for layout and requires the intended PostScript face to supply actual glyphs in each specimen. Portable regressions reject mismatched or empty glyph evidence without installing a font. A font file on disk, successful direct-byte diagnostic or green fallback check cannot substitute for this installed-font result.

The CI browser uses packaged Chrome because Ubuntu already supplies its sandbox policy. A downloaded Chromium build failed at launch with no usable sandbox on this runner; the same page checks had not yet executed. The workflow does not disable the sandbox or change AppArmor to accommodate that build. See [Chromium's explanation of Ubuntu's policy](https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md) and the [runner browser inventory](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md#browsers-and-drivers).

The preview builder copies only verified release bytes and explicitly selected source categories. It rejects a stale or edited artifact. Repeating the same build is harmless. When the source changes, choose a fresh preview output directory so an existing candidate is not silently replaced. `site-manifest.json` describes the exact preview bytes.

The generated page offers `Clair-Obscur-portable-preview.zip` and `portable-SHA256SUMS`. Download the ZIP, extract it completely and open the extracted `index.html`. Keep the directory together when moving it. Both palette specimens, all target packages and the complete local installation, switching, removal and restoration procedures remain available offline, including without JavaScript. Online reference links still need a connection. Page controls only change the specimen, and the kit installs no application theme or font.

The kit uses the same captured, verified files as the published preview. Its inner `site-manifest.json` hashes every other extracted file. The ZIP uses sorted paths, fixed timestamps and regular-file permissions. Its external checksum and the public manifest identify the ZIP bytes. The archive does not contain itself or its external checksum, and its extracted page supplies local directory instructions instead of a broken self-download. Comparing SHA-256 values establishes matching bytes, not authenticated origin or native compatibility.

The extracted page shows each package's local path. Those theme files are already included and can be used directly for the target procedure. Chrome may save a local archive but display a CSS file when its link opens, even with a download attribute. Return to the preview after viewing that file. No duplicate download is needed to obtain the included CSS.

The browser kit check clicks the generated archive and checksum links, extracts that actual download, moves the complete directory and opens its `file:` page. It blocks external requests and exercises 320/390-pixel keyboard guide journeys with and without JavaScript. It verifies every included package against the artifact manifest, saves local archives, and opens CSS as byte-matching text before returning to the page. This establishes the checked headless browser's direct-file behavior. It does not replace target application installation or physical reading acceptance.

The installation procedures have one maintained source in `docs/installation.md`. The preview renders its nine target sections and shared client font section from the same captured bytes included in `source.zip`. Keep each target's Prerequisites and status, Install, Switch, Remove and restore, Fonts and Troubleshooting subheadings. The small renderer supports paragraphs, `###` headings, flat ordered/unordered lists, inline code, bold text and links. It escapes ordinary text and rejects unsupported block syntax or active link schemes. Relative documentation references become explicitly labeled online references. Essential procedure text and shared font guidance remain local.

Each existing download card links to its appearance's package identity and target procedure. Package version, filename, byte count and SHA-256 come from the verified artifact snapshot. The paired Opera GX card links both appearances to one unchanged package. The browser harness moves the freshly generated site into a separate relative location before serving it on loopback. Its local-guide check blocks external requests and exercises Tab/Enter, both page appearances, all target/appearance links, 320/390-pixel widths and JavaScript-disabled delivery. Those page checks do not install packages or satisfy native restoration.

The optional chooser combines an explicit Target with Package appearance. Target starts unselected, and Package appearance starts at Obscur. Package selection stays independent of the page's Preview appearance. A selection updates the package action, identity and matching guide without downloading, navigating or changing native settings. Clearing the target removes the resolved actions. The complete catalog remains below, and JavaScript-disabled delivery hides the uninitialized chooser.

Target options come from the same manifest-backed catalog labels. The script resolves the existing appearance-specific card link and clones its package action, identity, hash and target limits, with the relative file path displayed. It fetches no manifest and maintains no second package inventory. Chrome, Edge and Brave share their unchanged Chrome file while keeping distinct target guides. Both Opera GX appearances resolve to its one paired package and their separate guide destinations. In an extracted kit, the cloned action keeps Open included behavior and its existing CSS-opening instructions.

The optional local package checker reads one selected file and computes SHA-256 on the device. Its references are the existing generated guide hashes and catalog links, with one manifest-derived byte-count attribute on each card. It fetches no inventory and does not upload, persist or automatically open the selected file. All matching target and appearance guides remain separate, including Chrome aliases and both Opera GX appearances. Renaming exact package bytes does not change identification. Matching a captured reference does not authenticate origin or establish native compatibility.

The checker bounds reading by the largest captured package, currently 14,037 bytes. Source archives and the complete kit use their separate checksums. A bounded unknown file can show a computed digest with no match. Oversize selections, missing read/hash support, invalid reference metadata, read failures and hash failures explicitly remain uncomputed. Each selection or Clear owns a new generation, so a late completion or rejection from earlier work cannot replace the current state. The controls keep their focus, and checking does not change reading appearance or chooser selections. Browsers must provide local file reading and `crypto.subtle.digest` in the page's context. An unavailable browser receives the manual guide-checksum route. Actual positive hashing in served and relocated `file:` pages remains a separate browser acceptance check. JavaScript-disabled delivery retains the complete catalog and guide hashes.

After keyboard Enter, the guide check waits up to two seconds for the exact fragment and then up to two seconds for focus on that destination. Keyboard dispatch can finish before the navigation is observed. A correct URL with focus left on the link still fails. Controlled fixtures hold and release navigation and focus separately, and require bounded failures for absent navigation, a wrong fragment and wrong focus. They use no sleeps and do not repair the generated page's focus.

The earlier guide test failed once on the immediate URL read in branch-push run 37744729136 at source 32dd975710d8cf4481fb475c14eca49ea40b65c6. Later PR and main runs passed the same source tree. The retained log establishes that failed observation, but contains no trace proving its cause. The controlled fixtures demonstrate the harness's immediate-read exposure rather than reproduce that historical failure.

The displayed palette, verified downloads and source archive must use the same token values. The preview compares their canonical token digests and rejects a change between reads before writing output. Equivalent JSON formatting is allowed, and the source archive retains the captured file bytes. This check does not establish native application acceptance.

The standalone license download and source archive share one captured `LICENSE` file. Its normalized grant must match both Chrome packages and both Equicord CSS files before the preview is written. Equivalent Windows line endings and extra final newlines are accepted, while the source archive and standalone download keep the captured bytes. A changed grant requires a matching artifact build rather than a preview beside older package notices.

The same grant is checked for the Firefox packages, client CSS, Opera GX package and the license beside Vivaldi's unpacked settings. Client-qualified filenames avoid collisions when downloads share a flat release directory. Edge and Brave aliases deliberately refer to the same Chrome files. A different file with the same flat filename is refused.

Mozilla validation is separate from the standard-library contract tests. With `web-ext` 10.7.0 available as a development tool, run the following against each generated Firefox directory. It uses Mozilla's actual schemas, treats warnings as failures and does not discover personal configuration, install a theme or submit it for signing:

```powershell
web-ext --no-config-discovery lint --source-dir dist/firefox/clair --warnings-as-errors --output json
web-ext --no-config-discovery lint --source-dir dist/firefox/obscur --warnings-as-errors --output json
```

The browser download checks use separate eight-choice Clair and Obscur journeys and one single-choice paired Opera GX journey. A rapid twelve-click burst in one page reached Chromium's download throttle in the earlier retained diagnostic. The tests do not change download permissions or disable safeguards. Native theme installation and normal restart acceptance remain manual, separately authorized checks.

To serve a built preview locally:

```powershell
py -3.11 -m http.server 8765 --bind 127.0.0.1 --directory outputs\preview-0.1.1
```

This is a local development command, not a public deployment. Stop that server when finished. The portable kit opens from its extracted `index.html` without a server. Browser download policies can vary, so the direct-file check remains separate from loopback page checks.

The build pipeline stages complete outputs, validates their contents and only replaces an earlier tree when its manifest still matches every file. It refuses foreign files, modified artifacts and links. An interrupted lock is evidence to inspect, not a file to remove automatically while another build might be active.

If generation or installation fails, a secondary staging or lock cleanup error keeps the original failure and adds a short recovery note. Inspect any retained temporary files before retrying. If the build otherwise completed, a cleanup failure is reported normally. A complete newly installed tree remains available when later cleanup fails.

Preview staging follows the same failure contract. A failed write or caller interruption stays primary if retiring its temporary stage also fails. The command prints secondary cleanup notes, and retained stage files need inspection before retrying. An interruption after the preview rename may leave a complete output available. It does not establish successful command completion.

## Change the source, then regenerate

Edit `tokens.json` for shared colors and the selected `themeforge` module for platform mappings. `firefox.py` implements Mozilla's static contract. `discord_clients.py` adds narrow client states over the unchanged shared Equicord generator. `vivaldi.py` supplies minimal shareable settings; `opera_gx.py` supplies paired HSL hints and its original icon. Edit `web/` for the component specimen. Do not patch `dist/` or a generated preview. The original release remains 0.1.1, earlier adapters remain 0.2.0, and new browser adapters declare 0.3.0 separately. Preparing a combined release requires a deliberate version and distribution review.

The preview includes a source archive with an explicit allowlist. A README, installation guide or test change can legitimately alter that archive even when the four theme assets stay identical. The current-source snapshot is separate from the versioned source download, which points to the existing release. Inspect the snapshot's revision, working-tree status and SHA-256 in the generated page and `site-manifest.json`. Source extracted without Git history is labeled with an unavailable revision rather than assigned a guessed commit.

The portable kit also follows the captured current source. Its archive digest and byte count appear under `distribution.portable_kit` in the public manifest. The extracted manifest identifies its `portable-kit` distribution and retains that captured source identity. Neither kit delivery nor a preview documentation change assigns a new theme version or replaces the original release source.

CI uses `python preview.py --expected-revision <workflow-commit>` to require that exact clean source revision. Rebuild the site after source changes and review its new manifest. Do not copy old hashes into a new build or overwrite a published release's bytes.

The [CI workflow](../.github/workflows/checks.yml) deploys checked pushes to `main` automatically. Its tag publication gate refuses this mixed-version preview so separately versioned candidates cannot silently replace the original release. Prepare a deliberate family release before tagging. Manual Pages dispatch is an optional fallback. The [publication guide](publication.md#github-delivery) describes the checks, artifact provenance and environment gates. A local run, a remote workflow pass and a verified public download remain distinct results.

## Reading the evidence

Declared palette contrast, browser-rendered glyphs, native theme loading and physical display appearance are separate checks. `THEME_EVIDENCE_DIR` can retain local browser measurements and screenshots. These are ordinary headless page captures, with no HDR capture or physical display claim. Exact application and display acceptance remains in [acceptance.md](acceptance.md).

The browser request check covers resources added by the specimen. It does not imply that Chrome or Discord makes no background requests. The timing sample describes one local fixture navigation. It is not a benchmark of application startup, a before/after speed claim or a sustained-reading measurement.

Playwright is a development dependency under Apache-2.0. It is not included in the theme downloads. No third-party theme code, fonts, images or monitor profiles are bundled. The original icon is generated by the Chrome theme builder. Research references are evidence and attribution records, not endorsements.
