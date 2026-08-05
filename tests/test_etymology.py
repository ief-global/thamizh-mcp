"""en.wiktionary etymology adapter + the classifier branch it feeds.

Parser tests are pure (fixture wikitext in, dict out) so they run with no network. Every fixture
below is trimmed from the real page — the shapes that actually broke are the point.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
import pytest

from thamizh_mcp.adapters.base import AdapterResult, NoEntry
from thamizh_mcp.adapters.etymology import (
    EnWiktionaryEtymologyAdapter, is_native_code, language_name, parse_etymology,
)
from thamizh_mcp.core.classifier import classify_origin


# --- parser ---------------------------------------------------------------------------------

def test_borrowed_names_the_source_language():
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{bor+|ta|pt|janela}}. Cognate with x.\n")
    assert ety["relation"] == "borrowed" and ety["is_native"] is False
    assert ety["source_lang"] == "pt" and ety["source_lang_name"] == "Portuguese"
    assert ety["source_word"] == "janela" and ety["certainty"] == "stated"


def test_sanskrit_borrowing():
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{bor|ta|sa|पुस्तक}}.\n")
    assert ety["source_lang"] == "sa" and ety["relation"] == "borrowed"


def test_inherited_is_positive_native_evidence():
    """The signal the classifier never had — proof a word IS native, not merely un-marked."""
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{inh+|ta|dra-pro|*maran}}.\n")
    assert ety["relation"] == "inherited" and ety["is_native"] is True


def test_only_the_tamil_section_is_read():
    """The same page carries other languages' entries; their etymologies say nothing about Tamil."""
    wt = ("==Sanskrit==\n===Etymology===\n{{bor|sa|en|nonsense}}.\n"
          "\n==Tamil==\n===Etymology===\n{{inh|ta|dra-pro|*kac-}}.\n")
    assert parse_etymology(wt)["is_native"] is True


def test_dravidian_subfamily_codes_are_native_by_prefix():
    """மழை is `dra-sdo-pro`. An enumerated list missed it and reported the word as BORROWED from a
    language called 'dra-sdo-pro'."""
    for code in ("dra", "dra-pro", "dra-sdo-pro", "dra-sou-pro", "dra-cen-pro", "ta", "oty"):
        assert is_native_code(code), code
    for code in ("sa", "en", "pt", "ur", "fa", "ar"):
        assert not is_native_code(code), code
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{inh+|ta|dra-sdo-pro|*maẓay}}.\n")
    assert ety["is_native"] is True


def test_homograph_with_conflicting_origins_is_reported_as_ambiguous():
    """கால் is leg (inherited) AND time (Sanskrit); பூ is flower AND earth.

    Ranking by template strength picked `bor` over `inh` every time, so any word with one Sanskrit
    sense came back Sanskrit — four core native words were labelled வடசொல் at 0.8.
    """
    wt = ("==Tamil==\n===Etymology 1===\n{{inh+|ta|dra-pro|*kāl||leg}}.\n"
          "===Etymology 2===\n{{bor|ta|sa|काल}}.\n")
    ety = parse_etymology(wt)
    assert ety["relation"] == "ambiguous" and ety["is_native"] is None
    assert {s["relation"] for s in ety["senses"]} == {"inherited", "borrowed"}


def test_native_word_formation_counts_as_native():
    """சாலை's native sense is {{suffix|ta|சால்|ஐ}} — built from Tamil parts, no language code."""
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{suffix|ta|சால்|ஐ}}.\n")
    assert ety["is_native"] is True and ety["source_lang"] == "ta"

    both = parse_etymology("==Tamil==\n===Etymology 1===\n{{suffix|ta|சால்|ஐ}}.\n"
                           "===Etymology 2===\n{{bor+|ta|sa|शाला}}.\n")
    assert both["relation"] == "ambiguous"


def test_der_is_weaker_than_a_stated_borrowing():
    ety = parse_etymology("==Tamil==\n===Etymology===\n{{der|ta|sa|रूप}}.\n")
    assert ety["certainty"] == "derived"


def test_no_etymology_returns_none():
    assert parse_etymology("==Tamil==\n===Noun===\n{{ta-noun}}\n# a word\n") is None
    assert parse_etymology("==Malayalam==\n{{bor|ml|en|bus}}\n") is None


def test_unknown_language_code_is_reported_not_guessed():
    assert language_name("zzz") == "zzz"


# --- adapter (mocked transport: no network in tests) -----------------------------------------

def _adapter(handler):
    return EnWiktionaryEtymologyAdapter(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _page(wikitext):
    return {"query": {"pages": [{"title": "x", "revisions": [
        {"slots": {"main": {"content": wikitext}}}]}]}}


def test_adapter_returns_etymology_with_citation():
    a = _adapter(lambda r: httpx.Response(200, json=_page(
        "==Tamil==\n===Etymology===\n{{bor+|ta|en|bus}}.\n")))
    res = asyncio.run(a.lookup("பஸ்"))
    assert isinstance(res, AdapterResult)
    assert res.fields["etymology"]["source_lang_name"] == "English"
    assert "en.wiktionary.org" in res.fields["etymology"]["citation"]
    assert res.sources[0].tier == "evolving", "crowd-edited: evidence, not authority"


def test_adapter_missing_page_is_an_honest_gap():
    a = _adapter(lambda r: httpx.Response(200, json={"query": {"pages": [{"missing": True}]}}))
    res = asyncio.run(a.lookup("கணினி"))
    assert isinstance(res, NoEntry) and res.reason == "no_entry"


def test_adapter_network_error_never_raises():
    def boom(request):
        raise httpx.ConnectError("down")
    res = asyncio.run(_adapter(boom).lookup("மரம்"))
    assert isinstance(res, NoEntry) and res.reason == "error"


# --- classifier branch ------------------------------------------------------------------------

def _ety(**kw):
    base = {"relation": "borrowed", "is_native": False, "source_lang": "en",
            "source_lang_name": "English", "source_word": "bus", "template": "bor",
            "certainty": "stated", "citation": "https://en.wiktionary.org/wiki/x#Tamil"}
    return {**base, **kw}


def test_sanskrit_etymology_gives_vadasol():
    o = classify_origin("புத்தகம்", fst_native_parse=None, in_i2pt=False,
                        etymology=_ety(source_lang="sa", source_lang_name="Sanskrit"))
    assert o.class_ == "வடசொல்" and o.borrowed_from == "Sanskrit" and o.is_native is False


def test_non_sanskrit_etymology_gives_loanword_naming_the_source():
    o = classify_origin("ஜன்னல்", fst_native_parse=None, in_i2pt=False,
                        etymology=_ety(source_lang="pt", source_lang_name="Portuguese"))
    assert o.class_ == "loanword" and o.borrowed_from == "Portuguese"


def test_inherited_etymology_gives_iyarchol():
    o = classify_origin("மரம்", fst_native_parse=True, in_i2pt=False,
                        etymology=_ety(relation="inherited", is_native=True,
                                       source_lang="dra-pro", source_lang_name="Proto-Dravidian"))
    assert o.class_ == "இயற்சொல்" and o.is_native is True


def test_ambiguous_etymology_stays_unknown_with_both_senses():
    o = classify_origin("கால்", fst_native_parse=True, in_i2pt=False, etymology={
        "relation": "ambiguous", "is_native": None, "citation": "u",
        "senses": [
            {"relation": "inherited", "source_lang": "dra-pro",
             "source_lang_name": "Proto-Dravidian", "source_word": "*kāl"},
            {"relation": "borrowed", "source_lang": "sa",
             "source_lang_name": "Sanskrit", "source_word": "काल"},
        ]})
    assert o.class_ == "unknown" and o.is_native is None
    assert {a["class"] for a in o.alternatives} == {"இயற்சொல்", "வடசொல்"}
    assert "sense" in o.evidence


def test_derived_scores_lower_than_stated():
    stated = classify_origin("x", fst_native_parse=None, in_i2pt=False, etymology=_ety())
    derived = classify_origin("x", fst_native_parse=None, in_i2pt=False,
                              etymology=_ety(certainty="derived"))
    assert derived.confidence < stated.confidence


def test_etymology_confidence_stays_below_certainty():
    """Evolving tier. Some etymologies are contested (பசு), so the competing class must survive."""
    o = classify_origin("x", fst_native_parse=None, in_i2pt=False, etymology=_ety())
    assert o.confidence <= 0.8 and o.alternatives, "never assert more than a crowd source earns"
    assert any("en.wiktionary.org" in (s.ref or "") for s in o.sources)


def test_no_etymology_falls_back_to_the_offline_rules():
    """Enrichment off, or a miss — the orthographic rules still run, unchanged."""
    o = classify_origin("ஜோதி", fst_native_parse=None, in_i2pt=False, etymology=None)
    assert o.class_ == "unknown" and o.is_native is False   # Grantha: borrowed, source unknown
