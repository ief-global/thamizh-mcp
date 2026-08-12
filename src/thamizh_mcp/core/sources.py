"""The source registry (D-017) — one machine-readable place saying what each source IS.

WHY THIS EXISTS. Licence and quality facts used to live in three prose locations: LICENSING.md,
data/PINS.md and per-adapter docstrings. Nothing checked that a shipped adapter had been through any
of them, and nothing in `src/` could read them. The cost was concrete: the S2PT word lists were
quietly load-bearing for weeks under a "MIT" claim that had no basis upstream. The defect was not
that S2PT is a weak source — weak sources are fine — but that its weakness was not DECLARED
anywhere a machine could check.

    Authenticity comes from every claim carrying a graded, citable provenance the user can
    check. NOT from every source being impeccable.

TWO INDEPENDENT AXES (D-016). `grade` is evidential standing; `redistribution` is what we may
legally do with the bytes. Collapsing them is the exact mistake D-016 was written to correct: the
Madras Tamil Lexicon is simultaneously the most authoritative lexicon we have (grade A) and the most
restrictively licensed (consult-and-cite). Both are true; neither implies the other.

WHAT THIS MODULE ENFORCES. `cap_for()` is a ceiling, not a score — it never raises a confidence, it
only refuses to let one exceed what its source can support. Today every cap sits at or above what
the classifier actually emits, so it binds nothing; that is the point of a guard. It starts binding
the day someone raises a confidence past its source's standing, which is precisely when nobody will
be thinking about the registry.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

from thamizh_mcp import config

# A source we have no entry for gets the floor, not the benefit of the doubt. An unregistered source
# is an unreviewed one, and the registry is only worth having if omission is the punished case.
UNREGISTERED_CAP = 0.55


@lru_cache(maxsize=1)
def _registry() -> dict:
    """The parsed registry, or {} if absent. A missing registry costs grading, never a crash."""
    try:
        return json.loads(config.SOURCES_FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def all_sources() -> dict[str, dict]:
    return _registry().get("sources", {})


def grades() -> dict[str, dict]:
    return {k: v for k, v in _registry().get("grades", {}).items() if k != "comment"}


@lru_cache(maxsize=64)
def _by_name() -> dict[str, str]:
    """Adapter `name` string → registry key. The adapter's own name is the join key, so a rename
    that misses the registry surfaces as an unregistered source rather than silently passing."""
    return {e["name"]: k for k, e in all_sources().items() if e.get("name")}


def entry(source_name: str) -> Optional[dict]:
    """The registry entry for a source, looked up by its display name, or None if unregistered."""
    src = all_sources()
    if source_name in src:            # allow the registry key itself
        return src[source_name]
    key = _by_name().get(source_name)
    return src.get(key) if key else None


def grade_of(source_name: str) -> Optional[str]:
    e = entry(source_name)
    return e.get("grade") if e else None


def cap_for(source_name: str) -> float:
    """The highest confidence this source's GRADE can support. Unregistered → the floor."""
    e = entry(source_name)
    if not e:
        return UNREGISTERED_CAP
    g = grades().get(e.get("grade", ""), {})
    cap = g.get("confidence_cap")
    return float(cap) if isinstance(cap, (int, float)) else UNREGISTERED_CAP


def cap(source_name: str, confidence: float) -> float:
    """Ceiling `confidence` at what `source_name` can support. Never raises a confidence."""
    return min(float(confidence), cap_for(source_name))


def describe(source_name: str) -> Optional[str]:
    """A one-line, user-facing statement of standing — what "on whose authority?" deserves.

    Deliberately names the licence gap out loud for an unstated source. A reader is better served
    by "grade D … licence unstated" than by a bare confidence number they cannot interpret.
    """
    e = entry(source_name)
    if not e:
        return None
    bits = [f"grade {e['grade']}"]
    g = grades().get(e["grade"], {})
    if g.get("means"):
        bits.append(g["means"].rstrip("."))
    if e.get("licence_status") == "unstated":
        bits.append("⚠️ upstream licence UNSTATED")
    else:
        bits.append(f"licence: {e['licence']}")
    bits.append(f"redistribution: {e['redistribution']}")
    return " · ".join(bits)


def annotate(ref: Any) -> Any:
    """Stamp a SourceRef with its registry grade and licence, in place.

    Called at the point a claim is assembled so the grade travels with the answer instead of living
    only in a file nobody reading the output will open.
    """
    e = entry(getattr(ref, "name", "") or "")
    if e is not None:
        ref.grade = e.get("grade")
        ref.licence = e.get("licence")
        ref.redistribution = e.get("redistribution")
    return ref
