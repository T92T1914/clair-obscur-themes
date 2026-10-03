# Platform candidates

The family now generates Firefox static themes and local Vencord and BetterDiscord CSS from the existing palette. The Chrome and Equicord 0.1.1 downloads retain their accepted bytes. New adapters are versioned 0.2.0. They are preview candidates, not a new signed release or a native compatibility pass. The [acceptance record](acceptance.md#platform-adapter-increment) identifies the executed Mozilla validation and isolated browser checks.

The artifact manifest records each download's own version. Edge points to the exact Chrome ZIP rather than a renamed copy. Twelve download choices refer to ten distinct files. A Chromium package that parses correctly still needs an actual Edge installation and surface check.

## Firefox

`themeforge/firefox.py` maps 37 native color keys for the frame, active and inactive tabs, toolbar, focused fields, popups, sidebar and new-tab surfaces. Highlighted text has a paired foreground. Deprecated tab and field separators are excluded. The package contains only `manifest.json` and the project's license, with no browsing permissions, scripts or fonts.

These are manual Clair and Obscur choices for desktop Firefox 128 or later. The declared minimum is a conservative package prerequisite, not evidence that this project ran in every later version. `color_scheme` follows the selected browser theme. `content_color_scheme` remains `system`, so the theme does not force every website into its own appearance. An automatic `dark_theme` pair is deliberately not included. Firefox retains its interface font. [Mozilla's static-theme contract](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/theme).

The generated XPIs are unsigned. For a separately authorized developer check, use a disposable Firefox profile and the supported temporary-addon route in `about:debugging`. Extracted `firefox/clair/manifest.json` and `firefox/obscur/manifest.json` are available in the build tree. A temporary load is removed when that test session ends. Normal distribution requires Mozilla signing. Do not disable signature enforcement, modify `userChrome.css` or install a website restyler to make the color theme appear complete. [Mozilla signing and distribution](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/).

Native acceptance must cover selected and inactive windows, address suggestions, popup and sidebar selections, private-window distinction, appearance switching, an ordinary restart and restoration. No native Firefox installation was performed in this phase.

## Microsoft Edge

The existing color-only Chromium artifact needs no code API translation. It contains no `update_url`. Reusing it is a candidate route supported by Microsoft's general porting guidance, not evidence that every Chromium color key reaches every Edge surface. [Microsoft's porting guide](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/port-chrome-extension) requires testing in Edge and describes separate branding requirements for certification. [Microsoft's extension overview](https://learn.microsoft.com/en-us/microsoft-edge/extensions/) explicitly includes native themes.

The download label preserves the Chrome filename so its identity is visible. It is not an Edge store package. A separately permitted check must use an isolated, recoverable Edge profile, the supported unpacked test route and the exact generated manifest. Check the tab strip, focused address field, suggestions, favorites, sidebar, selected and inactive windows, private-window identity and restoration. Record unchanged Edge-owned surfaces rather than applying CSS to them. No native Edge acceptance or store submission is claimed.

## Vencord and BetterDiscord

Both adapters reuse the existing Discord host-variable, local-font and semantic-control generator. Each file begins with its own loader metadata and retains the full project license. Six local Inter faces provide Regular, SemiBold and Bold with genuine italics where available. System, code, icon and language fallbacks remain in place. There are no remote imports, font binaries, global filters, fixed hashed class selectors or host layout changes.

Use Clair with the host's native Light appearance and Obscur with a native dark appearance. The opposite appearance keeps its own baseline. Enable one family theme. Preserve the current theme choices and QuickCSS. Use the installed client's own local Themes folder, add the downloaded `.theme.css`, then disable that file to restore the recorded appearance. This project does not install a client modification or overwrite existing user CSS. BetterDiscord's documented distribution format is a single metadata-bearing `.theme.css` file. [BetterDiscord theme structure](https://docs.betterdiscord.app/themes/introduction/structure).

The Vencord adapter handles its actual `vc-switch-container` and SVG-slider contract. The BetterDiscord adapter handles its invisible checkbox, adjacent `bd-switch-body`, SVG handle and filled brand buttons. Both pair Obscur's pale accent with dark foregrounds. Geometry, native disabled behavior, checkmarks and danger/positive filled-action pairs stay host-owned. Keyboard focus, reduced motion and forced colors receive scoped rules.

The current source contracts were inspected at Vencord revision `b52ed365cf2ea64a5019b419291a2d9d4d76852d` and BetterDiscord revision `9fc106e8e53e51589374c05cfb03b35f4149d0a2`. Relevant original interfaces are Vencord's [theme metadata parser](https://github.com/Vendicated/Vencord/blob/b52ed365cf2ea64a5019b419291a2d9d4d76852d/src/main/themes/index.ts), [switch](https://github.com/Vendicated/Vencord/blob/b52ed365cf2ea64a5019b419291a2d9d4d76852d/src/components/Switch.tsx) and [button stylesheet](https://github.com/Vendicated/Vencord/blob/b52ed365cf2ea64a5019b419291a2d9d4d76852d/src/components/Button.css), plus BetterDiscord's [theme manager](https://github.com/BetterDiscord/BetterDiscord/blob/9fc106e8e53e51589374c05cfb03b35f4149d0a2/src/betterdiscord/modules/thememanager.ts), [switch](https://github.com/BetterDiscord/BetterDiscord/blob/9fc106e8e53e51589374c05cfb03b35f4149d0a2/src/betterdiscord/ui/settings/components/switch.tsx) and [button stylesheet](https://github.com/BetterDiscord/BetterDiscord/blob/9fc106e8e53e51589374c05cfb03b35f4149d0a2/src/betterdiscord/styles/buttons.css). No upstream implementation is bundled. Future host changes can invalidate these mappings.

Vencord, Equicord and BetterDiscord are unofficial client-mod targets. They are not Discord-endorsed appearance options. Technical CSS checks do not establish zero account risk. Browser Vencord, desktop Vencord, Vesktop, BetterDiscord and Equicord are separate acceptance environments. [Vencord's official support and limitations](https://vencord.dev/support/).

Direct project distribution is separate from gallery approval. BetterDiscord's listing rules include authorship and design requirements. No listing is claimed and no decorative changes were added to chase one. [BetterDiscord theme guidelines](https://docs.betterdiscord.app/themes/publishing/guidelines).

## Evidence and remaining acceptance

| Target | Local contract | Native installation and loaded surfaces | Restart and restoration | Distribution |
| --- | --- | --- | --- | --- |
| Chrome 0.1.1 | Existing accepted generator and unchanged bytes | Existing limited Obscur evidence retained | Existing incomplete gates retained | Original preview release unchanged |
| Equicord 0.1.1 | Existing accepted generator and unchanged bytes | Existing limited Clair/Obscur evidence retained | Prior restoration evidence retained, full acceptance open | Original local CSS unchanged |
| Firefox 0.2.0 | Static manifest, bounded package and palette pairing tests | Deferred under SHARED_PC | Deferred under SHARED_PC | Unsigned candidate, signing and store review pending |
| Edge, Chromium 0.1.1 | Exact Chrome artifact reuse | Deferred under SHARED_PC | Deferred under SHARED_PC | No Edge store submission |
| Vencord 0.2.0 | Original scoped CSS over inspected current component contracts | Deferred separately for browser, desktop and Vesktop | Deferred separately | Direct CSS candidate, no gallery claim |
| BetterDiscord 0.2.0 | Original scoped CSS over inspected current component contracts | Deferred under SHARED_PC | Deferred under SHARED_PC | Direct CSS candidate, no gallery claim |

Local page fixtures can inspect color pairs, mode gates, keyboard focus, selectors, glyph fallbacks and unchanged geometry. They cannot certify native browser chrome or a signed-in client's full interface. Font resolution in the specimen does not establish Inter in browser tabs. Physical HDR, reading comfort and phone behavior remain separate evidence.

## Further targets

| Target | Actual route and disposition |
| --- | --- |
| Brave desktop | Its official documentation describes Chromium-extension compatibility. Theme-specific surfaces have not been inspected here. No Brave native compatibility claim or separate artifact. [Brave extension guidance](https://support.brave.com/hc/en-us/articles/360017909112-How-can-I-add-extensions-to-Brave). |
| Vivaldi desktop | Its shareable-theme route uses a ZIP with settings JSON. It requires a real adapter, not a renamed Chrome ZIP. Not implemented in this increment. [Vivaldi shareable themes](https://help.vivaldi.com/desktop/appearance-customization/shareable-vivaldi-themes/). |
| Opera and Opera GX | Opera documents built-in themes, colors and wallpapers. That does not establish arbitrary Chromium native-color package compatibility. No artifact or native check. GX requires its own documented format assessment. [Opera customization](https://help.opera.com/en/latest/customization/). |
| Safari | No compatible native color-theme route established in this investigation. A website extension would be a different product and is not substituted here. |
| Mobile browsers and clients | No desktop artifact is presented as a mobile-native theme. Keep each mobile platform's actual appearance capabilities separate. |
