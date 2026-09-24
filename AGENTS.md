# Clair and Obscur

Build a shared original theme family for native Google Chrome and Windows Equibop with Equicord. Atlas is a read-only design reference. Keep fonts, application integration, public previews and physical display evidence distinct.

- Edit shared tokens and generators, then rebuild. Generated packages contain no scripts, remote imports, analytics, font binaries or private machine data.
- Preserve native scaling, appropriate monospace and language/icon fallbacks. Use installed Inter 400, 600, 700 and genuine italics where supported. Native Chrome theme APIs cannot change its UI font.
- The primary reference is a user-reported PG32UCDMR, 4K/240 Hz, dark room, Windows HDR on, SDR brightness 0 and Auto HDR off. Do not change display settings, calibration, profiles or application security to satisfy a theme check.
- Actual Equibop loading and native Chrome frame checks are separate from local fixture checks. Never label a fixture as application acceptance or a screenshot as physical luminance measurement.
- Preserve existing client themes, QuickCSS, plugins and Chrome profiles. Only the coordinating agent performs scoped native application checks.
- Keep current private acceptance evidence outside the repository. Publish only sanitized facts and approved original assets.
- Maintain the actual README and necessary documentation as part of verified delivery. Keep public compatibility claims tied to the recorded evidence. Store publication remains a separate approval and acceptance process.

## Verification and generated files

- Run `python -m unittest discover -s tests -v`, `python build.py`, then `python build.py --check`.
- Run `npm ci --ignore-scripts --no-audit --no-fund` and `npm run test:browser` for isolated headless page checks. The default channel is ordinary installed Chrome. `THEME_BROWSER_CHANNEL=chromium` is a separate CI engine check. Require the six installed faces with `THEME_REQUIRE_INTER=1` when evaluating Inter itself.
- Browser tests use temporary profiles, loopback-only fixtures, no visible fallback and no desktop input. They never establish native frame or Equibop acceptance.
- `python preview.py --output outputs/preview` packages the static specimen and verified downloads. A changed existing preview is preserved. Use a fresh output directory for a new candidate.
- `dist/` is an exact managed build tree. Never edit generated theme files or add files to it. The builder rejects foreign or edited output and checks existing hashes before replacement.
- Extract native installation copies outside managed build output. Preserve files Chrome creates inside a live installation, including `Cached Theme.pak`.
- Native checks require a current scoped control grant and a functioning desktop tool. Preserve the exact interruption state, including URL-confidence and physical Escape stops. Do not retry or change controllers to bypass enforcement.

## Publication

- Reviewed updates merged into `main` deploy automatically after the same run's Linux, Windows and browser checks pass. Preserve the `github-pages` environment, approvals, scoped permissions, same-run artifact and concurrency controls. Manual dispatch is an optional fallback, not the ordinary publication step.
- Keep push triggers available for version tags. Tag prereleases are separate from website deployment. Do not move existing tags or replace published assets for documentation changes.
- Verify the main-triggered Pages result, served `site-manifest.json` revision, acceptance link and four actual downloads before reporting deployment. The versioned source link must use the original release archive. A current-source snapshot needs its actual revision and matching checksum.
