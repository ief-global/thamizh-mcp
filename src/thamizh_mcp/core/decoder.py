"""Linguistic decoding — lives in code, tested once, never re-derived by the model.

Implemented: FST POS tag → சொல் வகை (Tholkappiyam Collatikāram word classes);
FST case tag → வேற்றுமை (Tholkappiyam வேற்றுமையியல், eight cases).
Phase 3 remainder: decode_fst_tags → full பகுபத உறுப்பு Formation (Nannūl six-part labels).
"""
from __future__ import annotations

from typing import Optional

from thamizh_mcp.schema import GrammarCase, Pos, SourceRef, WordClass

THOLKAPPIYAM_COLLATIKARAM = SourceRef(
    name="Tholkappiyam", tier="anchor", authority="Tholkappiyam",
    ref="சொல்லதிகாரம் — word classes பெயர்/வினை/இடை/உரி", retrieved="classical (edition-pinned in Phase 4)")
THOLKAPPIYAM_VETRUMAI = SourceRef(
    name="Tholkappiyam", tier="anchor", authority="Tholkappiyam",
    ref="சொல்லதிகாரம், வேற்றுமையியல் — the eight வேற்றுமை", retrieved="classical (edition-pinned in Phase 4)")

# ThamizhiMorph POS tag → schema Pos (Tholkappiyam's four-way word-class frame).
_POS_MAP: dict[str, Pos] = {
    "noun": "பெயர்ச்சொல்", "propn": "பெயர்ச்சொல்", "pronoun": "பெயர்ச்சொல்", "pron": "பெயர்ச்சொல்",
    "verb": "வினைச்சொல்", "vb": "வினைச்சொல்",
    "part": "இடைச்சொல்", "particle": "இடைச்சொல்", "postp": "இடைச்சொல்",
    "adj": "உரிச்சொல்", "adv": "உரிச்சொல்",
}
_WORD_CLASS: dict[Pos, WordClass] = {
    "பெயர்ச்சொல்": "பெயர்", "வினைச்சொல்": "வினை", "இடைச்சொல்": "இடை", "உரிச்சொல்": "உரிச்சொல்",
}

# FST case tag → (number, name, function). Eight வேற்றுமை per Tholkappiyam;
# sociative ஒடு/உடன் sits inside the third case.
_CASE_MAP: dict[str, tuple[int, str, str]] = {
    "nom": (1, "முதல் வேற்றுமை (எழுவாய்)", "subject"),
    "acc": (2, "இரண்டாம் வேற்றுமை (ஐ)", "direct object"),
    "inst": (3, "மூன்றாம் வேற்றுமை (ஆல்)", "instrument/agency"),
    "soc": (3, "மூன்றாம் வேற்றுமை (ஒடு/உடன்)", "sociative/accompaniment"),
    "dat": (4, "நான்காம் வேற்றுமை (கு)", "dative/recipient"),
    "abl": (5, "ஐந்தாம் வேற்றுமை (இன்/இலிருந்து)", "ablative/comparison"),
    "gen": (6, "ஆறாம் வேற்றுமை (அது/உடைய)", "genitive/possession"),
    "loc": (7, "ஏழாம் வேற்றுமை (கண்/இல்)", "locative/இடப்பொருள்"),
    "voc": (8, "எட்டாம் வேற்றுமை (விளி)", "vocative/address"),
}


def map_pos(fst_pos_tag: str) -> Pos:
    return _POS_MAP.get(fst_pos_tag.lower(), "unknown")


def word_class_of(pos: Pos) -> WordClass:
    return _WORD_CLASS.get(pos, "unknown")


def map_case(tags: list[str]) -> Optional[GrammarCase]:
    """First recognized case tag → GrammarCase; None when no case tag present."""
    for t in tags:
        hit = _CASE_MAP.get(t.lower())
        if hit:
            return GrammarCase(number=hit[0], name=hit[1], function=hit[2])
    return None


def decode_fst_tags(raw_analysis: str):
    """Full பகுபத உறுப்பு Formation decode — lands in Phase 3 (blueprint §8)."""
    raise NotImplementedError("Formation decoder lands in Phase 3 — blueprint §8, tamil-grammar.md")
