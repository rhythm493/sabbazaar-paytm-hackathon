"""Deterministic ISBN handling. Canonical form is ISBN-13 digits only."""

from __future__ import annotations

import re


def _isbn13_check(first12: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def _isbn10_valid(s: str) -> bool:
    total = 0
    for i, ch in enumerate(s):
        v = 10 if (ch in "Xx" and i == 9) else (int(ch) if ch.isdigit() else -1)
        if v < 0:
            return False
        total += v * (10 - i)
    return total % 11 == 0


def normalize_isbn(raw: str | None) -> str | None:
    """Return a checksum-valid ISBN-13, converting ISBN-10. None if absent or invalid."""
    if not raw:
        return None
    s = re.sub(r"[\s\-]", "", raw.strip())
    if re.fullmatch(r"\d{13}", s):
        return s if s[:3] in ("978", "979") and _isbn13_check(s[:12]) == s[12] else None
    if re.fullmatch(r"\d{9}[\dXx]", s):
        if not _isbn10_valid(s):
            return None
        core = "978" + s[:9]
        return core + _isbn13_check(core)
    return None
