"""Small client adapters over the existing Discord palette and typography."""

from collections.abc import Mapping

from .equicord import render_theme


CLIENTS = {"vencord": "Vencord", "betterdiscord": "BetterDiscord"}


def render_client_theme(client: str, name: str, tokens: Mapping[str, str], version: str) -> str:
    """Reuse the shared host variables, adding only the selected client's states.

    Loader comments are rewritten before the canonical license comment. The
    Equicord generator remains unchanged, preserving released file bytes.
    """
    if client not in CLIENTS:
        raise ValueError("Client must be vencord or betterdiscord")
    css = render_theme(name, tokens, version)
    css = css.replace("Equibop with Equicord.", CLIENTS[client] + ".", 1)
    css = css.replace("/* Equicord's native switch owns geometry and checkmarks. */",
                      "/* Shared Equicord selectors are inactive in clients without those components. */")
    scope = ".theme-light" if name == "Clair" else ":is(.theme-dark, .theme-darker, .theme-midnight)"
    if client == "vencord":
        css += f"""
/* Vencord uses a container and SVG slider, not Equicord's indicator.
   Keep its geometry, checked transform and disabled behavior. */
{scope} .vc-switch-container {{
  background-color: var(--co-control);
  border-color: var(--co-border);
}}
{scope} .vc-switch-container.vc-switch-checked {{
  background-color: var(--co-accent);
  border-color: var(--co-accent);
}}
{scope} .vc-switch-slider > rect {{ fill: var(--co-text); }}
{scope} .vc-switch-slider path {{ fill: var(--co-control); }}
{scope} .vc-switch-checked .vc-switch-slider > rect {{ fill: var(--co-on-accent); }}
{scope} .vc-switch-checked .vc-switch-slider path {{ fill: var(--co-accent); }}
{scope} .vc-switch-container.vc-switch-focusVisible {{
  outline: 2px solid var(--co-focus);
  outline-offset: 2px;
}}
@media (prefers-reduced-motion: reduce) {{
  {scope} :is(.vc-switch-container, .vc-switch-slider) {{ transition: none; }}
}}
@media (forced-colors: active) {{
  {scope} .vc-switch-container.vc-switch-checked {{ background-color: Highlight; border-color: Highlight; }}
  {scope} .vc-switch-checked .vc-switch-slider > rect {{ fill: HighlightText; }}
  {scope} .vc-switch-checked .vc-switch-slider path {{ fill: Highlight; }}
}}
"""
    else:
        css += f"""
/* BetterDiscord owns its settings geometry, disabled states and SVG marks.
   Pair pale Obscur brand fills with dark foregrounds, not native white. */
{scope} {{
  --bd-brand: var(--co-accent);
  --bd-brand-hover: var(--co-accent);
  --bd-brand-active: var(--co-accent);
  --control-secondary-background-active: var(--co-selected);
  --control-secondary-text-active: var(--co-text);
}}
{scope} .bd-button {{ font-family: var(--font-primary); font-weight: 600; }}
{scope} .bd-button-filled:is(.bd-button-color-brand, .bd-button-color-blurple, .bd-button-color-link) {{
  background-color: var(--co-accent);
  color: var(--co-on-accent);
}}
{scope} .bd-button-filled:is(.bd-button-color-brand, .bd-button-color-blurple, .bd-button-color-link):is(:hover, :active, :disabled) {{
  background-color: var(--co-accent);
  color: var(--co-on-accent);
}}
{scope} .bd-switch-body {{
  --switch-color: var(--co-control);
  outline: 1px solid var(--co-border);
  outline-offset: -1px;
}}
{scope} .bd-switch input:checked + .bd-switch-body {{ --switch-color: var(--co-accent); }}
{scope} .bd-switch-handle {{ fill: var(--co-text); }}
{scope} .bd-switch input:checked + .bd-switch-body .bd-switch-handle {{ fill: var(--co-on-accent); }}
{scope} .bd-switch input:focus-visible + .bd-switch-body {{
  outline: 2px solid var(--co-focus);
  outline-offset: 2px;
}}
@media (prefers-reduced-motion: reduce) {{
  {scope} :is(.bd-button, .bd-switch, .bd-switch-body, .bd-switch-slider, .bd-switch-handle, .bd-switch-symbol path) {{
    transition: none;
  }}
}}
@media (forced-colors: active) {{
  {scope} .bd-switch input:checked + .bd-switch-body {{ --switch-color: Highlight; }}
  {scope} .bd-switch input:checked + .bd-switch-body .bd-switch-handle {{ fill: HighlightText; }}
}}
"""
    return css
