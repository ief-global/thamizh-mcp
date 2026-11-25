"""Round-trip validity (D-023): a split is valid only if joining its parts back, under the SAME
rule tables, rebuilds the word. Split and join follow one rule set (data/grammar/punarchi.json).

These run offline: the analyses below are the shapes ThamizhiMorph and the curated paradigms
return for these words (probed live 2026-11-25), so the guard does not depend on foma.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, SourceAdapter
from thamizh_mcp.core import classical, decoder, punarchi
from thamizh_mcp.core.engine import Engine
from thamizh_mcp.schema import MorphAnalysis, SourceRef

V = ["fin", "sim"]

# word → the analysis the FST (or the curated paradigm) gives for it
SWEEP = {
    "வந்தான்": ("வா", "verb", V + ["strong", "past=த்", "3sgm=ஆன்"]),
    "வருகிறான்": ("வா", "verb", V + ["pres=கிற்", "3sgm=ஆன்"]),
    "வருவான்": ("வா", "verb", V + ["fut=வ்", "3sgm=ஆன்"]),
    "வந்தனன்": ("வா", "verb", V + ["strong", "past=த்", "euph=அன்", "3sgm=அன்"]),
    "வந்தார்கள்": ("வா", "verb", V + ["strong", "past=த்", "3ple=ஆர்கள்"]),
    "வந்தீர்கள்": ("வா", "verb", V + ["strong", "past=த்", "2pl=ஈர்கள்"]),
    "படித்தான்": ("படி", "verb", V + ["strong", "past=த்", "3sgm=ஆன்"]),
    "படிக்கிறான்": ("படி", "verb", V + ["strong", "pres=க்கிற்", "3sgm=ஆன்"]),
    "படிப்பான்": ("படி", "verb", V + ["strong", "fut=ப்ப்", "3sgm=ஆன்"]),
    "நடந்தன": ("நட", "verb", V + ["strong", "past=த்", "3pln=அன"]),
    "வாழ்க": ("வாழ்", "verb", V + ["opt=க"]),
    "செய்வித்தான்": ("செய்", "verb", V + ["caus=வி", "past=த்", "3sgm=ஆன்"]),
    "மரத்தில்": ("மரம்", "noun", ["infInc", "loc"]),
    "மரத்தை": ("மரம்", "noun", ["infInc", "acc"]),
    "மரங்கள்": ("மரம்", "noun", ["pl", "nom"]),
    "மரத்துக்கு": ("மரம்", "noun", ["infInc", "dat"]),
    "வீட்டில்": ("வீடு", "noun", ["loc"]),
    "வீட்டுக்கு": ("வீடு", "noun", ["dat"]),
    "கையால்": ("கை", "noun", ["inst"]),
    "பள்ளியில்": ("பள்ளி", "noun", ["loc"]),
    "கொடுத்தான்": ("கொடு", "verb", V + ["past=த்", "3sgm=ஆன்"]),
    "கொடுக்கிறான்": ("கொடு", "verb", V + ["pres=க்கிற்", "3sgm=ஆன்"]),
    "கொடுப்பான்": ("கொடு", "verb", V + ["fut=ப்ப்", "3sgm=ஆன்"]),
    "போனான்": ("போ", "verb", V + ["past=ன்", "3sgm=ஆன்"]),
    "சொன்னான்": ("சொல்", "verb", V + ["past=ன்", "3sgm=ஆன்"]),
    "தூங்கினான்": ("தூங்கு", "verb", V + ["past=இன்", "3sgm=ஆன்"]),
    "எழுதினான்": ("எழுது", "verb", V + ["strong", "past=இன்", "3sgm=ஆன்"]),
    "ஓடினான்": ("ஓடு", "verb", V + ["strong", "past=இன்", "3sgm=ஆன்"]),
    "பார்த்தான்": ("பார்", "verb", V + ["strong", "past=த்", "3sgm=ஆன்"]),
    "காத்திருந்தாள்": ("காத்திரு", "verb", ["fin", "complex", "aspect", "strong", "past=த்", "3sgf=ஆள்"]),
    "கேட்டான்": ("கேள்", "verb", V + ["strong", "past=ட்", "3sgm=ஆன்"]),
    "உண்டான்": ("உண்", "verb", V + ["strong", "past=ட்", "3sgm=ஆன்"]),
    "கண்டான்": ("காண்", "verb", V + ["past=ட்", "3sgm=ஆன்"]),
    # D-030: verbs whose பகுதி changes, decoded by the catalogue, not by a list of verbs
    "கொன்றான்": ("கொல்", "verb", V + ["past=ற்", "3sgm=ஆன்"]),
    "சென்றான்": ("செல்", "verb", V + ["past=ற்", "3sgm=ஆன்"]),
    "நீண்டது": ("நீள்", "verb", V + ["past=ட்", "3sgn=அது"]),
    "நின்றான்": ("நில்", "verb", V + ["past=ற்", "3sgm=ஆன்"]),
    "கற்றான்": ("கல்", "verb", V + ["past=ற்", "3sgm=ஆன்"]),
    "தந்தான்": ("தா", "verb", V + ["past=த்", "3sgm=ஆன்"]),
    "செத்தான்": ("சா", "verb", V + ["past=த்", "3sgm=ஆன்"]),
    "சேர்ந்தான்": ("சேர்", "verb", V + ["past=த்", "3sgm=ஆன்"]),
    "வாழ்ந்தான்": ("வாழ்", "verb", V + ["past=த்", "3sgm=ஆன்"]),
    "தேய்ந்தான்": ("தேய்", "verb", V + ["past=த்", "3sgm=ஆன்"]),
}


def _decode(word):
    lemma, pos, tags = SWEEP[word]
    return decoder.decode_formation(word, MorphAnalysis(lemma=lemma, pos=pos, tags=tags))


# --- புணரியல் 36 / 37: letters and phonemes are one bijection --------------------------------

def test_split_and_join_of_letters_is_lossless_over_every_pinned_verse():
    """புணரியல் 37 (split) then 36 (join) must give back exactly the text, for every verse of
    Tholkappiyam. If this ever fails, nothing built on the phoneme layer can be trusted."""
    t = json.loads((config.REPO_ROOT / "data" / "classical" / "tholkappiyam.json").read_text("utf-8"))
    n = 0
    for iyals in t["athikaram"].values():
        for verses in iyals.values():
            for v in verses.values():
                assert punarchi.render(punarchi.phonemes(v)) == v
                n += 1
    assert n > 1500


def test_phonemes_split_uyirmei_into_mei_and_uyir():
    assert punarchi.phonemes("வந்தான்") == ["வ்", "அ", "ந்", "த்", "ஆ", "ன்"]
    assert punarchi.render(["க்", "இ", "ற்"]) == "கிற்"


# --- the guard: every decoded formation rebuilds its own word ---------------------------------

@pytest.mark.parametrize("word", sorted(SWEEP))
def test_decoded_formation_rebuilds_its_word(word):
    f = _decode(word)
    assert f.round_trip is not None
    assert f.round_trip.holds, f"{word}: {f.round_trip.note}"
    assert f.round_trip.rebuilt == word


@pytest.mark.parametrize("word", sorted(w for w, a in SWEEP.items() if a[1] == "verb"))
def test_verb_components_spell_the_word(word):
    """For a verb every join that adds letters is a COMPONENT, so the component surfaces, joined,
    spell the word. Nothing the word has may be missing from the split."""
    f = _decode(word)
    spelled = punarchi.render([p for c in f.components for p in punarchi.phonemes(c.surface or c.form)])
    assert spelled == word


def test_defect_1_the_missing_na_is_named():
    """KNOWN DECODER DEFECT 1: காத்திருந்தாள் decoded as காத்திரு + த் + ஆள், the ந் gone.
    Since D-031 the ந் is the சந்தி: பாவாணர், 'வந்தான், இருந்தான் முதலிய சொற்களில், ந் என்பதே சந்தி'
    (இயற்றமிழ் இலக்கணம் §57, p. 66). D-028 had it an இடைநிலை எழுத்து after நச்சினார்க்கினியர்."""
    f = _decode("காத்திருந்தாள்")
    assert [(c.part, c.form, c.surface) for c in f.components] == [
        ("பகுதி", "காத்திரு", None), ("சந்தி", "ந்", None), ("இடைநிலை", "த்", None),
        ("விகுதி", "ஆள்", None)]


def test_a_split_that_does_not_rebuild_says_so_and_names_the_missing_letters():
    f = decoder.decode_formation("செய்தான்", MorphAnalysis(lemma="செய்", pos="noun", tags=["foc"]))
    assert not f.round_trip.holds
    assert f.round_trip.rebuilt == "செய்"
    assert f.round_trip.unaccounted == "தான்"


def _engine(analyses):
    class _Fake(SourceAdapter):
        name, tier = "ThamizhiMorph", "anchor"

        async def lookup(self, w):
            return AdapterResult(fields={"all_analyses": analyses},
                                 sources=[SourceRef(name="ThamizhiMorph", tier="anchor")], tier="anchor")
    return Engine(morph=_Fake())


def test_engine_prefers_the_analysis_that_rebuilds_the_word():
    """The FST lists செய்தான் as the noun செய் + a focus tag FIRST; that split cannot account for
    -தான். The verb analysis can, so it is the one decoded, and no formation gap is raised."""
    noun = MorphAnalysis(lemma="செய்", pos="noun", tags=["foc"])
    verb = MorphAnalysis(lemma="செய்", pos="verb", tags=V + ["strong", "past=த்", "3sgm=ஆன்"])
    a = asyncio.run(_engine([noun, verb]).analyze("செய்தான்", "செய்தான்", include=["formation"]))
    assert a.formation.round_trip.holds
    assert [c.form for c in a.formation.components] == ["செய்", "த்", "ஆன்"]
    assert not any("rebuild" in g.note for g in a.gaps)


def test_engine_declares_a_gap_when_no_analysis_rebuilds():
    noun = MorphAnalysis(lemma="செய்", pos="noun", tags=["foc"])
    a = asyncio.run(_engine([noun]).analyze("செய்தான்", "செய்தான்", include=["formation"]))
    gap = [g for g in a.gaps if g.field == "formation"]
    assert gap and "does not rebuild" in gap[0].note and "தான்" in gap[0].note


# --- the rule table and the code agree, and every citation is real -----------------------------

def _all_rules():
    """The joins and the பகுதி விகாரம் catalogue (D-030): one standard of citation for both."""
    return punarchi.table()["join_rules"] + punarchi.vikaram_rules()


def test_every_rule_in_the_table_is_implemented_and_vice_versa():
    table_ids = {r["id"] for r in punarchi.table()["join_rules"]} - {"uyirmei"}
    boundary = {r["id"] for r in punarchi.vikaram_rules() if r["applies"] == "boundary"}
    stem = {r["id"] for r in punarchi.vikaram_rules() if r["applies"] == "stem"}
    assert table_ids | boundary == set(punarchi._ORDER)
    assert stem == set(punarchi.STEM_RULES)


def test_every_rule_declares_a_known_status_and_classical_rules_cite_a_verse():
    statuses = set(punarchi.table()["status_values"])
    for r in _all_rules():
        assert r["status"] in statuses, r["id"]
        if r["status"] == "classical":
            assert r["cites"], f"{r['id']} is classical but cites nothing"
        if r["status"] == "textbook":
            assert r["textbook"]["quote"] and r["textbook"]["source"].startswith("TVA")
        if r["status"] == "urai":
            # Only a passage read against its scan page may back a rule (D-027, D-028).
            assert r["urai"] and r["urai_scope"], r["id"]
            assert set(r["urai"]) <= set(classical.verified_quotations()), r["id"]
            assert "textbook" not in r, f"{r['id']}: a commentary outranks the course book (D-028)"
        if r["status"] == "scholar":
            # பாவாணர் (D-031): a passage of his read on the scan page, with its reach stated.
            assert r["urai_scope"] and any(q.startswith("pavanar-") for q in r["urai"]), r["id"]
            assert set(r["urai"]) <= set(classical.verified_quotations()), r["id"]
        if r["status"] == "parked":
            assert "D-023" in r["parked"]


def test_every_cited_verse_resolves_and_is_quoted_from_the_pinned_edition():
    for r in _all_rules():
        for c in r["cites"]:
            if c["authority"] == "Tholkappiyam":
                text = classical.tholkappiyam_verse(c["athikaram"], c["iyal"], c["verse"])
            else:
                text = classical.nannul_verse(c["verse"])
            assert text, f"{r['id']}: {c} does not resolve in data/classical/"
        for ref in punarchi.cite(r["id"]):
            assert ref.verse_text, f"{r['id']}: {ref.verse} carries no quoted text"


def test_tholkappiyam_is_cited_first_wherever_it_is_cited():
    for r in _all_rules():
        auths = [c["authority"] for c in r["cites"]]
        if "Tholkappiyam" in auths:
            assert auths[0] == "Tholkappiyam", r["id"]
        elif r["status"] == "classical":
            assert r.get("tholkappiyam_searched"), (
                f"{r['id']} cites only Nannūl, so it must record that Tholkappiyam was searched")


def test_a_parked_rule_never_carries_a_label():
    for r in _all_rules():
        if r["status"] == "parked":
            assert not r.get("part"), f"{r['id']} is parked, so it must not name an உறுப்பு"


def test_the_letter_after_the_pakuthi_is_a_santhi_on_pavanar():
    """D-031 (Saran, 2026-11-25): பாவாணர் breaks ties. He names the letter that appears where the
    பகுதி meets the next part a சந்தி (படித்தான், வந்தான்; இயற்றமிழ் இலக்கணம் §57, p. 66), which
    supersedes D-028's இடைநிலை எழுத்து. He limits சந்தி to that join, so a doubled letter after
    another part (செய்வித்தான்'s த்த் after வி) keeps D-028's label."""
    for rid in ("santhi_otru", "santhi_na"):
        rule = punarchi.rules()[rid]
        assert rule["status"] == "scholar" and rule["part"] == "சந்தி", rid
        assert "D-031" in rule["superseded"]["by"] and "இடைநிலை" in rule["superseded"]["label"], rid
        assert rule["cites"][0]["authority"] == "Tholkappiyam", rid
        assert rule["urai"][0].startswith("pavanar-"), rid
    for word in ("படித்தான்", "படிக்கிறான்", "படிப்பான்", "பார்த்தான்", "கொடுத்தான்", "வந்தான்",
                 "காத்திருந்தாள்", "சேர்ந்தான்"):
        parts = [c.part for c in _decode(word).components]
        assert parts[:2] == ["பகுதி", "சந்தி"] and None not in parts, word
    f = _decode("செய்வித்தான்")
    assert [c.part for c in f.components] == ["பகுதி", "இடைநிலை", "இடைநிலை", "இடைநிலை", "விகுதி"]
    assert [s.rule for s in f.round_trip.steps] == ["irattitha_otru"]


def test_a_pavanar_step_quotes_the_page_it_was_read_on():
    for rid in ("santhi_otru", "santhi_na", "in_muthal_kurai"):
        refs = punarchi.cite(rid)
        pav = [r for r in refs if "பாவாணர்" in (r.name or "")]
        assert pav and all(r.verse_text and "p. " in r.ref for r in pav), rid
    assert punarchi.cite("santhi_na")[0].name == "Tholkappiyam", "the நூற்பா is cited first"


# --- fixtures from நச்சினார்க்கினியர்'s உரை: the commentary's own worked examples -------------

def _urai_examples(iyal, verse):
    u = classical.tholkappiyam_urai("எழுத்ததிகாரம்", iyal, verse)
    return " ".join(u["examples"]) if u else ""


@pytest.mark.parametrize("iyal,verse,word,parts,kinds", [
    # உருபியல் 13: the commentator gives மரத்தை மரத்தொடு and says they are finished by புணரியல்
    # 31 (அத்தே வற்றே — the ம் drops) and 23 (அத்தின் அகரம் — அத்து's அ drops).
    ("உருபியல்", 13, "மரத்தை", ("மரம்", "அத்து", "ஐ"), ["stem", "sariyai", "case"]),
    ("உருபியல்", 13, "மரத்தொடு", ("மரம்", "அத்து", "ஒடு"), ["stem", "sariyai", "case"]),
    ("உருபியல்", 13, "நுகத்தை", ("நுகம்", "அத்து", "ஐ"), ["stem", "sariyai", "case"]),
    # புணரியல் 12: a case ending that begins with a hard consonant doubles it.
    ("புணரியல்", 12, "மணிக்கு", ("மணி", "கு"), ["stem", "case"]),
    ("புணரியல்", 12, "தீக்கு", ("தீ", "கு"), ["stem", "case"]),
    ("புணரியல்", 12, "ஊர்க்கு", ("ஊர்", "கு"), ["stem", "case"]),
    # புணரியல் 38: the உடம்படுமெய் between two vowels.
    ("புணரியல்", 38, "கிளியழகிது", ("கிளி", "அழகிது"), ["stem", "word"]),
    ("புணரியல்", 38, "விளவழகிது", ("விள", "அழகிது"), ["stem", "word"]),
    ("புணரியல்", 38, "பலாவழகிது", ("பலா", "அழகிது"), ["stem", "word"]),
])
def test_the_commentarys_worked_examples_rebuild(iyal, verse, word, parts, kinds):
    assert word in _urai_examples(iyal, verse), f"{word} is not in the உரை on {iyal} {verse}"
    assert word in punarchi.joins_all(*parts, kinds=kinds)


# --- the பகுதி விகாரம் catalogue (D-029, D-030): rules, not a list of verbs ----------------------

def _verb(word, lemma, tense, png="3sgm=ஆன்"):
    return decoder.decode_formation(word, MorphAnalysis(lemma=lemma, pos="verb",
                                                        tags=["fin", tense, png]))


_VIKARAM = {
    # word: (lemma, tense tag, the பகுதி as it surfaces, the rule that changes it)
    "நின்றான்": ("நில்", "past=ற்", "நின்", "eetrumei_inam_thirithal"),
    "கொண்டான்": ("கொள்", "past=ட்", "கொண்", "eetrumei_inam_thirithal"),
    "கொன்றான்": ("கொல்", "past=ற்", "கொன்", "eetrumei_inam_thirithal"),
    "சென்றான்": ("செல்", "past=ற்", "சென்", "eetrumei_inam_thirithal"),
    "வென்றான்": ("வெல்", "past=ற்", "வென்", "eetrumei_inam_thirithal"),
    "போன்றான்": ("போல்", "past=ற்", "போன்", "eetrumei_inam_thirithal"),
    "கற்றான்": ("கல்", "past=ற்", "கற்", "eetrumei_varumei_thirithal"),
    "கேட்டான்": ("கேள்", "past=ட்", "கேட்", "eetrumei_varumei_thirithal"),
    "விற்றான்": ("வில்", "past=ற்", "விற்", "eetrumei_varumei_thirithal"),
    "நிற்பான்": ("நில்", "fut=ப்", "நிற்", "eetrumei_varumei_thirithal"),
    "கற்பான்": ("கல்", "fut=ப்", "கற்", "eetrumei_varumei_thirithal"),
    "சொன்னான்": ("சொல்", "past=ன்", "சொன்", "eetrumei_varumei_thirithal"),
    "கண்டான்": ("காண்", "past=ட்", "கண்", "muthanilai_kurukkal"),
    "வந்தான்": ("வா", "past=த்", "வ", "muthanilai_kurukkal"),
    "தந்தான்": ("தா", "past=த்", "த", "muthanilai_kurukkal"),
    "செத்தான்": ("சா", "past=த்", "செ", "muthal_aa_ekaram"),
    "வருவான்": ("வா", "fut=வ்", "வரு", "kurukki_uyirmei_virithal"),
    "விராவினான்": ("விரவு", "past=இன்", "விராவ்", "naduk_kuril_neettal"),
    "கொணர்ந்தான்": ("கொணா", "past=த்", "கொணர்", "ayal_kurukki_ra_virithal"),
}


@pytest.mark.parametrize("word", _VIKARAM)
def test_the_change_in_the_pakuthi_comes_from_one_cited_rule(word):
    """Every verb here is decoded by the same catalogue; none is listed by name. Each change is one
    cited rule: the Tholkappiyam commentator first where one states it, else the Nannūl
    commentator (Saran, D-030), each quoted from the page it was read on."""
    lemma, tag, stem, rule = _VIKARAM[word]
    f = _verb(word, lemma, tag)
    assert f.round_trip.holds, word
    assert f.components[0].form == lemma and f.components[0].surface == stem, word
    changes = [s for s in f.round_trip.steps if s.rule in {r["id"] for r in punarchi.vikaram_rules()}]
    assert [s.rule for s in changes] == [rule], word
    [step] = changes
    assert step.status == "urai"
    assert step.sources[0].authority == "Tholkappiyam", f"{word}: Tholkappiyam leads"
    assert any("உரை" in (r.verse or "") and r.verse_text and "p. " in (r.ref or "")
               for r in step.sources), f"{word}: a commentary quoted from its page"


def test_the_table_lists_kinds_of_change_never_verbs():
    """D-030 replaced D-029's per-verb list. A rule names a change, not a root: no entry may carry
    a lemma, and the old list is gone."""
    t = punarchi.table()
    assert "stem_alternants" not in t
    for r in punarchi.vikaram_rules():
        assert "lemma" not in r and r["applies"] in ("stem", "boundary"), r["id"]
        assert r["kind"] and r["examples"], r["id"]


@pytest.mark.parametrize("rule", [r["id"] for r in json.loads(
    config.GRAMMAR_PUNARCHI_FILE.read_text("utf-8"))["pakuthi_vikaram"]["rules"]])
def test_every_example_a_rule_gives_is_rebuilt_by_that_rule(rule):
    """The commentators' own examples are the fixtures: each one decodes with its rule."""
    r = punarchi.rules()[rule]
    for word in r["examples"]:
        if word in _VIKARAM:
            assert _VIKARAM[word][3] == rule, word


def test_roots_of_one_shape_change_differently_and_the_word_decides():
    """விசாகப் பெருமாளையர் (நன்னூல் 137, p. 114): 'ஒரு நிகராகிய பகுதிகள் பலவிதமாக விகாரப்படுதலால்'
    — கல், நில், சொல் are alike but give கற்றான், நின்றான், சொன்னான். So the root's shape cannot pick
    the change. Joining கல் + ற் + ஆன் may give either; analysing a word picks the one that rebuilds
    IT, and only that one."""
    built = punarchi.joins_all("நில்", "ற்", "ஆன்", kinds=["stem", "idainilai", "vikuthi"], verb=True)
    assert {"நின்றான்", "நிற்றான்"} <= built
    assert _verb("நின்றான்", "நில்", "past=ற்").components[0].surface == "நின்"
    assert _verb("கற்றான்", "கல்", "past=ற்").components[0].surface == "கற்"


def test_sol_follows_nil_and_its_tense_letter_is_cited():
    """Saran, 2026-11-25 (D-030): சொல் → சொன் follows the same pattern as நில் → நின். The change is
    Tholkappiyam's ல் before a nasal (புள்ளிமயங்கியல் 71, 72). The ன் after it is the இடைநிலை இன் with
    its first letter dropped (பாவாணர் §104; D-031). Nothing about சொன்னான் is parked."""
    f = _verb("சொன்னான்", "சொல்", "past=ன்")
    assert [(c.part, c.form, c.surface) for c in f.components] == [
        ("பகுதி", "சொல்", "சொன்"), ("இடைநிலை", "இன்", "ன்"), ("விகுதி", "ஆன்", None)]
    assert not any(s.status == "parked" for s in f.round_trip.steps)
    assert [s.rule for s in f.round_trip.steps] == ["in_muthal_kurai", "eetrumei_varumei_thirithal"]
    na = json.loads(config.GRAMMAR_IDAINILAI_FILE.read_text("utf-8"))["idainilai"]["past"]["from_fst"]["ன்"]
    assert na["urai"] == ["pavanar-104-in"] and "§104" in f.components[1].role


def test_ponan_is_po_plus_in_with_its_first_letter_dropped():
    """பாவாணர் §104 (p. 32): 'இன் என்னும் இடைநிலை ன் என முதல் குறைந்தும் … நிற்கும். உ-ம். போனான்
    – போ + ன் + ஆன்'. It breaks the tie with D-030's reading (another இடைநிலை under நன்னூல் 144)."""
    f = _verb("போனான்", "போ", "past=ன்")
    assert [(c.part, c.form, c.surface) for c in f.components] == [
        ("பகுதி", "போ", None), ("இடைநிலை", "இன்", "ன்"), ("விகுதி", "ஆன்", None)]
    [step] = f.round_trip.steps
    assert step.rule == "in_muthal_kurai" and step.status == "scholar"


def test_na_comes_after_ya_ra_zha_as_the_commentators_examples_show():
    """Before D-030 the ந் rule fired after a vowel only, and சேர்ந்தான், வாழ்ந்தான், தேய்ந்தான்
    failed to rebuild. The Nannūl commentators' lists of past forms give the ந் there too."""
    for word, lemma in (("சேர்ந்தான்", "சேர்"), ("வாழ்ந்தான்", "வாழ்"), ("தேய்ந்தான்", "தேய்")):
        f = _verb(word, lemma, "past=த்")
        assert f.round_trip.holds, word
        assert [c.form for c in f.components] == [lemma, "ந்", "த்", "ஆன்"], word


def test_a_catalogued_change_the_engine_does_not_apply_says_why():
    t = punarchi.table()["pakuthi_vikaram"]
    applied = {r["id"] for r in t["rules"]}
    for r in t["catalogued_not_applied"]:
        assert r["why_not_applied"] and r["id"] not in applied
        assert set(r["urai"]) <= set(classical.verified_quotations()), r["id"]


def test_a_letter_is_counted_as_written():
    """An உயிர்மெய் is ONE letter. Before 2026-11-25 the count was by code point, so வா was two
    letters and the one-letter-root rule could never fire."""
    assert punarchi._letters(punarchi.phonemes("வா")) == 1
    assert punarchi._letters(punarchi.phonemes("வீடு")) == 2
    assert punarchi._letters(punarchi.phonemes("காத்திரு")) == 4


def test_a_step_cites_the_verses_for_its_own_letter_only():
    """eetrumei_varumei_thirithal covers ல் and ள், before a hard consonant and before a nasal. A step
    cites only the நூற்பா for the join it made: சொன்னான் (ல் before ன்) cites புள்ளிமயங்கியல் 71 and 72,
    கேட்டான் (ள் before ட்) cites 101 and 7."""
    def verses(word, lemma, tag):
        [s] = [s for s in _verb(word, lemma, tag).round_trip.steps
               if s.rule == "eetrumei_varumei_thirithal"]
        return {r.verse for r in s.sources if r.verse and "உரை" not in r.verse}
    pulli = "எழுத்ததிகாரம் › புள்ளிமயங்கியல் › நூற்பா "
    sol = verses("சொன்னான்", "சொல்", "past=ன்")
    assert {pulli + "71", pulli + "72"} <= sol and not {pulli + "37", pulli + "101"} & sol
    kel = verses("கேட்டான்", "கேள்", "past=ட்")
    assert {pulli + "101", pulli + "7"} <= kel and not {pulli + "71", pulli + "102"} & kel


def test_muzhku_and_moozhku_each_decode_from_their_own_root():
    """விசாகப் பெருமாளையர் gives முழுகு → முழுகினான், மூழ்கினான் as one root changing. Saran
    (2026-11-25): மூழ்கு is the written verb and முழுகு its colloquial form, so each word decodes from
    its own root by the ordinary joins, with no பகுதி விகாரம் between them."""
    vikaram = {r["id"] for r in punarchi.vikaram_rules()}
    for word, lemma in (("மூழ்கினான்", "மூழ்கு"), ("முழுகினான்", "முழுகு")):
        f = _verb(word, lemma, "past=இன்")
        assert f.round_trip.holds, word
        assert not [s for s in f.round_trip.steps if s.rule in vikaram], word
