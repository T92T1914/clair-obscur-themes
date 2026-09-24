"""Generate self-contained CSS for Equibop's Equicord theme loader."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .legal import license_comment


TOKEN_NAMES = (
    "canvas", "panel", "text", "muted", "divider", "control", "hover",
    "selected", "border", "accent", "on_accent", "focus", "success",
    "warning", "error", "code", "disabled",
)

# Full and PostScript names from the official Inter 4.1 static faces.
FACES = (
    (400, "normal", "Inter Regular", "Inter-Regular"),
    (400, "italic", "Inter Italic", "Inter-Italic"),
    (600, "normal", "Inter SemiBold", "Inter-SemiBold"),
    (600, "italic", "Inter SemiBold Italic", "Inter-SemiBoldItalic"),
    (700, "normal", "Inter Bold", "Inter-Bold"),
    (700, "italic", "Inter Bold Italic", "Inter-BoldItalic"),
)

# Host custom properties, not a replacement for Discord's component layout.
# Both current surface tokens and retained legacy tokens are intentional.
HOST_TOKENS = {
    "background-primary": "canvas",
    "background-secondary": "panel",
    "background-secondary-alt": "control",
    "background-tertiary": "canvas",
    "background-accent": "selected",
    "background-floating": "panel",
    "background-base-lowest": "canvas",
    "background-base-lower": "canvas",
    "background-base-lower-alt": "panel",
    "background-base-low": "panel",
    "background-surface-high": "panel",
    "background-surface-higher": "control",
    "background-surface-highest": "selected",
    "background-mod-subtle": "hover",
    "background-mod-muted": "control",
    "background-mod-normal": "selected",
    "background-mod-strong": "hover",
    "background-modifier-hover": "hover",
    "background-modifier-active": "selected",
    "background-modifier-selected": "selected",
    "background-modifier-accent": "divider",
    "bg-base-primary": "canvas",
    "bg-base-secondary": "panel",
    "bg-base-tertiary": "canvas",
    "bg-surface-overlay": "panel",
    "bg-surface-raised": "panel",
    "bg-mod-faint": "control",
    "bg-mod-subtle": "hover",
    "bg-mod-strong": "selected",
    "text-normal": "text",
    "text-default": "text",
    "text-strong": "text",
    "text-muted": "muted",
    "text-subtle": "muted",
    "text-faint": "muted",
    "header-primary": "text",
    "header-secondary": "muted",
    "channels-default": "muted",
    "channel-icon": "muted",
    "interactive-normal": "muted",
    "interactive-hover": "text",
    "interactive-active": "text",
    "interactive-muted": "disabled",
    "interactive-icon-default": "muted",
    "interactive-icon-hover": "text",
    "interactive-icon-active": "text",
    "interactive-text-default": "text",
    "interactive-text-hover": "text",
    "interactive-background-hover": "hover",
    "input-background": "control",
    "input-background-default": "control",
    "input-border": "border",
    "input-border-default": "border",
    "input-placeholder-text-default": "muted",
    "channeltextarea-background": "control",
    "modal-background": "panel",
    "modal-footer-background": "control",
    "border-subtle": "divider",
    "border-muted": "divider",
    "border-normal": "border",
    "border-strong": "border",
    "border-focus": "focus",
    "text-link": "accent",
    "text-brand": "accent",
    "brand-500": "accent",
    "brand-560": "accent",
    "brand-600": "accent",
    "button-brand-background": "accent",
    "button-brand-background-hover": "accent",
    "button-brand-background-active": "accent",
    "button-brand-text": "on_accent",
    "button-secondary-background": "control",
    "button-secondary-background-hover": "hover",
    "button-secondary-background-active": "selected",
    "button-secondary-text": "text",
    "control-primary-background-default": "accent",
    "control-primary-background-hover": "accent",
    "control-primary-border-default": "accent",
    "control-primary-border-hover": "accent",
    "control-primary-text-default": "on_accent",
    "control-primary-text-hover": "on_accent",
    "control-secondary-background-default": "control",
    "control-secondary-background-hover": "hover",
    "control-secondary-border-default": "border",
    "control-secondary-border-hover": "border",
    "control-secondary-text-default": "text",
    "control-secondary-text-hover": "text",
    "control-icon-only-background-hover": "hover",
    "control-icon-only-background-active": "selected",
    "control-icon-only-border-hover": "border",
    "control-icon-only-border-active": "border",
    "control-icon-only-icon-default": "muted",
    "control-icon-only-icon-hover": "text",
    "text-positive": "success",
    "text-warning": "warning",
    "text-danger": "error",
    "text-feedback-positive": "success",
    "text-feedback-warning": "warning",
    "text-feedback-critical": "error",
    "text-feedback-info": "accent",
    "status-positive": "success",
    "status-warning": "warning",
    "status-danger": "error",
    "background-message-hover": "panel",
    "background-mentioned": "selected",
    "background-mentioned-hover": "hover",
    "mention-background": "selected",
    "mention-foreground": "accent",
    "scrollbar-thin-thumb": "border",
    "scrollbar-thin-track": "canvas",
    "scrollbar-auto-thumb": "border",
    "scrollbar-auto-track": "canvas",
    "switch-background-default": "control",
    "switch-background-hover": "hover",
    "switch-background-selected-default": "accent",
    "switch-background-selected-hover": "accent",
    "switch-border-default": "border",
    "switch-border-hover": "border",
    "switch-border-selected-default": "accent",
    "switch-border-selected-hover": "accent",
    "switch-thumb-background-default": "text",
    "switch-thumb-background-selected-default": "on_accent",
    "checkbox-background-default": "control",
    "checkbox-border-default": "border",
    "checkbox-background-selected-default": "accent",
    "checkbox-border-selected-default": "accent",
    "checkbox-icon-selected-default": "on_accent",
}


def render_theme(name: str, tokens: Mapping[str, str], version: str) -> str:
    """Render one manually selected theme, gated to its matching native mode.

    Validation keeps malformed source values from becoming CSS or metadata.
    No font installation, host settings changes or remote reads occur here.
    """
    if name not in ("Clair", "Obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
        raise ValueError("Version must be a semantic version")
    missing = set(TOKEN_NAMES) - set(tokens)
    if missing:
        raise ValueError("Missing theme tokens: " + ", ".join(sorted(missing)))
    for key in TOKEN_NAMES:
        if not isinstance(tokens[key], str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", tokens[key]):
            raise ValueError(f"Token {key} must be a six-digit hex color")
    mode = "light" if name == "Clair" else "dark"
    scope = ".theme-light" if mode == "light" else ":is(.theme-dark, .theme-darker, .theme-midnight)"
    description = "Warm paper and clear ink" if name == "Clair" else "Deep neutral surfaces and restrained emphasis"
    parts = [f"""/**
 * @name {name}
 * @author T92T1914
 * @version {version}
 * @description {description}. Equibop with Equicord. Use native {mode.title()} mode. Install Inter locally for the intended typography.
 */

{license_comment()}

/* Enable only one family theme. Native {mode.title()} mode is required.
   The opposite native app mode keeps its own palette. No network font loading.
   Edit shared source tokens, then rebuild this file. */
"""]
    for weight, style, full, postscript in FACES:
        parts.append(f"""@font-face {{
  font-family: "Clair Obscur Inter";
  src: local("{full}"), local("{postscript}");
  font-weight: {weight};
  font-style: {style};
  font-display: swap;
}}
""")
    parts.append(f"{scope} {{\n")
    for key in TOKEN_NAMES:
        parts.append(f"  --co-{key.replace('_', '-')}: {tokens[key].lower()};\n")
    parts.extend([
        '  --font-primary: "Clair Obscur Inter", "Inter", system-ui, "Segoe UI", sans-serif;\n',
        '  --font-display: var(--font-primary);\n',
        '  --font-headline: var(--font-primary);\n',
        '  --font-weight-normal: 400;\n',
        '  --font-weight-medium: 600;\n',
        '  --font-weight-semibold: 600;\n',
        '  --font-weight-bold: 700;\n',
    ])
    for host, token in HOST_TOKENS.items():
        parts.append(f"  --{host}: var(--co-{token.replace('_', '-')});\n")
    parts.append(f"  color-scheme: {mode};\n}}\n")
    parts.append(f"""
/* Stable message IDs and semantic controls. No blanket descendant font reset. */
{scope} :is([id^="message-content-"], [role="textbox"][contenteditable="true"]) {{
  font-family: var(--font-primary);
  font-weight: 400;
  font-optical-sizing: auto;
  font-synthesis: none;
  letter-spacing: normal;
}}
{scope} :is([id^="message-content-"] strong, [id^="message-content-"] b) {{
  font-weight: 700;
}}
{scope} :is([id^="message-content-"] em, [id^="message-content-"] i) {{
  font-style: italic;
}}
{scope} :is(.vc-btn-small, .vc-btn-medium) {{
  font-weight: 600;
}}
{scope} :is([id^="message-content-"] code, [id^="message-content-"] pre) {{
  font-family: var(--font-code, ui-monospace, Consolas, monospace);
  background-color: var(--co-code);
}}
/* Native highlight syntax colors stay intact. */
{scope} [id^="message-content-"] code:not(.hljs) {{
  color: var(--co-text);
}}
{scope} :is([role="textbox"][contenteditable="true"], input:not(.vc-switch-input),
  textarea, button, a, [role="button"], [role="tab"], [role="menuitem"]):focus-visible {{
  outline: 2px solid var(--co-focus);
  outline-offset: 2px;
}}
/* Equicord's native switch owns geometry and checkmarks. */
{scope} .vc-switch-focusVisible .vc-switch-indicator {{
  outline: 2px solid var(--co-focus);
  outline-offset: 2px;
}}

@media (prefers-reduced-motion: reduce) {{
  {scope} :is(.vc-switch-indicator, .vc-switch-thumb, .vc-btn-base) {{
    transition: none;
  }}
}}

/* Restore system colors rather than locking in a custom high-contrast palette. */
@media (forced-colors: active) {{
  {scope} {{
    --co-canvas: Canvas;
    --co-panel: Canvas;
    --co-text: CanvasText;
    --co-muted: CanvasText;
    --co-divider: CanvasText;
    --co-control: ButtonFace;
    --co-hover: ButtonFace;
    --co-selected: ButtonFace;
    --co-border: ButtonText;
    --co-accent: LinkText;
    --co-on-accent: Canvas;
    --co-focus: Highlight;
    --co-success: CanvasText;
    --co-warning: CanvasText;
    --co-error: CanvasText;
    --co-code: Canvas;
    --co-disabled: GrayText;
    --switch-background-selected-default: Highlight;
    --switch-background-selected-hover: Highlight;
    --switch-border-selected-default: Highlight;
    --switch-border-selected-hover: Highlight;
    --switch-thumb-background-selected-default: HighlightText;
  }}
}}
""")
    return "".join(parts)
