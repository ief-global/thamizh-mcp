"""Curated verb-paradigm fallback: Tamil-script joining, generation matching, closed-table honesty,
FST precedence, and the causative இடைநிலை decode. All offline (no foma needed for the rule paths)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.adapters.paradigms import VerbParadigmAdapter, join_surface
from thamizh_mcp.core import decoder
from thamizh_mcp.core.engine import Engine
from thamizh_mcp.schema import MorphAnalysis, SourceRef


# --- Tamil script joining (the bug that made prefix-matching wrong) ---

def test_join_surface_merges_mei_and_uyir():
    assert join_surface("போன்", "ஆன்") == "போனான்"        # not "போன்ஆன்"
    assert join_surface("கொடுத்த்", "ஆன்") == "கொடுத்தான்"
    assert join_surface("கற்ற்", "அது") == "கற்றது"
    assert join_surface("தூங்கின்", "ஏன்") == "தூங்கினேன்"


# --- adapter lookup ---

def test_irregular_past_forms_resolve_with_correct_lemma():
    ad = VerbParadigmAdapter()
    cases = {"கொடுத்தான்": "கொடு", "சொன்னான்": "சொல்", "கற்றான்": "கல்",
             "போனான்": "போ", "விற்றான்": "விற்", "நின்றாள்": "நில்"}
    for word, lemma in cases.items():
        got = ad.analyses_for(word)
        assert got and got[0].lemma == lemma, f"{word} → {got}"
        assert got[0].pos == "verb"
        assert any(t.startswith("past=") for t in got[0].tags)


def test_png_is_decoded_from_the_generated_tags():
    ad = VerbParadigmAdapter()
    a = ad.analyses_for("கொடுத்தேன்")[0]
    tense, png = decoder.decode_verb_grammar(a)
    assert tense == "இறந்தகாலம்" and png == "தன்மை ஒருமை"


# --- present / future paradigms ---

def test_present_forms_resolve():
    ad = VerbParadigmAdapter()
    cases = {"வருகிறான்": "வா", "கொடுக்கிறான்": "கொடு", "கேட்கிறாள்": "கேள்",
             "விற்கிறேன்": "விற்", "தூங்குகிறோம்": "தூங்கு", "கற்கிறான்": "கல்"}
    for word, lemma in cases.items():
        got = ad.analyses_for(word)
        assert got and got[0].lemma == lemma, f"{word} → {got}"
        assert any(t.startswith("pres=") for t in got[0].tags)
        assert decoder.decode_verb_grammar(got[0])[0] == "நிகழ்காலம்"


def test_literary_present_variant_kinru():
    ad = VerbParadigmAdapter()
    got = ad.analyses_for("வருகின்றான்")
    assert got and got[0].lemma == "வா" and any("கின்ற்" in t for t in got[0].tags)


def test_future_forms_resolve():
    ad = VerbParadigmAdapter()
    cases = {"வருவான்": "வா", "கொடுப்பான்": "கொடு", "கேட்பாள்": "கேள்",
             "விற்பேன்": "விற்", "தூங்குவோம்": "தூங்கு", "கற்பான்": "கல்"}
    for word, lemma in cases.items():
        got = ad.analyses_for(word)
        assert got and got[0].lemma == lemma, f"{word} → {got}"
        assert any(t.startswith("fut=") for t in got[0].tags)
        assert decoder.decode_verb_grammar(got[0])[0] == "எதிர்காலம்"


def test_future_neuter_um_is_not_invented():
    """Tamil future neuter is -உம் (வரும்), which ThamizhiMorph tags as NONFINITE futANDadjpart —
    the table must not fabricate a finite 3sgn future (வரு + அது)."""
    ad = VerbParadigmAdapter()
    assert ad.analyses_for("வருவது") == []      # not a finite future form we claim
    for a in ad.analyses_for("வருவான்"):
        assert "3sgn=அது" not in a.tags


def test_tense_marker_matches_fst_convention():
    """Markers mirror ThamizhiMorph's own surface-marker convention (strong doubling included)."""
    ad = VerbParadigmAdapter()
    assert any("pres=க்கிற்" in a.tags for a in ad.analyses_for("கொடுக்கிறான்"))
    assert any("fut=ப்ப்" in a.tags for a in ad.analyses_for("கொடுப்பான்"))
    assert any("fut=வ்" in a.tags for a in ad.analyses_for("வருவான்"))


def test_table_is_closed_no_guessing():
    """An unlisted word must NOT match — the table is deliberately closed (honest gap, not a guess)."""
    ad = VerbParadigmAdapter()
    for w in ["ஸ்கூல்", "மரம்", "ஜிலேபிக்கினான்"]:
        assert ad.analyses_for(w) == []
    assert isinstance(asyncio.run(ad.lookup("மரம்")), NoEntry)


def test_missing_table_is_not_fatal(tmp_path):
    ad = VerbParadigmAdapter(table_path=tmp_path / "nope.json")
    assert ad.analyses_for("கொடுத்தான்") == []
    assert isinstance(asyncio.run(ad.lookup("கொடுத்தான்")), NoEntry)


def test_claims_cite_the_curated_table():
    res = asyncio.run(VerbParadigmAdapter().lookup("போனான்"))
    assert isinstance(res, AdapterResult)
    assert res.tier == "anchor" and "verb_paradigms.json" in res.sources[0].ref


# --- engine wiring: fallback only fills genuine gaps ---

class _FstHit(SourceAdapter):
    name, tier = "ThamizhiMorph", "anchor"
    async def lookup(self, w):
        return AdapterResult(fields={"all_analyses": [MorphAnalysis(lemma="FST", pos="verb", tags=["fin"])]},
                             sources=[SourceRef(name="ThamizhiMorph", tier="anchor")], tier="anchor")


class _FstMiss(SourceAdapter):
    name, tier = "ThamizhiMorph", "anchor"
    async def lookup(self, w):
        return NoEntry(source=self.name, reason="no_entry", note="not in lexicon")


def test_fst_wins_when_it_covers_the_word():
    e = Engine(morph=_FstHit(), morph_fallback=VerbParadigmAdapter())
    a = asyncio.run(e.analyze("கொடுத்தான்", "கொடுத்தான்", include=["root"]))
    assert a.lemma == "FST"                      # fallback must not override the anchor FST


def test_fallback_fills_the_gap_on_fst_miss():
    e = Engine(morph=_FstMiss(), morph_fallback=VerbParadigmAdapter())
    a = asyncio.run(e.analyze("கொடுத்தான்", "கொடுத்தான்", include=["root", "grammar", "formation"]))
    assert a.lemma == "கொடு" and a.grammar.tense == "இறந்தகாலம்"
    assert [c.form for c in a.formation.components] == ["கொடு", "த்", "ஆன்"]


def test_fallback_also_grounds_origin_as_native():
    e = Engine(morph=_FstMiss(), morph_fallback=VerbParadigmAdapter())
    a = asyncio.run(e.analyze("சொன்னான்", "சொன்னான்", include=["origin"]))
    assert a.origin.class_ == "இயற்சொல்" and a.origin.is_native is True


def test_unlisted_word_still_gaps_honestly():
    e = Engine(morph=_FstMiss(), morph_fallback=VerbParadigmAdapter())
    a = asyncio.run(e.analyze("மரம்", "மரம்", include=["root"]))
    assert a.lemma == "" and any(g.field == "lemma" for g in a.gaps)


# --- causative இடைநிலை decode (the FST supplied caus= but the decoder dropped it) ---

def test_causative_marker_is_decoded():
    an = MorphAnalysis(lemma="செய்", pos="verb",
                       tags=["fin", "sim", "caus=வி", "past=த்", "3sgm=ஆன்"])
    f = decoder.decode_formation("செய்வித்தான்", an)
    forms = [(c.part, c.form) for c in f.components]
    assert forms == [("பகுதி", "செய்"), ("இடைநிலை", "வி"), ("இடைநிலை", "த்"), ("விகுதி", "ஆன்")]
    assert any("பிறவினை" in (c.role or "") for c in f.components)
