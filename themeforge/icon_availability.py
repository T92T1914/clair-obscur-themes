"""Derive gallery availability from the same exact declarations used by the packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .android_iconpack import _components


@dataclass(frozen=True)
class MappingAvailability:
    included: bool
    exact_component_count: int
    packages: tuple[str, ...]


def mapping_availability(catalog: list[dict], components: Path,
                         captured_payload: bytes) -> dict[str, MappingAvailability]:
    """Validate declarations and bind their derived states to the source snapshot.

    A named app needs a row assigned to its own icon and exact package. A verified
    generic row counts only for the function it actually names. Package hints and
    current launcher behavior are separate from these declarations.
    """
    if not isinstance(catalog, list) or not catalog or type(captured_payload) is not bytes:
        raise ValueError("Expected an icon catalog and captured mapping bytes")
    ids, named_packages = set(), set()
    for entry in catalog:
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                or not entry["id"] or entry["id"] in ids
                or entry.get("kind") not in ("app", "function")):
            raise ValueError("Invalid or repeated icon availability identity")
        ids.add(entry["id"])
        if entry["kind"] == "app":
            package = entry.get("android_package")
            if (not isinstance(package, str)
                    or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", package)
                    or package in named_packages):
                raise ValueError("Expected distinct exact named package identities")
            named_packages.add(package)
    try:
        table, payload, _guards = _components(Path(components), catalog)
    except OSError as error:
        raise ValueError("Mapping declarations are unavailable") from error
    if payload != captured_payload:
        raise ValueError("Mapping declarations differ from the captured source snapshot")

    by_id = {entry["id"]: entry for entry in catalog}
    assigned = {identifier: [] for identifier in by_id}
    for row in table["mappings"]:
        entry = by_id[row["icon_id"]]
        # The pack's validator already enforces this exact package or verified
        # generic allowlist. Keep the named-app requirement explicit here.
        if entry["kind"] == "app" and row["android_package"] != entry["android_package"]:
            raise ValueError("Named mapping differs from its exact catalog package")
        assigned[entry["id"]].append(row)
    return {
        identifier: MappingAvailability(
            included=bool(rows), exact_component_count=len(rows),
            packages=tuple(sorted({row["android_package"] for row in rows})),
        )
        for identifier, rows in assigned.items()
    }
