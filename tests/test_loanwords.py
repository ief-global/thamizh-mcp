"""English-loanword evidence (Dakshina artifact) + the gate that makes it safe.

The gate is the whole point. Ungated, attested-romanization matching fires on 15 of 56 native words
in the 108-word sweep — கால் → "call", கை → "kai", தீ → "thee", கார் → "car". These tests exist to
stop that regressing, so they assert the NEGATIVE cases as hard as the positive ones.
"""
import asyncio
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry
from thamizh_mcp.adapters.loanwords import EnglishLoanwordAdapter, load_loans
from thamizh_mcp.core.classifier import classify_origin
from thamizh_mcp.core.engine import Engine


# --- the shipped artifact -----------------------------------------------------------------------

def test_artifact_is_present_and_sane():
    loans = load_loans()
    assert len(loans) > 500, "artifact looks truncated — rebuild with scripts/build_english_loans.py"
    for ta, en in (("ஸ்கூல்", "school"), ("ஹோட்டல்", "hotel"), ("ஆபீஸ்", "office")):
        assert loans[ta][0] == en


def test_artifact_declares_its_share_alike_licence():
    """Inherited from Dakshina. Losing this marking would relicense CC BY-SA data as Apache-2.0."""
    raw = json.loads(io.open(config.ENGLISH_LOANS_FILE, encoding="utf-8").read())
    meta = raw["_meta"]
    assert "CC BY-SA 4.0" in meta["licence"] and "NOT Apache-2.0" in meta["licence"]
    assert any("Dakshina" in s["name"] for s in meta["sources"])
    assert meta["min_attestations"] >= 2, "single-attestation rows admit phonetic coincidences"


def test_native_words_are_absent_from_the_artifact_by_construction():
    """The build gate excludes anything orthography does not already mark non-native, so a native
    word cannot be looked up even by mistake. கார் is the case that forced this."""
    loans = load_loans()
    for native in ("கார்", "கால்", "கை", "தீ", "கல்", "பால்", "மரம்", "வான்", "பூ", "போ"):
        assert native not in loans, f"{native} must never be lookup-able as an English loan"


def test_sanskrit_words_english_also_borrowed_are_excluded():
    """ராஜா romanizes to "raja", which IS in an English wordlist. Excluding S2PT வடசொல் headwords
    at build time keeps it from being relabelled English."""
    loans = load_loans()
    assert "ராஜா" not in loans


def test_a_single_attestation_phonetic_coincidence_is_excluded():
    """ஆயுட் (Sanskrit āyus) had one annotator romanize it "out". The min-2 threshold drops it."""
    assert "ஆயுட்" not in load_loans()


# --- adapter ------------------------------------------------------------------------------------

def test_adapter_hit_carries_attestation_count_and_citation():
    res = asyncio.run(EnglishLoanwordAdapter().lookup("ஸ்கூல்"))
    assert isinstance(res, AdapterResult)
    loan = res.fields["english_loan"]
    assert loan["english"] == "school" and loan["attestations"] >= 2
    assert res.sources[0].tier == "anchor" and "CC BY-SA" in res.sources[0].ref


def test_adapter_miss_is_an_honest_noentry():
    assert isinstance(asyncio.run(EnglishLoanwordAdapter().lookup("மரம்")), NoEntry)


def test_a_missing_artifact_degrades_to_no_signal_not_an_exception(tmp_path):
    """Losing the artifact must cost one signal, not raise — the orthographic rules still run."""
    ad = EnglishLoanwordAdapter(tmp_path / "absent.json")
    assert ad.loans == {}
    assert isinstance(asyncio.run(ad.lookup("ஸ்கூல்")), NoEntry)


# --- the gate in the classifier ------------------------------------------------------------------

_SCHOOL = {"english": "school", "attestations": 4}
_CAR = {"english": "car", "attestations": 4}


def test_evidence_names_english_where_orthography_proved_non_native():
    o = classify_origin("ஸ்கூல்", fst_native_parse=None, in_s2pt=False, english_loan=_SCHOOL)
    assert o.class_ == "loanword" and o.borrowed_from == "English"
    assert "Grantha" in o.evidence, "must still say WHY it is non-native"
    assert "school" in o.evidence and "4 independent annotators" in o.evidence
    assert any(s.name.startswith("Google Dakshina") for s in o.sources)


def test_the_gate_refuses_to_name_english_for_an_orthographically_native_word():
    """THE critical test. கார் is native Tamil (blackness/monsoon) and romanizes to "car"(4).
    Even handed that evidence explicitly, the classifier must not touch it — Saran's ruling
    2026-08-05 is that கார் leads native."""
    o = classify_origin("கார்", fst_native_parse=True, in_s2pt=False, english_loan=_CAR)
    assert o.class_ == "இயற்சொல்" and o.is_native is True
    assert "English" not in o.evidence

    # and the same for a handful of other natives, with the evidence forced in
    for native in ("கால்", "கை", "தீ", "மரம்", "பூ"):
        o = classify_origin(native, fst_native_parse=True, in_s2pt=False,
                            english_loan={"english": "call", "attestations": 9})
        assert o.class_ != "loanword", f"{native} was mislabelled a loanword"


def test_a_wiktionary_etymology_still_outranks_the_romanization_evidence():
    ety = {"relation": "inherited", "is_native": True, "source_lang": "dra-pro",
           "source_lang_name": "Proto-Dravidian", "source_word": "*kār", "template": "inh",
           "certainty": "stated", "citation": "u"}
    o = classify_origin("கார்", fst_native_parse=True, in_s2pt=False,
                        etymology=ety, english_loan=_CAR)
    assert o.class_ == "இயற்சொல்" and o.is_native is True


# --- engine wiring ------------------------------------------------------------------------------

def test_engine_resolves_a_modern_english_loan_end_to_end():
    e = Engine(loanword_sources=[EnglishLoanwordAdapter()])
    a = asyncio.run(e.analyze("ஸ்கூல்", "ஸ்கூல்", include=["origin"]))
    assert a.origin.class_ == "loanword" and a.origin.borrowed_from == "English"
    assert not any(g.field == "origin" for g in a.gaps), "a resolved origin is not a gap"
    assert any(s.name.startswith("Google Dakshina") for s in a.sources)


def test_engine_without_the_loanword_source_still_works():
    a = asyncio.run(Engine().analyze("ஸ்கூல்", "ஸ்கூல்", include=["origin"]))
    assert a.origin.class_ == "unknown", "no signal → honest unknown, unchanged behaviour"
