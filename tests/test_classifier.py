"""Origin classifier (objective 1): orthographic + phonotactic rules and signal fusion.

The rule logic is pure and offline — signals (FST parse, I2PT membership) are passed in directly,
so these run without foma. One live end-to-end test (needs_fst) exercises the real FST path.
"""
import asyncio
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
    o = classify_origin("ஜோதி", fst_native_parse=None, in_i2pt=False)  # ஜ is a Grantha letter
    assert o.is_native is False, "Grantha DOES prove the word is not native"
    assert o.class_ == "unknown", "but it does NOT prove the source is Sanskrit"
    assert o.borrowed_from is None
    assert {a["class"] for a in o.alternatives} == {"வடசொல்", "loanword"}
    assert any("Grantha" in (s.ref or "") or "எழுத்து" in (s.ref or "") for s in o.sources)


def test_grantha_does_not_call_english_loans_sanskrit():
    """The regression that motivated the change — these are English, Portuguese and Urdu."""
    for word in ("பஸ்", "ஸ்கூல்", "ஹோட்டல்", "ஆபீஸ்", "நர்ஸ்", "ஜன்னல்", "ஜாமீன்", "ஜில்லா"):
        o = classify_origin(word, fst_native_parse=None, in_i2pt=False)
        assert o.class_ != "வடசொல்", f"{word} is not Sanskrit"
        assert o.is_native is False, f"{word} is certainly borrowed"


def test_forbidden_initial_proves_borrowed_not_the_source():
    """A முதல் எழுத்து violation proves non-nativeness, not WHICH language.

    Sanskrit borrowings break the rule as readily as English ones — ரூபம் (Skt rūpa) and ராஜா sit
    beside ரயில் and லாரி. Calling them all `loanword` (which in the Tholkappiyam frame means a
    NON-Sanskrit borrowing) got the English ones right and ரூபம் wrong, by the same ungrounded
    inference. Lucky hits are still guesses.
    """
    o = classify_origin("ரயில்", fst_native_parse=None, in_i2pt=False)
    assert o.is_native is False, "the rule DOES prove the word is not native"
    assert o.class_ == "unknown", "but it does NOT prove the source language"
    assert "முதல் எழுத்து" in o.evidence
    assert {a["class"] for a in o.alternatives} == {"வடசொல்", "loanword"}

    # The word that exposed it: Sanskrit, and it must no longer be called a non-Sanskrit loan.
    r = classify_origin("ரூபம்", fst_native_parse=None, in_i2pt=False)
    assert r.class_ != "loanword" and r.is_native is False


def test_bare_vallinam_final_still_asserts_loanword():
    """Deliberately NOT changed with the other two — a different signal, not the same defect.

    Those rules turn on which letters appear, which is source-neutral. This one turns on
    morphological assimilation: Sanskrit borrowings are adapted and take Tamil endings (ரூபம்,
    யோகம், மனிதன்), so they never surface with a bare vallinam final. An unadapted final really is
    evidence of a non-Sanskrit loan.
    """
    o = classify_origin("கேக்", fst_native_parse=None, in_i2pt=False)   # cake
    assert o.class_ == "loanword" and o.is_native is False


def test_forbidden_final_is_loanword():
    o = classify_origin("கேக்", fst_native_parse=None, in_i2pt=False)
    assert o.class_ == "loanword" and "இறுதி எழுத்து" in o.evidence


def test_i2pt_borrowed_without_marker_is_honest_unknown():
    # காபி (coffee): phonotactically native-looking, but attested as borrowed → don't guess the language.
    o = classify_origin("காபி", fst_native_parse=None, in_i2pt=True)
    assert o.class_ == "unknown" and o.is_native is False
    assert {alt["class"] for alt in o.alternatives} == {"வடசொல்", "loanword"}


def test_native_fst_parse_is_iyarcol():
    o = classify_origin("மரம்", fst_native_parse=True, in_i2pt=False)
    assert o.class_ == "இயற்சொல்" and o.is_native is True
    assert 0.0 < o.confidence < 1.0                       # moderate — naturalized borrowings can look native


def test_no_signal_is_unknown_not_a_guess():
    o = classify_origin("மரம்", fst_native_parse=False, in_i2pt=False)
    assert o.class_ == "unknown" and o.confidence == 0.0
    o2 = classify_origin("மரம்", fst_native_parse=None, in_i2pt=False)
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
