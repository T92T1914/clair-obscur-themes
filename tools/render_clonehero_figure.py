"""Render the Clone Hero route figure with the mechanism renderer.

This only points the existing renderer at its own configuration and receipt, so
the figure is drawn by the same code from the same Obscur tokens and fonts.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_mechanism  # noqa: E402

ROOT = render_mechanism.ROOT
render_mechanism.CONFIG = ROOT / "docs/clone-hero-figure.json"
render_mechanism.RECEIPT = ROOT / "docs/clone-hero-rendering.json"


def check() -> None:
    render_mechanism.check()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--font-dir", type=Path, default=os.environ.get("OBSCUR_FONT_DIR"))
    args = parser.parse_args()
    if args.check:
        check()
    else:
        if args.font_dir is None:
            parser.error("Supply --font-dir or OBSCUR_FONT_DIR with the actual Inter TTF directory")
        render_mechanism.render(Path(args.font_dir))


if __name__ == "__main__":
    main()
