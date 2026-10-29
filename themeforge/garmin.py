"""Generate a separate watch-face palette without changing desktop packages."""

from __future__ import annotations

import argparse
from pathlib import Path

from .legal import license_comment
from .tokens import load, validate


VERSION = "0.9.0"


def render_palette(document: dict) -> str:
    """Map every validated semantic role to a literal Monkey C color."""
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("Expected a token document with an integer schema version")
    validate(document)
    lines = [
        "// Generated from validated semantic tokens by themeforge.garmin. Do not edit.\n",
        license_comment(),
        "\nmodule ThemePalette {\n",
        f'    const WATCHFACE_VERSION = "{VERSION}";\n',
        f'    const TOKEN_SCHEMA = {document["schema_version"]};\n',
        f'    const TOKEN_VERSION = "{document["version"]}";\n',
    ]
    for name in ("Clair", "Obscur"):
        for role, color in sorted(document["themes"][name].items()):
            lines.append(f"    const {name.upper()}_{role.upper()} = 0x{color[1:].upper()};\n")
    lines.append("}\n")
    return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=root / "tokens-monochrome.json",
                        help="Current monochrome tokens by default; select tokens.json for the legacy palette")
    parser.add_argument("--output", type=Path, default=root / "garmin/watchface/source/GeneratedPalette.mc")
    parser.add_argument("--check", action="store_true", help="Compare only; never write source")
    options = parser.parse_args(argv)
    expected = render_palette(load(options.tokens)).encode("utf-8")
    if options.output.is_symlink():
        raise ValueError("The generated palette output must not be a symlink")
    if options.check:
        if not options.output.is_file() or options.output.read_bytes() != expected:
            raise ValueError("Generated Garmin palette differs from the validated tokens")
    else:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_bytes(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
