"""Origin classifier (objective 1): orthographic + phonotactic rules and signal fusion.

The rule logic is pure and offline — signals (FST parse, S2PT membership) are passed in directly,
so these run without foma. One live end-to-end test (needs_fst) exercises the real FST path.
"""
import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from thamizh_mcp import config
from thamizh_mcp.core import classifier
from thamizh_mcp.core.classifier import classify_origin, forbidden_final, forbidden_initial, grantha_letters_in
from thamizh_mcp.core.engine import Engine


# --- orthographic / phonotactic helpers ---

def test_grantha_detection():
    assert grantha_letters_in("ஜோதி") == ["ஜ"]
    assert grantha_letters_in("பாஷை") == ["ஷ"]
    assert grantha_letters_in("மரம்") == []


def test_forbidden_initial_rule():
    assert forbidden_initial("ரயில்") == "ர்"   # ர cannot begin a native word
    assert forbidden_initial("லாரி") == "ல்"
    assert forbidden_initial("மரம்") is None      # ம is a valid initial
    assert forbidden_initial("அகராதி") is None    # vowels always valid


def test_forbidden_final_rule():
    assert forbidden_final("கேக்") == "க்"        # bare vallinam final (cake)
    assert forbidden_final("மரம்") is None         # ம் is a permitted final
    assert forbidden_final("பணம்") is None


# --- classification decisions (signals injected) ---

def test_grantha_proves_borrowed_not_sanskrit():
    """Grantha marks a non-native SOUND, not a source language.

    Reading it as a Sanskrit signal produced eleven confident-wrong answers in a 108-word everyday
    sweep — பஸ், ஸ்கூல், ஹோட்டல், ஆபீஸ், நர்ஸ், ஸ்டேஷன், கிளாஸ், ஹாஸ்பிட்டல் (English), ஜன்னல்
    (Portuguese janela), ஜாமீன் and ஜில்லா (Urdu) — every one labelled வடசொல் at 0.9. What the
    orthography licenses is `is_native=False`; the source needs a lexicon we do not have offline.
    """
    o = classify_origin("ஜோதி", fst_native_parse=None, in_s2pt=False)  # ஜ is a Grantha letter
    assert o.is_native is False, "Grantha DOES prove the word is not native"
    assert o.class_ == "unknown", "but it does NOT prove the source is Sanskrit"
    assert o.borrowed_from is None
    assert {a["class"] for a in o.alternatives} == {"வடசொல்", "loanword"}
    assert any("Grantha" in (s.ref or "") or "எழுத்து" in (s.ref or "") for s in o.sources)


def test_grantha_does_not_call_english_loans_sanskrit():
    """The regression that motivated the change — these are English, Portuguese and Urdu."""
    for word in ("பஸ்", "ஸ்கூல்", "ஹோட்டல்", "ஆபீஸ்", "நர்ஸ்", "ஜன்னல்", "ஜாமீன்", "ஜில்லா"):
        o = classify_origin(word, fst_native_parse=None, in_s2pt=False)
        assert o.class_ != "வடசொல்", f"{word} is not Sanskrit"
        assert o.is_native is False, f"{word} is certainly borrowed"


def test_forbidden_initial_is_loanword():
    o = classify_origin("ரயில்", fst_native_parse=None, in_s2pt=False)
    assert o.is_native is False, "the rule DOES prove the word is not native"
    assert o.class_ == "unknown", "but it does NOT prove the source language"
    assert "முதல் எழுத்து" in o.evidence
    assert {a["class"] for a in o.alternatives} == {"வடசொல்", "loanword"}

    # The word that exposed it: Sanskrit, and it must no longer be called a non-Sanskrit loan.
    r = classify_origin("ரூபம்", fst_native_parse=None, in_s2pt=False)
    assert r.class_ != "loanword" and r.is_native is False


def test_bare_vallinam_final_still_asserts_loanword():
    """Deliberately NOT changed with the other two — a different signal, not the same defect.

    Those rules turn on which letters appear, which is source-neutral. This one turns on
    morphological assimilation: Sanskrit borrowings are adapted and take Tamil endings (ரூபம்,
    யோகம், மனிதன்), so they never surface with a bare vallinam final. An unadapted final really is
    evidence of a non-Sanskrit loan.
    """
    o = classify_origin("கேக்", fst_native_parse=None, in_s2pt=False)   # cake
    assert o.class_ == "loanword" and o.is_native is False


def test_forbidden_final_is_loanword():
    o = classify_origin("கேக்", fst_native_parse=None, in_s2pt=False)
    assert o.class_ == "loanword" and "இறுதி எழுத்து" in o.evidence


def test_s2pt_membership_is_positive_vadasol_evidence_but_scored_low():
    """S2PT is வடசொல்-scoped (upstream README: "வடசொல் to தமிழ்"), so membership names Sanskrit.

    This used to return `unknown` on the grounds that no orthographic marker separates வடசொல் from
    loanword — true, but it ignored what the source is ABOUT and discarded the one thing the list
    attests. Scored 0.55, the lowest committing score in the module, because the source is
    provisional: no upstream licence, unmaintained since 2020, scraped upstreams.
    """
    o = classify_origin("சந்திரன்", fst_native_parse=None, in_s2pt=True)
    assert o.class_ == "வடசொல்" and o.is_native is False
    assert o.borrowed_from == "Sanskrit"
    assert o.confidence == 0.55, "must stay below the 0.8 an en.wiktionary etymology earns"
    # the weakness is stated in the answer, not hidden in a doc
    assert "unmaintained" in o.evidence and "no stated licence" in o.evidence
    assert "evidence, NOT authority" in o.evidence
    assert {a["class"] for a in o.alternatives} == {"loanword", "unknown"}


def test_a_wiktionary_etymology_always_outranks_the_s2pt_list():
    """Precedence: the provisional list is a floor, never an override."""
    ety = {"relation": "borrowed", "is_native": False, "source_lang": "en",
           "source_lang_name": "English", "source_word": "bus", "template": "bor",
           "certainty": "stated", "citation": "u"}
    o = classify_origin("பஸ்", fst_native_parse=None, in_s2pt=True, etymology=ety)
    assert o.class_ == "loanword" and o.borrowed_from == "English"
    assert o.confidence > 0.55


def test_the_s2pt_lists_really_are_sanskrit_scoped():
    """Guards the assumption the branch above rests on. If English loans ever appear as S2PT
    headwords, the வடசொல் inference is invalid and must be withdrawn."""
    import csv, glob
    keys = set()
    for f in glob.glob("data/equivalents/sanskrit-to-pure-tamil/*.csv"):
        for row in csv.DictReader(io.open(f, encoding="utf-8")):
            if (k := (row.get("INDIC") or "").strip()):
                keys.add(k)
    assert len(keys) > 1500, "vendored lists look truncated"
    for english_loan in ("காபி", "டீ", "பஸ்", "ரயில்", "கேக்", "ஸ்கூல்", "ஹோட்டல்", "ரேடியோ"):
        assert english_loan not in keys, (
            f"{english_loan} is an ENGLISH loan but appears as a வடசொல் headword — the "
            "Sanskrit-scoping assumption in classify_origin is broken")


def test_a_malformed_but_tamil_grapheme_does_not_crash():
    """`நுா` is நு followed by a second vowel sign — malformed, but every codepoint IS Tamil, so it
    passes normalize(). open-tamil's splitMeiUyir raises ValueError on it, which crashed
    classify_origin and would have been a 500 from the web head. An unsplittable grapheme carries
    no consonant signal; the honest answer is a class, not a traceback."""
    o = classify_origin("நுா", fst_native_parse=None, in_s2pt=False)
    assert o.class_ == "unknown"
    assert forbidden_initial("நுா") is None and forbidden_final("நுா") is None


def test_native_fst_parse_is_iyarcol():
    o = classify_origin("மரம்", fst_native_parse=True, in_s2pt=False)
    assert o.class_ == "இயற்சொல்" and o.is_native is True
    assert 0.0 < o.confidence < 1.0                       # moderate — naturalized borrowings can look native


def test_no_signal_is_unknown_not_a_guess():
    o = classify_origin("மரம்", fst_native_parse=False, in_s2pt=False)
    assert o.class_ == "unknown" and o.confidence == 0.0
    o2 = classify_origin("மரம்", fst_native_parse=None, in_s2pt=False)
    assert o2.class_ == "unknown" and "foma" in o2.evidence   # FST-unavailable reason surfaced


# --- engine wiring: origin gates native_equivalent ---

class _FakeMorph:
    name, tier = "ThamizhiMorph", "anchor"
    async def lookup(self, w):
        from thamizh_mcp.adapters.base import AdapterResult
        from thamizh_mcp.schema import MorphAnalysis, SourceRef
        return AdapterResult(fields={"all_analyses": [MorphAnalysis(lemma=w, pos="noun", tags=[])]},
                             sources=[SourceRef(name="ThamizhiMorph", tier="anchor")], tier="anchor")


def test_engine_native_word_gates_equivalent_off():
    a = asyncio.run(Engine(morph=_FakeMorph()).analyze("மரம்", "மரம்"))
    assert a.origin.class_ == "இயற்சொல்"
    assert a.native_equivalent.applicable is False
    assert not any(g.field == "native_equivalent" for g in a.gaps)  # native = resolved, not a gap


def test_engine_grantha_word_is_borrowed_source_undetermined():
    """The engine surfaces the undetermined source as an explicit gap — the design rule working.

    A Grantha word used to resolve to வடசொல் with no gap. It now reports what is actually known
    (not native) and records a gap for what is not (which language), so a consumer can see the
    difference between an answer and a guess.
    """
    a = asyncio.run(Engine(morph=_FakeMorph()).analyze("ஜோதி", "ஜோதி", include=["origin"]))
    assert a.origin.class_ == "unknown" and a.origin.is_native is False
    assert any(g.field == "origin" for g in a.gaps), "an undetermined source must be an honest gap"


needs_fst = pytest.mark.skipif(not config.flookup_available(),
                               reason="flookup/FSTs not on this machine (see data/PINS.md)")


@needs_fst
def test_live_native_word_is_iyarcol():
    from thamizh_mcp.adapters.thamizhimorph import ThamizhiMorphAdapter
    a = asyncio.run(Engine(morph=ThamizhiMorphAdapter()).analyze("மரம்", "மரம்", include=["origin"]))
    assert a.origin.class_ == "இயற்சொல்" and a.origin.is_native is True
