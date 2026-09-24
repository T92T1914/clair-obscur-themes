"""Read the repository's canonical license for standalone theme downloads."""

from pathlib import Path
import stat


LICENSE_PATH = Path(__file__).resolve().parents[1] / "LICENSE"


def license_text() -> str:
    """Return normalized plain text without following a linked license file."""
    info = LICENSE_PATH.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("Canonical license must be a regular file, not a link")
    # A bounded read also prevents an accidental large file becoming a download.
    with LICENSE_PATH.open("rb") as stream:
        payload = stream.read(65537)
    if len(payload) > 65536:
        raise ValueError("Canonical license is unexpectedly large")
    text = payload.decode("utf-8").replace("\r\n", "\n")
    if not text.startswith("MIT License\n") or any(value in text for value in ("/*", "*/", "\x00", "\r")):
        raise ValueError("Canonical license must be plain MIT text safe for a CSS comment")
    return text.rstrip("\n") + "\n"


def license_comment() -> str:
    """Keep the complete grant separate from Equicord's first metadata block."""
    return "/*\n" + license_text() + "*/\n"
