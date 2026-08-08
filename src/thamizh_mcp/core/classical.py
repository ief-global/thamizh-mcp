"""Runtime access to the pinned classical texts — so a claim can quote its நூற்பா, not just cite it.

WHY THIS EXISTS. The project's promise is that every grammatical claim is grounded in Tholkappiyam
and Nannūl. Until now that was delivered at DESIGN time only: `data/grammar/*.json` carried நூற்பா
numbers and `tests/test_citations.py` proved each number resolves in the pinned edition. Real, but a
reader asking "on whose authority?" got a chapter name — `SourceRef.verse` was always None and the
462 Nannūl verses and Tholkappiyam's 1,486 sat unused at runtime.

That gap had a measurable cost. The question of what the second `த்` in வா + த் + த் + ஏன் is called
took several rounds to settle, and the answer — நன்னூல் 133, which names the six பகுபத உறுப்பு
including சந்தி — was sitting in this repo the whole time. It had to be looked up by hand because
nothing in `src/` could read it.

ADDRESSING. The two texts are numbered differently and it is not cosmetic:
  · **Nannūl** — CONTINUOUS 1–462, so a bare number is unambiguous.
  · **Tholkappiyam** — நூற்பா RESTART at 1 in every இயல் and collide across இயல் and அதிகாரம், so a
    citation MUST be qualified அதிகாரம் › இயல் › நூற்பா. Passing a bare number here is a bug, not a
    convenience, and this module has no API that would let you.

HONESTY. A verse this edition does not print returns None and the caller keeps `verse=None` with its
note — exactly as D-011 requires. Never fabricate a number to make a citation look complete.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from thamizh_mcp import config
from thamizh_mcp.schema import SourceRef

NANNUL_TOTAL = 462


@lru_cache(maxsize=2)
def _load(name: str) -> dict:
    """The pinned artifact, or {} if absent. A missing text costs quotation, never a crash."""
    try:
        return json.loads((config.CLASSICAL_DIR / f"{name}.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _clean(text: str) -> str:
    return " ".join(str(text).split())


def nannul_verse(verse: int | str) -> Optional[str]:
    """நன்னூல் நூற்பா text by its continuous number, or None if not printed in this edition."""
    v = _load("nannul").get("verses", {}).get(str(verse))
    return _clean(v) if v else None


def tholkappiyam_verse(athikaram: str, iyal: str, verse: int | str) -> Optional[str]:
    """தொல்காப்பியம் நூற்பா text. All three coordinates are required — numbers restart per இயல்."""
    node = _load("tholkappiyam").get("athikaram", {}).get(athikaram, {}).get(iyal, {})
    v = node.get(str(verse))
    return _clean(v) if v else None


def cite_nannul(verse: int | str, ref: str) -> SourceRef:
    """A Nannūl SourceRef carrying the verse number AND its text where the edition prints it."""
    text = nannul_verse(verse)
    return SourceRef(
        name="Nannūl", tier="anchor", authority="Nannūl",
        ref=ref, verse=f"நூற்பா {verse}", verse_text=text,
        retrieved=_load("nannul").get("edition") or "Project Madurai (pinned; see data/PINS.md)")


def cite_tholkappiyam(athikaram: str, iyal: str, verse: int | str, ref: str) -> SourceRef:
    """A Tholkappiyam SourceRef. The verse label carries அதிகாரம் › இயல் › நூற்பா, never a bare number."""
    text = tholkappiyam_verse(athikaram, iyal, verse)
    return SourceRef(
        name="Tholkappiyam", tier="anchor", authority="Tholkappiyam",
        ref=ref, verse=f"{athikaram} › {iyal} › நூற்பா {verse}", verse_text=text,
        retrieved=_load("tholkappiyam").get("edition")
        or "Project Madurai (pinned; see data/PINS.md)")


def attribution(name: str) -> Optional[str]:
    """The edition's own attribution line. Project Madurai grants free distribution PROVIDED the
    header travels with the text, so any surface that quotes a verse must be able to show this."""
    d = _load(name)
    return d.get("attribution") or d.get("edition_credits")
