"""Generate paired, data-only Windows Terminal color schemes outside desktop dist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import _checksum_bytes, _digest, _inventory, _json_bytes, _safe_destination, _zip_bytes
from .legal import license_text
from .tokens import contrast, load, luminance, validate

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
FRAGMENT = f"Clair-Obscur-Windows-Terminal-{VERSION}.json"
ARCHIVE = f"Clair-Obscur-Windows-Terminal-{VERSION}.zip"
NAMES = {name: f"Clair Obscur - {name}" for name in ("Clair", "Obscur")}
ANSI_FIELDS = (
    "black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
    "brightBlack", "brightRed", "brightGreen", "brightYellow",
    "brightBlue", "brightPurple", "brightCyan", "brightWhite",
)
CORE_ROLES = {"background": "code", "foreground": "text",
              "cursorColor": "focus", "selectionBackground": "selected"}
FOREGROUND_EXCEPTIONS = {"Clair": ("white", "brightWhite"), "Obscur": ("black", "brightBlack")}
ROLE_COLORS = {
    "Clair": {"black": "text", "red": "error", "green": "success", "yellow": "warning",
              "blue": "accent", "white": "panel", "brightBlack": "muted", "brightWhite": "on_accent"},
    "Obscur": {"black": "panel", "red": "error", "green": "success", "yellow": "warning",
               "blue": "accent", "white": "muted", "brightBlack": "divider",
               "brightBlue": "focus", "brightWhite": "text"},
}
# ANSI adds purple/cyan and distinct intensity slots absent from the shared roles.
# These values belong only to this adapter version, never to the original packages.
ANSI_EXTRAS = {
    "Clair": {
        "purple": "#744b88", "cyan": "#256971",
        "brightRed": "#b33b3f", "brightGreen": "#387555", "brightYellow": "#8e6112",
        "brightBlue": "#476f88", "brightPurple": "#805794", "brightCyan": "#2c7178",
    },
    "Obscur": {
        "purple": "#c3a4dc", "cyan": "#8acbd0", "brightRed": "#ffb8b8",
        "brightGreen": "#a6e0b3", "brightYellow": "#f4d391",
        "brightPurple": "#d7bcec", "brightCyan": "#a7dfe3",
    },
}


def _validated(document: dict) -> None:
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    try:
        validate(document)
    except (TypeError, AttributeError) as error:
        raise ValueError("Malformed token document") from error


def color_scheme(name: str, document: dict) -> dict:
    """Map one validated palette into the complete native scheme-only contract."""
    _validated(document)
    if name not in ("Clair", "Obscur"):
        raise ValueError("Theme name must be Clair or Obscur")
    palette = document["themes"][name]
    colors = {field: palette[role].lower() for field, role in ROLE_COLORS[name].items()}
    colors.update(ANSI_EXTRAS[name])
    assert set(colors) == set(ANSI_FIELDS)
    if len(set(colors.values())) != 16:
        raise ValueError(f"{name}: ANSI slots must remain distinct")
    background = palette["code"]
    for field, color in colors.items():
        if field not in FOREGROUND_EXCEPTIONS[name] and contrast(color, background) < 4.5:
            raise ValueError(f"{name}: ANSI {field} fails 4.5:1 on the default background")
    for white in ("white", "brightWhite"):
        for black in ("black", "brightBlack"):
            if contrast(colors[white], colors[black]) < 4.5:
                raise ValueError(f"{name}: ANSI neutral {white}/{black} fails 4.5:1")
    if contrast(palette['text'], background) < 4.5 or contrast(palette['text'], palette['selected']) < 4.5:
        raise ValueError(f"{name}: default or selected foreground fails 4.5:1")
    if contrast(palette['focus'], background) < 3:
        raise ValueError(f"{name}: cursor fails 3:1 on the default background")
    for normal, bright in zip(ANSI_FIELDS[:8], ANSI_FIELDS[8:]):
        if luminance(colors[bright]) <= luminance(colors[normal]):
            raise ValueError(f"{name}: ANSI {bright} must have higher luminance than {normal}")
    return {"name": NAMES[name], **{field: palette[role].lower() for field, role in CORE_ROLES.items()},
            **{field: colors[field] for field in ANSI_FIELDS}}


def render_terminal(document: dict) -> dict[str, bytes]:
    """Return the paired fragment, local archive and exact independent identities."""
    schemes = [color_scheme(name, document) for name in ("Clair", "Obscur")]
    payload = {FRAGMENT: _json_bytes({"schemes": schemes}),
               "LICENSE.txt": license_text().encode("utf-8")}
    files = {**payload, ARCHIVE: _zip_bytes(payload)}
    manifest = {
        "schema_version": 1, "generator": "themeforge.terminal", "version": VERSION,
        "token_schema": document["schema_version"], "token_version": document["version"],
        "tokens_sha256": _digest(_json_bytes(document)), "fragment": FRAGMENT, "archive": ARCHIVE,
        "schemes": NAMES, "core_roles": CORE_ROLES, "native_acceptance": "unverified",
        "scope": "Scheme colors only; no profiles, commands, font settings or installation",
        "contrast_scope": "14 foreground slots per default background plus neutral cross-pairs; not arbitrary ANSI pairs or native pixels",
        "foreground_exceptions": FOREGROUND_EXCEPTIONS,
        "neutral_pair_contrast": {
            name: {f"{white}/{black}": round(contrast(scheme[white], scheme[black]), 6)
                   for white in ("white", "brightWhite") for black in ("black", "brightBlack")}
            for name, scheme in zip(("Clair", "Obscur"), schemes)
        },
        "default_background_contrast": {
            name: {field: round(contrast(scheme[field], scheme["background"]), 6) for field in ANSI_FIELDS}
            for name, scheme in zip(("Clair", "Obscur"), schemes)
        },
        "files": [{"path": name, "bytes": len(data), "sha256": _digest(data)}
                  for name, data in sorted(files.items())],
    }
    files["manifest.json"] = _json_bytes(manifest)
    files["SHA256SUMS"] = _checksum_bytes(files)
    return files


def _safe_output(path: Path) -> Path:
    path = _safe_destination(path)
    if path == ROOT / "dist" or ROOT / "dist" in path.parents:
        raise ValueError("Terminal output must stay outside managed desktop dist")
    return path


def build_terminal(document: dict, output: Path, *, check: bool = False) -> dict:
    """Create a new flat output tree or compare existing bytes without repair."""
    files = render_terminal(document)
    output = _safe_output(Path(output))
    if check:
        if not output.is_dir():
            raise ValueError("Terminal check requires an existing generated output directory")
        actual, directories = _inventory(output)
        if actual != files or directories:
            raise ValueError("Terminal output differs: changed, missing or extra entries")
    else:
        if output.exists():
            raise ValueError("Terminal generation requires a new output directory; existing entries are preserved")
        output.parent.mkdir(parents=True, exist_ok=True)
        output = _safe_output(output)
        output.mkdir(exist_ok=False)
        for name, data in files.items():
            target = _safe_destination(output / name)
            with target.open("xb") as stream:
                stream.write(data)
    return json.loads(files["manifest.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=ROOT / "tokens.json")
    parser.add_argument("--output", type=Path, required=True, help="A new directory outside managed desktop dist")
    parser.add_argument("--check", action="store_true", help="Compare exact generated output without writing")
    args = parser.parse_args(argv)
    try:
        manifest = build_terminal(load(args.tokens), args.output, check=args.check)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.exit(1, f"Terminal generation: {error}\n")
    print(f'{"Verified" if args.check else "Generated"} paired Windows Terminal {manifest["version"]} candidate; native acceptance unverified')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
