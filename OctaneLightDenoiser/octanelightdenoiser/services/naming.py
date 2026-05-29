"""Naming engine — mirrors the original UI prototype exactly.

Rules (in priority order):
  1. A non-empty manual name wins.
  2. Otherwise the auto name = ``source`` with spaces removed + ``_DN``
     (e.g. "Denoise Albedo" -> "DenoiseAlbedo_DN", "KeyLight" -> "KeyLight_DN").
  3. The final name is sanitised so it is a valid EXR layer name
     (spaces -> '_', anything not [A-Za-z0-9_-] -> '_', collapse repeats).
  4. Duplicates are de-duped with a numeric suffix (_2, _3, ...).

The validation helpers (`has_invalid`) match the prototype so the UI shows the
same errors: empty, "No spaces or special characters" (fixable), duplicate.
"""
from __future__ import annotations

import re

_INVALID = re.compile(r"[^A-Za-z0-9_\-]")
_WS      = re.compile(r"\s+")
_MULTI_US = re.compile(r"_+")


def auto_name(source: str) -> str:
    """Auto name = sanitised source (spaces removed) + '_DN'.

    Sanitising here (not only in resolve_name) guarantees the name shown in the
    UI is exactly what Build writes. Otherwise a source with characters that
    sanitise away (e.g. a trailing '_') would display one name but build
    another, and the auto/manual flag would flip after a build.
    """
    base = sanitize(_WS.sub("", source or "")).strip("_")
    return (base or "AOV") + "_DN"


def sanitize(name: str) -> str:
    """Make a string safe as an EXR layer / Octane AOV name."""
    s = _WS.sub("_", name or "")
    s = _INVALID.sub("_", s)
    s = _MULTI_US.sub("_", s)
    return s


def has_invalid(name: str) -> bool:
    """True if name has whitespace or characters EXR/Octane won't accept."""
    if name is None:
        return False
    return bool(re.search(r"\s", name)) or bool(_INVALID.search(name))


def validate(name: str, *, name_counts: dict) -> tuple:
    """Return (error, fixable) for a selected row's name.

    name_counts: {final_name: count} across all selected rows (built by caller).
    """
    if name is None or name.strip() == "":
        return ("Name can't be empty", False)
    if has_invalid(name):
        return ("No spaces or special characters", True)
    if name_counts.get(name, 0) > 1:
        return ("Duplicate name — must be unique", False)
    return (None, False)


def resolve_name(custom: str, source: str, used: set) -> str:
    """Final, sanitised, de-duplicated name for an output AOV.

    `used` accumulates names already taken; pass the same set across all
    rows in one build so duplicates get _2/_3 suffixes deterministically.
    """
    raw = (custom or "").strip()
    if not raw:
        raw = auto_name(source)
    name = sanitize(raw).strip("_") or "AOV"
    base, n = name, 2
    while name in used:
        name = "%s_%d" % (base, n)
        n += 1
    used.add(name)
    return name
