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


@lru_cache(maxsize=4)
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


# Which pinned commentary covers which அதிகாரம், by commentator. நச்சினார்க்கினியர் covers
# எழுத்ததிகாரம் (D-024, a proof-read Project Madurai etext) and சொல்லதிகாரம் (D-027, OCR of a TVA
# scan); இளம்பூரணர் covers சொல்லதிகாரம் (D-027, OCR of a TVA scan); சேனாவரையர் covers
# சொல்லதிகாரம் (D-028, OCR of a two-volume TVA-collection edition). நச்சினார்க்கினியர் is the
# default so the அதிகாரம் read uniformly.
DEFAULT_COMMENTATOR = "நச்சினார்க்கினியர்"
_URAI = {
    ("எழுத்ததிகாரம்", "நச்சினார்க்கினியர்"): "tholkappiyam_eluthu_urai",
    ("சொல்லதிகாரம்", "நச்சினார்க்கினியர்"): "tholkappiyam_sol_urai_nacchinarkkiniyar",
    ("சொல்லதிகாரம்", "இளம்பூரணர்"): "tholkappiyam_sol_urai_ilampuranar",
    ("சொல்லதிகாரம்", "சேனாவரையர்"): "tholkappiyam_sol_urai_senavaraiyar",
}
_ATHIKARAM_OF = {name: a for (a, _), name in _URAI.items()}
# The registry entry (data/sources.json) a commentary citation is graded under.
URAI_SOURCE_NAME = ("Tholkappiyam சொல்லதிகாரம் — classical commentaries "
                    "(நச்சினார்க்கினியர், இளம்பூரணர், சேனாவரையர்)")
NANNUL_URAI_SOURCE_NAME = "Nannūl பதவியல் — commentaries (நன்னூல் உரைவளம் 5, cited pages)"


def commentators(athikaram: str) -> list[str]:
    """The commentators whose உரை we hold for this அதிகாரம், default first."""
    held = [c for a, c in _URAI if a == athikaram]
    return sorted(held, key=lambda c: c != DEFAULT_COMMENTATOR)


def urai_artifact(athikaram: str, commentator: str = DEFAULT_COMMENTATOR) -> Optional[str]:
    """The data/classical artifact name for this commentary (for `attribution`), or None."""
    return _URAI.get((athikaram, commentator))


@lru_cache(maxsize=8)
def _urai_index(athikaram: str, commentator: str) -> dict[tuple[str, str], dict]:
    """(இயல், நூற்பா) of OUR text → the commentary unit aligned to it, merged units included."""
    name = _URAI.get((athikaram, commentator))
    units = _load(name).get("units", []) if name else []
    idx: dict[tuple[str, str], dict] = {}
    for u in units:
        for c in [u.get("aligned_to")] + (u.get("also_covers") or []):
            if c:
                idx[(c["iyal"], str(c["verse"]))] = u
    return idx


def tholkappiyam_urai(athikaram: str, iyal: str, verse: int | str,
                      commentator: str = DEFAULT_COMMENTATOR) -> Optional[dict]:
    """The classical commentary on one Tholkappiyam நூற்பா, or None where we hold none.

    Keyed by OUR coordinates. The commentary editions number continuously and divide some இயல்
    differently, so they are matched to our verses by text at build time, never by number. The
    unit carries the verse as the commentary prints it and the உரை. Quoting it obliges
    `attribution(urai_artifact(athikaram, commentator))`.

    ⚠️ The சொல்லதிகாரம் commentaries are archive.org OCR, not proof-read: each unit names the scan
    `pages` it came from, and a quotation must be checked against that page before a rule cites it
    (data/classical/verified_quotations.json records the ones that were).
    """
    return _urai_index(athikaram, commentator).get((iyal, str(verse)))


@lru_cache(maxsize=1)
def verified_quotations() -> dict[str, dict]:
    """id → a commentary passage that was read against its SCAN PAGE (D-027). The OCR is not
    proof-read, so these are the only commentary passages a rule may cite."""
    return {q["id"]: q for q in _load("verified_quotations").get("quotations", [])}


def cite_urai(quotation_id: str, ref: str) -> SourceRef:
    """A SourceRef quoting a verified commentary passage, as printed, with its page (D-028, D-029).

    A Tholkappiyam commentary is filed under the நூற்பா it comments on, by OUR coordinates; a Nannūl
    commentary under OUR Nannūl number. The page is the edition's printed page (and volume, for a
    multi-volume edition); a proof-read etext has none."""
    q = verified_quotations()[quotation_id]
    d = _load(q["artifact"])
    commentator = q.get("commentator") or d.get("commentator")
    page = ((f"vol. {q['volume']}, " if q.get("volume") else "") + f"p. {q['printed_page']}"
            if q.get("printed_page") else "proof-read etext")
    if q.get("nannul_verse"):
        return SourceRef(
            name=NANNUL_URAI_SOURCE_NAME, tier="anchor", authority="Nannūl",
            ref=f"{commentator} உரை, {d.get('text_ta', '')}, {page} — {ref}",
            verse=f"நூற்பா {q['nannul_verse']} ({commentator} உரை)",
            verse_text=q["as_printed"],
            retrieved=(d.get("edition") or {}).get("publisher"))
    u = q["unit"]
    athikaram = _ATHIKARAM_OF.get(q["artifact"], "சொல்லதிகாரம்")
    return SourceRef(
        name=URAI_SOURCE_NAME if athikaram == "சொல்லதிகாரம்" else "Tholkappiyam",
        tier="anchor", authority="Tholkappiyam",
        ref=f"{commentator} உரை, {page} — {ref}",
        verse=f"{athikaram} › {u['iyal']} › நூற்பா {u['verse']} ({commentator} உரை)",
        verse_text=q["as_printed"],
        retrieved=(d.get("edition") or {}).get("publisher") if isinstance(d.get("edition"), dict)
        else d.get("edition"))


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
