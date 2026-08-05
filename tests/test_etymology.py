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
from thamizh_mcp.core.classifier import classify_origin, looks_orthographically_native


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


def test_plus_variants_state_the_relation_as_firmly_as_the_bare_form():
    """`der`/`der+` are the ONLY weaker relation — the rest of the `+` forms are not a hedge.

    en.wiktionary's inh+/bor+/lbor+ differ from inh/bor/lbor only in rendering a leading
    "Inherited from" / "Borrowed from"; the claim is identical. inh+ and lbor+ were missing from
    the `stated` list while bor+ was in it, so every {{inh+}} word — மழை and much of the native
    sweep — scored 0.65 while Sanskrit and English {{bor+}} borrowings scored 0.8.
    """
    for tmpl in ("bor", "bor+", "lbor", "lbor+", "inh", "inh+"):
        ety = parse_etymology(f"==Tamil==\n===Etymology===\n{{{{{tmpl}|ta|dra-pro|*maẓay}}}}.\n")
        assert ety["template"] == tmpl
        assert ety["certainty"] == "stated", tmpl
    for tmpl in ("der", "der+"):
        ety = parse_etymology(f"==Tamil==\n===Etymology===\n{{{{{tmpl}|ta|sa|रूप}}}}.\n")
        assert ety["certainty"] == "derived", tmpl


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


def test_homograph_leads_with_the_tamil_sense_and_still_cites_the_borrowing():
    """Saran's ruling, 2026-08-05: where a Tamil sense and a borrowed sense share a form, the
    Tamil sense leads -- this is a Thamizh server -- and the borrowing is cited, never suppressed.

    This replaces the earlier `unknown` answer, which was honest but discarded evidence we held
    and made five everyday words look like coverage gaps.
    """
    o = classify_origin("கால்", fst_native_parse=True, in_i2pt=False, etymology={
        "relation": "ambiguous", "is_native": None, "citation": "u",
        "senses": [
            {"relation": "inherited", "source_lang": "dra-pro", "sense": "leg",
             "source_lang_name": "Proto-Dravidian", "source_word": "*kāl"},
            {"relation": "borrowed", "source_lang": "sa", "sense": "time",
             "source_lang_name": "Sanskrit", "source_word": "काल"},
        ]})
    assert o.class_ == "இயற்சொல்" and o.is_native is True
    assert o.confidence < 0.8, "a reporting ruling on top of evidence, not evidence alone"

    # the borrowing survives in all three places it must
    assert "Sanskrit" in o.evidence and "time" in o.evidence
    assert {a["class"] for a in o.alternatives} == {"வடசொல்"}
    assert [s.sense for s in o.senses] == ["leg", "time"]
    assert [s.class_ for s in o.senses] == ["இயற்சொல்", "வடசொல்"]
    assert o.senses[1].borrowed_from == "Sanskrit" and o.senses[1].source_word == "काल"


def test_homograph_borrowed_in_every_sense_stays_unknown():
    """The ruling only picks a winner when a TAMIL sense exists. Senses that merely disagree about
    which foreign language is the source have no Tamil word to lead with."""
    o = classify_origin("x", fst_native_parse=None, in_i2pt=False, etymology={
        "relation": "ambiguous", "is_native": None, "citation": "u",
        "senses": [
            {"relation": "borrowed", "source_lang": "sa", "sense": "a",
             "source_lang_name": "Sanskrit", "source_word": "क"},
            {"relation": "borrowed", "source_lang": "en", "sense": "b",
             "source_lang_name": "English", "source_word": "b"},
        ]})
    assert o.class_ == "unknown"
    assert [s.class_ for s in o.senses] == ["வடசொல்", "loanword"]


def test_single_origin_word_carries_no_sense_breakdown():
    """senses[] is the homograph affordance -- an ordinary word must not sprout a one-item list."""
    o = classify_origin("ஜன்னல்", fst_native_parse=None, in_i2pt=False, etymology=_ety())
    assert o.senses == []


# --- per-sense parsing (the structural fix) ---------------------------------------------------

_KAL = """==Tamil==

===Pronunciation===
{{ta-IPA}}

===Etymology 1===
{{ety|ta|id=leg|:inh|dra-pro:*kāl<id:leg>}}
{{inh+|ta|dra-pro|*kāl||[[leg]]}}. Cognate with {{cog|kn|ಕಾಲು}}.

====Noun====
# {{lb|ta|anatomy}} [[leg]]

===Etymology 4===
Cognate with {{cog|kn|ಗಾಳಿ}}. Related to {{m|ta|காற்று||wind, air}}.

====Noun====
# [[wind]], [[air]]

===Etymology 5===
{{ety|ta|id=time|:bor|sa:काल<id:time>}}
From {{bor|ta|sa|काल|t=time}}.

====Noun====
# [[time]]
"""


def test_each_etymology_section_is_parsed_as_its_own_sense():
    """The structural defect: templates were ranked across the WHOLE Tamil section, mixing
    unrelated senses into one answer. Each ===Etymology N=== block is one sense."""
    ety = parse_etymology(_KAL)
    assert ety["relation"] == "ambiguous"
    assert [s["sense"] for s in ety["senses"]] == ["leg", "time"]
    assert ety["senses"][0]["source_word"] == "*kāl"
    assert ety["senses"][1]["source_lang"] == "sa"


def test_a_sense_stating_no_etymology_is_omitted():
    """Saran's ruling: kal 'wind' has bare cognates and no relation template, so it is left out
    rather than padded in as an unknown sense."""
    assert all(s["sense"] != "wind, air" for s in parse_etymology(_KAL)["senses"])


def test_tamil_senses_are_ordered_first():
    """Presentation follows the ruling: the reader meets the Tamil word before the borrowing."""
    wt = ("==Tamil==\n===Etymology 1===\n{{bor+|ta|sa|पशु}}.\n\n====Noun====\n# [[cow]]\n"
          "===Etymology 2===\n{{inh+|ta|dra-pro|*pac-}}.\n\n====Noun====\n# [[green]]\n")
    senses = parse_etymology(wt)["senses"]
    assert [s["relation"] for s in senses] == ["inherited", "borrowed"], \
        "pasu lists the Sanskrit sense FIRST on the page -- section order is not a primacy signal"


def test_nested_templates_never_leak_wikitext_into_a_sense_label():
    """Wiktionary nests templates: {{ng|... {{m|ta|x}} ...}}. Stripping in one pass removed the
    INNER template and left `{{ng|the alphasyllabic combination of` in a user-facing field."""
    wt = ("==Tamil==\n===Etymology===\n{{inh+|ta|dra-pro|*x}}.\n\n====Noun====\n"
          "# {{ng|the alphasyllabic combination of {{m|ta|\u0bb5\u0bcd}} and {{m|ta|\u0b86}}}}\n"
          "# [[a real gloss]]\n")
    label = parse_etymology(wt)["sense"]
    assert label is None or "{{" not in label, f"raw wikitext leaked: {label!r}"


def test_sense_label_falls_back_from_id_to_template_gloss_to_definition():
    by_id = parse_etymology("==Tamil==\n===Etymology 1===\n{{ety|ta|id=leg|:inh|x}}\n"
                            "{{inh+|ta|dra-pro|*kāl}}.\n")
    assert by_id["sense"] == "leg"

    by_gloss = parse_etymology("==Tamil==\n===Etymology===\n{{inh+|ta|dra-pro|*kār||black}}.\n")
    assert by_gloss["sense"] == "black"

    by_def = parse_etymology("==Tamil==\n===Etymology===\n{{suffix|ta|சால்|ஐ}}.\n"
                             "\n====Noun====\n# [[road]], [[path]]\n")
    assert by_def["sense"] == "road, path"

    by_t_param = parse_etymology("==Tamil==\n===Etymology===\n{{bor|ta|sa|काल|t=time}}.\n")
    assert by_t_param["sense"] == "time"


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


# --- Saran's ruling applies to ANY source language, not just Sanskrit -------------------------

def _homograph(borrowed_lang, borrowed_name, borrowed_word, synonyms=()):
    return {"relation": "ambiguous", "is_native": None, "citation": "u",
            "senses": [
                {"relation": "inherited", "source_lang": "dra-pro", "sense": "native sense",
                 "source_lang_name": "Proto-Dravidian", "source_word": "*x", "synonyms": []},
                {"relation": "borrowed", "source_lang": borrowed_lang, "sense": "borrowed sense",
                 "source_lang_name": borrowed_name, "source_word": borrowed_word,
                 "synonyms": list(synonyms)},
            ]}


def test_the_tamil_sense_leads_whatever_the_other_language_is():
    """Saran clarified 2026-08-05: the rule is NOT Sanskrit-only. Tamil leads over English, Urdu,
    Marathi, Telugu — any source. கார் (native blackness vs English car) is the case that forced
    the question; it must behave exactly like பூ (native flower vs Sanskrit earth)."""
    for code, name, word in [("sa", "Sanskrit", "भू"), ("en", "English", "car"),
                             ("ur", "Urdu", "x"), ("mr", "Marathi", "y"), ("te", "Telugu", "z")]:
        o = classify_origin("x", fst_native_parse=True, in_i2pt=False,
                            etymology=_homograph(code, name, word))
        assert o.class_ == "இயற்சொல்" and o.is_native is True, name
        assert name in o.evidence, f"{name} sense must still be disclosed"
        assert o.senses[1].borrowed_from == name


# --- pure-Tamil alternative for the BORROWED sense --------------------------------------------

def test_borrowed_sense_hands_back_the_pure_tamil_word():
    """The point of the ruling: a reader who meant English 'car' still learns மகிழுந்து."""
    o = classify_origin("கார்", fst_native_parse=True, in_i2pt=False, etymology=_homograph(
        "en", "English", "car", ["மகிழுந்து", "சீருந்து", "தானுந்து"]))
    borrowed = o.senses[1]
    assert [c.equivalent for c in borrowed.tamil_alternatives] == ["மகிழுந்து", "சீருந்து", "தானுந்து"]
    assert all(c.attestation == "attested" and c.citation for c in borrowed.tamil_alternatives)
    assert o.senses[0].tamil_alternatives == [], "a native sense already IS the Tamil word"


def test_a_synonym_that_is_itself_borrowed_is_never_offered_as_pure_tamil():
    """சாலை's road sense lists ரோடு — English. Offering it as a pure-Tamil equivalent would be
    worse than offering nothing, so the orthographic rules filter the synonym list."""
    o = classify_origin("சாலை", fst_native_parse=True, in_i2pt=False, etymology=_homograph(
        "sa", "Sanskrit", "शाला", ["ரோடு", "வழி", "பாதை"]))
    got = [c.equivalent for c in o.senses[1].tamil_alternatives]
    assert "ரோடு" not in got and got == ["வழி", "பாதை"]


def test_orthographic_native_filter():
    """Proves NON-nativeness only — that is all it is used for."""
    for w in ("மகிழுந்து", "சீருந்து", "தானுந்து", "வழி", "பாதை", "வீடு", "மனை"):
        assert looks_orthographically_native(w), w
    for w in ("ரோடு", "ஜன்னல்", "பஸ்", "Thesaurus", "", "car"):
        assert not looks_orthographically_native(w), w


def test_synonyms_are_collected_per_sense_block():
    """The synonym list must follow the SENSE, not the page: கார்'s car synonyms belong to the
    English block, not to the native blackness block."""
    wt = ("==Tamil==\n"
          "===Etymology 1===\n{{inh+|ta|dra-pro|*kār||black}}.\n\n====Noun====\n"
          "# [[blackness]]\n#: {{syn|ta|கருமை}}\n"
          "===Etymology 2===\n{{bor+|ta|en|car}}.\n\n====Noun====\n"
          "# [[car]]\n#: {{syn|ta|மகிழுந்து|சீருந்து}} {{a|ta|all|_|Formal}}\n")
    senses = parse_etymology(wt)["senses"]
    assert senses[0]["synonyms"] == ["கருமை"]
    assert senses[1]["synonyms"] == ["மகிழுந்து", "சீருந்து"]
