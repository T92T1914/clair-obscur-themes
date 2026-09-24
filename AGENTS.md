# Clair and Obscur

Build a shared original theme family for native Google Chrome and Windows Equibop with Equicord. Atlas is a read-only design reference. Keep fonts, application integration, public previews and physical display evidence distinct.

- Edit shared tokens and generators, then rebuild. Generated packages contain no scripts, remote imports, analytics, font binaries or private machine data.
- Preserve native scaling, appropriate monospace and language/icon fallbacks. Use installed Inter 400, 600, 700 and genuine italics where supported. Native Chrome theme APIs cannot change its UI font.
- The primary reference is a user-reported PG32UCDMR, 4K/240 Hz, dark room, Windows HDR on, SDR brightness 0 and Auto HDR off. Do not change display settings, calibration, profiles or application security to satisfy a theme check.
- Actual Equibop loading and native Chrome frame checks are separate from local fixture checks. Never label a fixture as application acceptance or a screenshot as physical luminance measurement.
- Preserve existing client themes, QuickCSS, plugins and Chrome profiles. Only the coordinating agent performs scoped native application checks.
- Keep current private acceptance evidence outside the repository. Publish only sanitized facts and approved original assets.
- README and store copy remain proposed until requested. Necessary factual installation, build and compatibility documentation is in scope.

## Verification and generated files

- Run `python -m unittest discover -s tests -v`, `python build.py`, then `python build.py --check`.
- Run `npm ci --ignore-scripts --no-audit --no-fund` and `npm run test:browser` for isolated headless page checks. The default channel is ordinary installed Chrome. `THEME_BROWSER_CHANNEL=chromium` is a separate CI engine check. Require the six installed faces with `THEME_REQUIRE_INTER=1` when evaluating Inter itself.
- Browser tests use temporary profiles, loopback-only fixtures, no visible fallback and no desktop input. They never establish native frame or Equibop acceptance.
- `python preview.py --output outputs/preview` packages the static specimen and verified downloads. A changed existing preview is preserved. Use a fresh output directory for a new candidate.
- `dist/` is an exact managed build tree. Never edit generated theme files or add files to it. The builder rejects foreign or edited output and checks existing hashes before replacement.
- Native checks require a current scoped control grant and a functioning desktop tool. Preserve the interruption state and do not bypass a physical Escape stop.
