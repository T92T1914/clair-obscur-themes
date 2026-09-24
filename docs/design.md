# Design and implementation

Clair and Obscur carry Tornado Atlas's warm light and restrained dark identity into two native application surfaces. Clair is a light theme, not a dark interface with a cream message pane. Obscur separates near-black surfaces without relying on background images, transparency or animated effects. Both retain the host application's layout and scaling.

The shared source is [tokens.json](../tokens.json). Its Atlas reference is [revision 1eadada](https://github.com/T92T1914/tornado-atlas/tree/1eadada6370fba3bee875fa4020d41bbdd663dbf), specifically `web/appearance.css` and `web/atlas.css`. Atlas itself is not modified by this project.

## Shared roles

| Role | Clair | Obscur | Purpose |
| --- | --- | --- | --- |
| Canvas | `#f8f7f3` | `#090909` | Main background |
| Panel | `#fdfcf8` | `#151515` | Raised reading and navigation surfaces |
| Primary text | `#242424` | `#f4f4f4` | Body content and important controls |
| Secondary text | `#595854` | `#bcbcbc` | Supporting information |
| Control | `#ecebe6` | `#252525` | Inputs and inactive controls |
| Hover | `#e0ded7` | `#373737` | Pointer feedback |
| Selected surface | `#e7e4da` | `#333333` | Selection background |
| Essential border | `#7f7d76` | `#858585` | Control boundaries |
| Accent | `#365f78` | `#b3c8d8` | Links and selected actions |
| Focus | `#315977` | `#c2d7e6` | Keyboard focus |
| Code background | `#eeece5` | `#111111` | Inline and fenced code |

Clair's panel is deliberately softened from Atlas's white to `#fdfcf8`. The body text stays dark. A blue accent identifies ordinary interaction without reusing Atlas's pink remembrance meaning. Success, warning and error have separate semantic roles. A decorative divider is not a substitute for the stronger border used where a control boundary matters.

The token validator checks selected text/background pairs at 4.5:1 and essential borders/focus at 3:1. These are checks on declared opaque sRGB pairs. They do not certify every inherited host state, prove physical luminance or establish complete accessibility compliance. The [acceptance record](acceptance.md) separates those questions.

## Typography

Equicord themes use local Inter Regular 400, SemiBold 600 and Bold 700, with genuine italic faces for all three weights. Font files are not distributed or fetched by the theme. Local aliases resolve the official static Inter face names, then fall back to installed Inter and the platform's sans-serif stack. This build does not offer an unverified intermediate 450 weight.

Message content and controls retain native sizing. Code keeps the host's monospace stack. Icons, emoji and other writing systems keep appropriate fallback fonts. There is no universal descendant font rule, forced text smoothing or fixed pixel-size replacement for the application's own scaling. Actual glyph-face inspection is required because a computed `font-family` alone does not establish which face drew the text.

Native Chrome themes cannot select Chrome's UI font. Chrome retains its own typography. Inter in the project's preview does not imply Inter in the tab strip or address bar. Reading mode is a separate browser feature, and any future companion would be separately installable.

## Platform boundaries

| Surface | Implementation | Preserved host behavior |
| --- | --- | --- |
| Google Chrome | Native Manifest V3 color theme plus original package icon | Browser fonts, layout, tab geometry, site content, security indicators and native controls |
| Equibop with Equicord | Standalone local CSS using host variables and narrow semantic selectors | Layout, chat size, zoom, code syntax colors, icons, user content and plugin state |

Use Clair with native Light appearance and Obscur with a native dark appearance. CSS mode gates avoid partially recoloring an opposite native base. They do not implement universal cross-mode conversion. Selection and toggle state should remain visible through native geometry, borders and checkmarks as well as color. Manual switching is the default.

The [Chrome contract](chrome-contract.md) and [Equicord contract](equicord-contract.md) describe exact mappings and volatile host interfaces. The [research](../research/research.md) explains why code, search, toggles, active tabs and opposite-base behavior receive explicit checks. No candidate theme implementation is a dependency.

## Display and evidence

The reference setup is a user-reported ASUS PG32UCDMR at 3840 × 2160 and 240 Hz in a dark room, with Windows HDR on, SDR content brightness 0 and Auto HDR off. Reported monitor settings are Gaming HDR, brightness 100 and contrast 80. These are preservation requirements, not measurements established by the theme.

A read-only Windows API inspection confirmed the PG32UCDMR's active 3840 × 2160 signal, 240 Hz, 150% scaling and HDR mode. Separate current-user SDR and extended-color profile associations were present. No settings or profiles were changed. The configured SDR reference was 80 nits according to the Windows API conversion. That value is not measured panel luminance, nor an independent reading of the brightness slider. Physical comfort, monitor controls and the reported recording behavior remain separate, unverified questions.

The theme contains no monitor-specific transform, calibration adjustment or recording workaround. A token contrast calculation, headless render, native application capture and physical viewing check answer different questions. Screenshots cannot establish physical OLED appearance or subjective reading comfort.
