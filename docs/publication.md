# Distribution and publication

The project distributes experimental previews. A public repository, downloadable prerelease, deployed preview, native acceptance and store approval are separate states. None is established by a successful local package build. Current application acceptance is recorded in [acceptance.md](acceptance.md).

## What can be distributed

Original source and documentation use the repository's [MIT license](../LICENSE). Generated themes contain original token mappings and a small original package icon. No candidate theme CSS, screenshots, logos, testimonials or font binaries are included as implementation assets. The [research matrix](../research/source-matrix.json) records candidate licenses as source metadata, not licenses inherited by this project.

The Atlas identity reference is identified in [design.md](design.md). Inter is obtained separately from its official distribution. A local font alias neither redistributes Inter nor gives the theme control over Chrome's native typography.

Public material should contain only original or appropriately licensed assets and verified, sanitized claims. Exclude account names, private conversations, server/channel lists, local paths, credentials, profile data, display identifiers and private captures. A permitted local screenshot is not automatically suitable for public distribution.

## Release gates

Before publishing a downloadable preview:

1. Build from a recorded revision, execute the relevant checks and inspect generated output.
2. Verify that Chrome archives have `manifest.json` at the root and that every release file matches the accompanying hashes.
3. Include license and installation information. Identify the exact version and keep the actual application status visible.
4. Review the full source, artifacts, image metadata and proposed copy for private material and unsupported claims.
5. Reopen the resulting remote revision and downloadable artifacts after upload. A completed upload is distinct from verified public access.

A preview may describe its implemented behavior and remaining gates accurately. It must not claim successful Equibop loading, physical HDR tuning, complete accessibility, store approval or universal readability without the corresponding evidence. The [README](../README.md) is the adopted project introduction. Store copy and promotional assets still require their destination-specific checks.

## GitHub delivery

The public source destination is [T92T1914/clair-obscur-themes](https://github.com/T92T1914/clair-obscur-themes). Inspect its current revision and Actions results rather than assuming that a local commit has been pushed.

The [Theme checks workflow](../.github/workflows/checks.yml) runs package checks on Linux and Windows plus a separate headless Chrome specimen job. Its Linux build retains the generated site and downloads as the `clair-obscur-preview` workflow artifact. The preview builder verifies that its clean source matches the run's commit and records that revision in `site-manifest.json`.

For a downloadable prerelease, create a `v<VERSION>` tag for the intended source revision only after review. The version must match `tokens.json`. After its required build and browser jobs pass, the workflow can publish the two Chrome ZIPs, two Equicord CSS files, `release-SHA256SUMS`, `artifact-manifest.json` and `source.zip` to a GitHub prerelease. Verify the resulting release and downloaded bytes. A tag push alone is not proof of publication.

Each push to `main` automatically deploys that run's checked preview after both build platforms and the browser job succeed. Pull requests, other branches and tag pushes cannot deploy the main website. A failed, canceled or skipped prerequisite prevents publication. The optional manual `publish_pages` input remains available from `main` for a deliberate redeployment.

Pages downloads the named artifact from the same workflow run. It does not rebuild the site or select an artifact from another run. The `github-pages` environment and its approval rules still apply. Only the deployment job receives Pages and identity-token write permissions. Main pushes and publishing manual runs share a concurrency group so a replacement run cancels obsolete work. Check-only manual runs use another group and cannot cancel publication. Release-tag runs keep their separate publication queue.

The repository must have GitHub Pages configured to use GitHub Actions. After merging, inspect the actual main-triggered run and deployment, then compare the served `site-manifest.json` revision with the tested commit. Follow the acceptance link and exercise all four downloads. A successful merge or uploaded artifact alone is not a verified deployment. See GitHub's [custom Pages workflow requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

Use the repository's normal scoped workflow token for authorized Actions publication. Do not place personal access tokens, browser data or local credential material in the source or artifacts. Keep published tags and versioned assets intact. A documentation or website update does not require a new theme release. The page links the versioned source archive and release checksums to the existing GitHub release. Its separate current-source snapshot identifies the website's actual source revision and checksum. Never replace the released archive with that newer snapshot.

## Equicord library

The [Equicord library](https://themes.equicord.org/) is the relevant directory for the primary client. Its inspected [submission implementation](https://github.com/Equicord/Equithemes.org/blob/ddefa615fd1d7e23c2b77330213a50a945e45986/src/pages/theme/submit.tsx) uses login, attribution, preview and theme/source metadata. Server-side review distinguishes pending submission from approval. Source inspection does not establish that the authenticated submission route was exercised.

No separate public rule settling theme-license or assisted-authorship eligibility was established during research. Resolve current applicable submission rules before submitting. The [privacy policy](https://themes.equicord.org/privacy) describes OAuth identity and attribution. Do not invent an accepted listing, bypass an account requirement or send community messages merely to complete a checklist.

BetterDiscord is an optional and separate directory. Its [publication guidelines](https://docs.betterdiscord.app/themes/publishing/guidelines) reject automatically generated themes, code written by someone else and simple recolors. Do not represent this assisted implementation as meeting that directory's authorship requirement. Those restrictions are not a prohibition on independent distribution and do not establish Equicord's rules. BetterDiscord installation is not part of this project.

## Chrome Web Store

The Chrome ZIP is a native development/upload artifact. Local unpacked installation does not establish store review or consumer availability. Ordinary Chrome remains the target browser.

Before a store submission, check the existing authorized publisher account, current listing requirements, privacy declarations and [publication workflow](https://developer.chrome.com/docs/webstore/publish). New publisher [registration](https://developer.chrome.com/docs/webstore/register) can require a fee and agreement acceptance. [2-Step Verification](https://developer.chrome.com/docs/webstore/program-policies/two-step-verification) is an account requirement. Building the package does not authorize paying fees, accepting new agreements or changing account security.

Prepare the required original promotional image and actual native-product screenshots at the [documented sizes](https://developer.chrome.com/docs/webstore/images). At least one 1280 × 800 or 640 × 400 native screenshot is still missing. A webpage mockup or theme-preview card must not be substituted for the browser frame. Store packages are therefore not submission-ready solely because their manifests and ZIPs validate.

Review listing text separately for each variant. State that fonts and websites remain native. Explain the light or dark palette directly. Do not promise OLED power savings, burn-in prevention, eye-health benefits or a correction to a recording pipeline.

## Store status

No Chrome Web Store or Equicord library approval is claimed. GitHub distribution does not imply either directory reviewed the theme. No optional reader is included in these packages.
