"""Pure normalization + matching primitives for the exoplanet identity graph.

No DB, no I/O — deterministic, unit-tested in isolation (ported in spirit from the satellite
platform's identity/normalize.py).
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_NONWORD = re.compile(r"[^\w\s]+", re.UNICODE)


def norm_name(s: str | None) -> str:
    """Canonicalize a host/planet name for fuzzy comparison: casefold, punctuation -> space,
    collapse whitespace. 'Kepler-227 b' / 'KEPLER 227 B' -> 'kepler 227 b'. '' for empty/None."""
    if not s:
        return ""
    s = str(s).casefold()
    s = _NONWORD.sub(" ", s)
    return _WS.sub(" ", s).strip()


def _to_float(x) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def period_rel_diff(p1, p2) -> float | None:
    """Relative difference between two orbital periods, or None if either is missing/non-positive.

    Symmetric: |p1 - p2| / max(p1, p2). 0.0 = identical, 0.01 = 1% apart.
    """
    a, b = _to_float(p1), _to_float(p2)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return abs(a - b) / max(a, b)


def periods_match(p1, p2, tol: float = 0.01) -> bool:
    """True if two periods agree within `tol` relative difference (default 1%, per SPEC).

    A missing period never matches (returns False) — absence of evidence is not agreement.
    """
    d = period_rel_diff(p1, p2)
    return d is not None and d < tol


def rel_diff(v1, v2) -> float | None:
    """Symmetric relative difference for any positive scalar (radius, teff, rstar). None if either
    is missing or non-positive."""
    a, b = _to_float(v1), _to_float(v2)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return abs(a - b) / max(a, b)


def canonical_candidate_name(names: dict) -> str:
    """Pick the most human/scientific candidate name from the available designations.

    Priority: a published planet name (pl_name, e.g. 'Kepler-227 b') > TOI > KOI (kepoi_name) >
    CTOI. Falls back to the star label so a candidate always has a non-empty canonical_name.
    """
    if names.get("planet"):
        return str(names["planet"])
    if names.get("toi"):
        return f"TOI {names['toi']}"
    if names.get("koi"):
        return f"KOI {names['koi']}"
    if names.get("ctoi"):
        return f"CTOI {names['ctoi']}"
    return names.get("fallback", "UNKNOWN")
