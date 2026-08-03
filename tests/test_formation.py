"""Formation decoder (பகுபத உறுப்பு) + verb grammar (tense/முற்று) + explain_* tools.

Decoder rules are pure: MorphAnalysis in → Formation out, so most tests run without foma. One
live test exercises the real FST path.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

import thamizh_mcp.core.engine as eng
from thamizh_mcp import config, server
from thamizh_mcp.adapters.base import AdapterResult, SourceAdapter
from thamizh_mcp.core import decoder
from thamizh_mcp.core.engine import Engine
from thamizh_mcp.schema import MorphAnalysis, SourceRef


def _mk(word, analyses):
    class _Fake(SourceAdapter):
        name, tier = "ThamizhiMorph", "anchor"
        async def lookup(self, w):
            return AdapterResult(fields={"all_analyses": analyses},
                                 sources=[SourceRef(name="ThamizhiMorph", tier="anchor")], tier="anchor")
    return _Fake()


# --- decoder rules (pure, offline) ---

def test_bare_noun_is_pakapadam():
    f = decoder.decode_formation("மரம்", MorphAnalysis(lemma="மரம்", pos="noun", tags=["nom"]))
    assert f.word_type == "பகாப்பதம்"
    assert [c.part for c in f.components] == ["பகுதி"] and f.components[0].form == "மரம்"


def test_inflected_noun_full_decompose():
    f = decoder.decode_formation("மரத்தில்", MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "loc"]))
    assert f.word_type == "பகுபதம்"
    parts = {c.part: c.form for c in f.components}
    assert parts == {"பகுதி": "மரம்", "சாரியை": "அத்து", "விகுதி": "இல்"}
    # மரம் + ஐ > மர + அத்து + ஐ — the ம் DROPS (குன்றல்) and the அத்து சாரியை APPEARS (மிகுதல்).
    # It is NOT ‘ம் becomes த்’: the த் belongs to the சாரியை. Tholkappiyam names both விகாரம்.
    assert {s.type for s in f.sandhi} == {"குன்றல்", "மிகுதல்"}
    assert all(s.authority == "Tholkappiyam" for s in f.sandhi)
    assert all(c.authority == "Nannūl" for c in f.components)   # six-part labels are Nannūl's


def test_plural_noun_sandhi():
    f = decoder.decode_formation("மரங்கள்", MorphAnalysis(lemma="மரம்", pos="noun", tags=["pl", "nom"]))
    assert any(c.part == "விகுதி" and c.form == "கள்" for c in f.components)
    assert any(s.type == "பிறிது ஆதல்" and "ங்" in s.detail for s in f.sandhi)


def test_dative_doubling():
    f = decoder.decode_formation("மரத்துக்கு", MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "dat"]))
    assert any(c.part == "விகுதி" and c.form == "கு" for c in f.components)
    # Tholkappiyam's name for the event (புணரியல் 7), not the description ‘வல்லினம்மிகுதல்’.
    assert any(s.type == "மிகுதல்" and "வல்லினம்" in s.detail for s in f.sandhi)


def test_verb_tense_and_ending():
    an = MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "sim", "strong", "past=த்", "3sgm=ஆன்"])
    f = decoder.decode_formation("வந்தான்", an)
    assert f.word_type == "பகுபதம்"
    parts = {c.part: c.form for c in f.components}
    assert parts == {"பகுதி": "வா", "இடைநிலை": "த்", "விகுதி": "ஆன்"}
    tense, png = decoder.decode_verb_grammar(an)
    assert tense == "இறந்தகாலம்" and png == "படர்க்கை ஆண்பால் ஒருமை"


def test_borrowing_treated_as_pakapadam():
    f = decoder.decode_formation("புத்தகம்", MorphAnalysis(lemma="புத்தகம்", pos="noun", tags=["nom"]))
    assert f.word_type == "பகாப்பதம்"


# --- engine wiring ---

def test_engine_formation_decoded_no_gap():
    e = Engine(morph=_mk("மரத்தில்", [MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "loc"])]))
    a = asyncio.run(e.analyze("மரத்தில்", "மரத்தில்", include=["formation"]))
    assert a.formation.components and not any(g.field == "formation" for g in a.gaps)


def test_engine_grammar_gets_verb_tense():
    an = [MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "past=த்", "3sgm=ஆன்"])]
    a = asyncio.run(Engine(morph=_mk("வந்தான்", an)).analyze("வந்தான்", "வந்தான்", include=["grammar"]))
    assert a.grammar.tense == "இறந்தகாலம்" and a.grammar.person_number_gender == "படர்க்கை ஆண்பால் ஒருமை"


def test_engine_no_fst_is_formation_gap():
    a = asyncio.run(Engine().analyze("மரம்", "மரம்", include=["formation"]))
    assert not a.formation.components and any(g.field == "formation" for g in a.gaps)


# --- tools ---

def test_all_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {"analyze_word", "suggest_native_equivalent", "classify_origin", "get_root",
            "get_meaning", "enrich_word", "explain_formation", "explain_grammar",
            "refresh_sources"} <= names


def test_explain_formation_tool(monkeypatch):
    monkeypatch.setattr(eng, "_default",
                        Engine(morph=_mk("மரத்தில்", [MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "loc"])])))
    out = json.loads(asyncio.run(server.explain_formation(server.ExplainFormationInput(word="மரத்தில்"))))
    assert out["formation"]["word_type"] == "பகுபதம்"
    forms = {c["part"]: c["form"] for c in out["formation"]["components"]}
    assert forms["பகுதி"] == "மரம்" and forms["விகுதி"] == "இல்"


def test_explain_grammar_tool(monkeypatch):
    an = [MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "past=த்", "3sgm=ஆன்"])]
    monkeypatch.setattr(eng, "_default", Engine(morph=_mk("வந்தான்", an)))
    out = json.loads(asyncio.run(server.explain_grammar(server.ExplainGrammarInput(word="வந்தான்"))))
    assert out["grammar"]["word_class"] == "வினை" and out["grammar"]["tense"] == "இறந்தகாலம்"


def test_explain_tools_reject_non_tamil():
    assert asyncio.run(server.explain_formation(server.ExplainFormationInput(word="tree"))).startswith("Error:")
    assert asyncio.run(server.explain_grammar(server.ExplainGrammarInput(word="tree"))).startswith("Error:")


needs_fst = pytest.mark.skipif(not config.flookup_available(),
                               reason="flookup/FSTs not on this machine (see data/PINS.md)")


@needs_fst
def test_live_formation_marathil(monkeypatch):
    from thamizh_mcp.adapters.thamizhimorph import ThamizhiMorphAdapter
    monkeypatch.setattr(eng, "_default", Engine(morph=ThamizhiMorphAdapter()))
    out = json.loads(asyncio.run(server.explain_formation(server.ExplainFormationInput(word="மரத்தில்"))))
    forms = {c["part"]: c["form"] for c in out["formation"]["components"]}
    assert forms.get("பகுதி") == "மரம்" and "விகுதி" in forms


# --- இடைநிலை normalisation (Nannūl உறுப்பு vs FST surface morph) ---

def test_present_idainilai_is_the_grammatical_form_not_the_fst_surface():
    """நிகழ்கால இடைநிலை are கிறு / கின்று / ஆநின்று. The FST reports the surface morph (கிற்),
    which is NOT a valid இடைநிலை — reported by Saran 2026-08-02 from TVA A0212."""
    an = MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "sim", "pres=கிற்", "3sgm=ஆன்"])
    forms = {c.part: c.form for c in decoder.decode_formation("வருகிறான்", an).components}
    assert forms["இடைநிலை"] == "கிறு"          # not "கிற்"
    an2 = MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "pres=கின்ற்", "3sgm=ஆன்"])
    forms2 = {c.part: c.form for c in decoder.decode_formation("வருகின்றான்", an2).components}
    assert forms2["இடைநிலை"] == "கின்று"        # not "கின்ற்"


def test_strong_verb_doubling_is_sandhi_not_part_of_the_idainilai():
    """வல்லினம் மிகுதல் is புணர்ச்சி, so க் is its own சந்தி உறுப்பு — Saran's ruling 2026-08-02."""
    an = MorphAnalysis(lemma="படி", pos="verb", tags=["fin", "strong", "pres=க்கிற்", "3sgm=ஆன்"])
    f = decoder.decode_formation("படிக்கிறான்", an)
    assert [(c.part, c.form) for c in f.components] == [
        ("பகுதி", "படி"), ("சந்தி", "க்"), ("இடைநிலை", "கிறு"), ("விகுதி", "ஆன்")]
    assert any(s.type == "மிகுதல்" and "வல்லினம்" in s.detail for s in f.sandhi)


def test_future_doubling_also_splits():
    an = MorphAnalysis(lemma="படி", pos="verb", tags=["fin", "strong", "fut=ப்ப்", "3sgm=ஆன்"])
    forms = [(c.part, c.form) for c in decoder.decode_formation("படிப்பான்", an).components]
    assert forms == [("பகுதி", "படி"), ("சந்தி", "ப்"), ("இடைநிலை", "ப்"), ("விகுதி", "ஆன்")]


def test_past_and_future_markers_are_already_canonical():
    for tag, want in (("past=த்", "த்"), ("past=ற்", "ற்"), ("fut=வ்", "வ்")):
        an = MorphAnalysis(lemma="வா", pos="verb", tags=["fin", tag, "3sgm=ஆன்"])
        forms = {c.part: c.form for c in decoder.decode_formation("x", an).components}
        assert forms["இடைநிலை"] == want


def test_unmapped_marker_passes_through_never_invented():
    an = MorphAnalysis(lemma="x", pos="verb", tags=["fin", "pres=ZZZ", "3sgm=ஆன்"])
    forms = {c.part: c.form for c in decoder.decode_formation("x", an).components}
    assert forms["இடைநிலை"] == "ZZZ"          # honest pass-through, not a guess


def test_idainilai_role_names_the_classical_class():
    an = MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "pres=கிற்", "3sgm=ஆன்"])
    c = next(c for c in decoder.decode_formation("வருகிறான்", an).components if c.part == "இடைநிலை")
    assert "நிகழ்கால இடைநிலை" in (c.role or "") and c.authority == "Nannūl"


# --- D-014 decoder audit: one regression test per finding (A1–A8) --------------------------------
# Each locks in a case where we previously emitted ThamizhiMorph's computational surface string as
# if it were the grammatical உறுப்பு — the same bug class as கிற்/கிறு. Evidence and நூற்பா for each
# are in the design repo's DECODER-AUDIT-D014.md.

def _parts(word, **kw):
    return [(c.part, c.form) for c in decoder.decode_formation(word, MorphAnalysis(**kw)).components]


def test_a1_euphonic_increment_is_a_sariyai_not_dropped():
    """வந்தனன் = வா + த் + அன்(சாரியை) + அன்(விகுதி). The FST tags the சாரியை `euph`; we used to
    have no handler, so the word silently lost an உறுப்பு. TVA C0212 §5.3.4 / C0214 §4.2.1."""
    got = _parts("வந்தனன்", lemma="வா", pos="verb",
                 tags=["fin", "past=த்", "euph=அன்", "3sgm=அன்"])
    assert got == [("பகுதி", "வா"), ("இடைநிலை", "த்"), ("சாரியை", "அன்"), ("விகுதி", "அன்")]


def test_a2_kal_is_split_off_the_vikuthi_as_modern_accretion():
    """நன்னூல் 337 gives the முன்னிலைப் பன்மை விகுதி as இர்/ஈர் alone; கள் is modern. Saran's
    ruling 2026-08-02: emit it, labelled as modern, rather than folding it into the விகுதி."""
    f = decoder.decode_formation(
        "வந்தீர்கள்", MorphAnalysis(lemma="வா", pos="verb", tags=["fin", "past=த்", "2pl=ஈர்கள்"]))
    assert [(c.part, c.form) for c in f.components] == [
        ("பகுதி", "வா"), ("இடைநிலை", "த்"), ("விகுதி", "ஈர்"), ("விகுதி", "கள்")]
    kal = f.components[-1]
    assert kal.authority is None, "no classical authority sanctions கள்"
    assert "modern" in (kal.role or "")


def test_a3_3pln_surface_is_two_urupukal():
    """நடந்தன = நட + த் + அன்(சாரியை) + அ(விகுதி) — one FST suffix, TWO உறுப்புகள்.
    `3pln` was not mapped at all, so the word previously got no விகுதி. TVA C0214 §4.2.1."""
    got = _parts("நடந்தன", lemma="நட", pos="verb", tags=["fin", "past=த்", "3pln=அன"])
    assert got == [("பகுதி", "நட"), ("இடைநிலை", "த்"), ("சாரியை", "அன்"), ("விகுதி", "அ")]


def test_a4_optative_vikuthi_is_emitted():
    """வாழ்க → வியங்கோள் விகுதி க (நன்னூல் 140). `opt=` was dropped entirely."""
    assert _parts("வாழ்க", lemma="வாழ்", pos="verb", tags=["fin", "opt=க"]) == [
        ("பகுதி", "வாழ்"), ("விகுதி", "க")]


def test_a5_case_urubu_matches_the_surface_across_every_listed_form():
    """A case may carry several உருபு, and a vowel-initial one FUSES into the stem on the surface
    (மரம்+இல் → மரத்தில்), so matching the standalone form alone never succeeded."""
    assert decoder.case_urubu_forms("abl")[:2] == ["இன்", "இல்"]
    assert decoder.case_urubu_forms("inst")[0] == "ஒடு", "Tholkappiyam's form leads (வேற்றுமையியல் 12)"
    loc = {c.part: c.form for c in decoder.decode_formation(
        "மரத்தில்", MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "loc"])).components}
    assert loc["விகுதி"] == "இல்", "surface ...தில் must resolve to the உருபு இல், not the list head"


def test_a6_sollurubu_is_not_presented_as_the_urubu():
    """‘உடைய’ is a சொல்லுருபு and ‘இலிருந்து’ is in neither authority — neither may sit in the
    case NAME, which is where the உருபு goes."""
    for tag in ("gen", "abl", "inst", "loc"):
        name = decoder.map_case([tag]).name
        assert "உடைய" not in name and "இலிருந்து" not in name
    assert decoder.map_case(["gen"]).name == "ஆறாம் வேற்றுமை (அது/ஆது/அ)"


def test_a7_oblique_increment_is_kundral_plus_mikuthal():
    """மரம் + ஐ > மர + அத்து + ஐ. The ம் drops and the சாரியை appears — two விகாரம். The old
    ‘திரிதல் — ம் changes to த்’ was wrong: the த் belongs to அத்து; nothing transforms."""
    f = decoder.decode_formation(
        "மரத்தை", MorphAnalysis(lemma="மரம்", pos="noun", tags=["infInc", "acc"]))
    assert {s.type for s in f.sandhi} == {"குன்றல்", "மிகுதல்"}
    assert any("கெட்டது" in s.detail for s in f.sandhi)


def test_a8_sandhi_type_is_a_classical_vikaram_name():
    """நூற்பா 154 / புணரியல் 7 name exactly three. ‘வல்லினம்மிகுதல்’ describes the event; it is not
    one of them. Saran's ruling: emit Tholkappiyam's name."""
    classical = {"மிகுதல்", "குன்றல்", "பிறிது ஆதல்"}
    for word, kw in (
        ("படிக்கிறான்", dict(lemma="படி", pos="verb", tags=["fin", "strong", "pres=க்கிற்", "3sgm=ஆன்"])),
        ("மரத்துக்கு", dict(lemma="மரம்", pos="noun", tags=["infInc", "dat"])),
        ("மரங்கள்", dict(lemma="மரம்", pos="noun", tags=["pl", "nom"])),
    ):
        f = decoder.decode_formation(word, MorphAnalysis(**kw))
        assert f.sandhi, word
        assert {s.type for s in f.sandhi} <= classical, f"{word}: {[s.type for s in f.sandhi]}"


def test_b1_causative_vi_stays_an_idainilai():
    """Saran's ruling 2026-08-02: வி is an இடைநிலை (Nannūl's positional definition, C0212 §5.3.3),
    NOT a பிறவினை விகுதி despite TVA C0212 §6.1.7 listing it among them. Settled — do not re-open."""
    assert _parts("செய்வித்தான்", lemma="செய்", pos="verb",
                  tags=["fin", "caus=வி", "past=த்", "3sgm=ஆன்"]) == [
        ("பகுதி", "செய்"), ("இடைநிலை", "வி"), ("இடைநிலை", "த்"), ("விகுதி", "ஆன்")]


def test_unmapped_surfaces_still_pass_through_unchanged():
    """The honesty rule survives all of the above: an unrecognised surface is reported as-is,
    never guessed at and never dropped."""
    got = _parts("சொல்லிற்று", lemma="சொல்", pos="verb", tags=["fin", "past=இன்", "3sgn=அது"])
    assert ("விகுதி", "அது") in got, "3sgn=அது is deliberately unmapped — must pass through"
