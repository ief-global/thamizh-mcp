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
    Since D-028 the ந் is an இடைநிலை எழுத்து: நச்சினார்க்கினியர் names வந்தான்'s ந் 'கால வெழுத்திற்
    கேற்ற இடைநிலை யெழுத்து' (சொல். எச்சவியல் 67, p. 467). It was a சந்தி த் → ந் on TVA C0212 §5.3.6
    and Saran's ruling of 2026-08-11; a classical commentary outranks both."""
    f = _decode("காத்திருந்தாள்")
    assert [(c.part, c.form, c.surface) for c in f.components] == [
        ("பகுதி", "காத்திரு", None), ("இடைநிலை", "ந்", None), ("இடைநிலை", "த்", None),
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

def test_every_rule_in_the_table_is_implemented_and_vice_versa():
    table_ids = {r["id"] for r in punarchi.table()["join_rules"]} - {"uyirmei"}
    assert table_ids == set(punarchi._ORDER)


def test_every_rule_declares_a_known_status_and_classical_rules_cite_a_verse():
    statuses = set(punarchi.table()["status_values"])
    for r in punarchi.table()["join_rules"]:
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
        if r["status"] == "parked":
            assert "D-023" in r["parked"]


def test_every_cited_verse_resolves_and_is_quoted_from_the_pinned_edition():
    for r in punarchi.table()["join_rules"]:
        for c in r["cites"]:
            if c["authority"] == "Tholkappiyam":
                text = classical.tholkappiyam_verse(c["athikaram"], c["iyal"], c["verse"])
            else:
                text = classical.nannul_verse(c["verse"])
            assert text, f"{r['id']}: {c} does not resolve in data/classical/"
        for ref in punarchi.cite(r["id"]):
            assert ref.verse_text, f"{r['id']}: {ref.verse} carries no quoted text"


def test_tholkappiyam_is_cited_first_wherever_it_is_cited():
    for r in punarchi.table()["join_rules"]:
        auths = [c["authority"] for c in r["cites"]]
        if "Tholkappiyam" in auths:
            assert auths[0] == "Tholkappiyam", r["id"]
        elif r["status"] == "classical":
            assert r.get("tholkappiyam_searched"), (
                f"{r['id']} cites only Nannūl, so it must record that Tholkappiyam was searched")


def test_a_parked_rule_never_carries_a_label():
    for r in punarchi.table()["join_rules"]:
        if r["status"] == "parked":
            assert not r.get("part"), f"{r['id']} is parked, so it must not name an உறுப்பு"


def test_no_verb_part_is_labelled_santhi_once_the_commentary_is_read():
    """D-028 (Saran, 2026-11-25): a classical commentary ALWAYS outranks a TVA course book.
    நச்சினார்க்கினியர் never calls a part of a verb சந்தி; the medial letters are இடைநிலை எழுத்து. So
    the strong-verb doubled consonant (D-026's சந்தி, TVA C0212 §5.3.5) and வந்தான்'s ந் (TVA
    C0212 §5.3.6) are both இடைநிலை now, each citing the scan-verified passage it rests on."""
    for rid in ("irattitha_otru", "idainilai_na"):
        rule = punarchi.rules()[rid]
        assert rule["status"] == "urai" and rule["part"] == "இடைநிலை", rid
        assert "TVA" in rule["superseded"]["source"] and "D-028" in rule["superseded"]["by"], rid
        assert rule["cites"][0]["authority"] == "Tholkappiyam", rid
    for word in ("படித்தான்", "படிக்கிறான்", "படிப்பான்", "பார்த்தான்", "கொடுத்தான்", "செய்வித்தான்",
                 "வந்தான்", "காத்திருந்தாள்"):
        f = _decode(word)
        assert all(c.part is not None for c in f.components), word
        assert "சந்தி" not in [c.part for c in f.components], word
        assert not any(s.status in ("parked", "textbook") for s in f.round_trip.steps
                       if s.rule in ("irattitha_otru", "idainilai_na")), word


def test_a_commentary_step_quotes_the_page_it_was_read_on():
    for rid in ("irattitha_otru", "idainilai_na"):
        refs = punarchi.cite(rid)
        urai = [r for r in refs if "உரை" in (r.verse or "")]
        assert urai and all(r.verse_text and "p. " in r.ref for r in urai), rid
        assert refs[0].name == "Tholkappiyam", f"{rid}: the நூற்பா is cited first"


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


# --- ruling (a): roots whose last consonant changes (D-029) -------------------------------------

_RULING_A = {
    # word: (lemma, tense tag, stem as it surfaces, the tense letter after it)
    "நின்றான்": ("நில்", "past=ற்", "நின்", "ற்"),
    "கொண்டான்": ("கொள்", "past=ட்", "கொண்", "ட்"),
    "கற்றான்": ("கல்", "past=ற்", "கற்", "ற்"),
    "கேட்டான்": ("கேள்", "past=ட்", "கேட்", "ட்"),
    "விற்றான்": ("வில்", "past=ற்", "விற்", "ற்"),
    "நிற்பான்": ("நில்", "fut=ப்", "நிற்", "ப்"),
    "கற்பான்": ("கல்", "fut=ப்", "கற்", "ப்"),
}


@pytest.mark.parametrize("word", _RULING_A)
def test_ruling_a_the_stem_change_is_named_and_cited(word):
    """நில் → நின் and கொள் → கொண் are stated for those verbs by நச்சினார்க்கினியர், சேனாவரையர் and
    மயிலைநாதர். கல் → கற், கேள் → கேட், வில் → விற் are Tholkappiyam's ல்/ள் join (புள்ளிமயங்கியல் 71,
    101) carried into the பகுபதம், as சங்கர நமச்சிவாயர் and சிவஞான முனிவர் say such changes are,
    with விசாகப் பெருமாளையர் naming கல் → கற்றான். Each split is root + tense letter + ஆன்."""
    lemma, tag, stem, letter = _RULING_A[word]
    f = decoder.decode_formation(word, MorphAnalysis(lemma=lemma, pos="verb",
                                                    tags=["fin", tag, "3sgm=ஆன்"]))
    assert f.round_trip.holds, word
    assert [(c.part, c.form, c.surface) for c in f.components] == [
        ("பகுதி", lemma, stem), ("இடைநிலை", letter, None), ("விகுதி", "ஆன்", None)]
    [step] = [s for s in f.round_trip.steps if s.rule == "stem_alternant"]
    assert step.status == "urai" and "திரிதல்" in step.effect, word
    assert step.sources[0].authority == "Tholkappiyam", f"{word}: the நூற்பா leads"
    assert any("உரை" in (r.verse or "") and r.verse_text and "p. " in (r.ref or "")
               for r in step.sources), f"{word}: a commentary quoted from its page"


def test_ruling_a_sol_stays_parked_because_no_text_splits_it():
    """சொன்னான்: மயிலைநாதர் says only that it does not take the இன் இடைநிலை; விசாகப்
    பெருமாளையர் lists it among roots that change in many ways. Nothing names the change, so it stays
    parked (D-023)."""
    f = decoder.decode_formation("சொன்னான்", MorphAnalysis(lemma="சொல்", pos="verb",
                                                          tags=["fin", "past=ன்", "3sgm=ஆன்"]))
    [step] = [s for s in f.round_trip.steps if s.rule == "stem_alternant"]
    assert step.status == "parked" and "not named" in step.effect


def test_ruling_a_never_generates_a_stem_change_from_the_join_alone():
    """The ல் → ற் join would turn கொல் into *கொற்றான், but the verb is கொன்றான். So stem changes
    are LISTED per verb in punarchi.json, each with its own citation; none is produced by rule."""
    lemmas = {e["lemma"] for e in punarchi.table()["stem_alternants"]["entries"]}
    assert {"நில்", "கொள்", "கல்", "கேள்", "வில்"} <= lemmas
    assert "கொல்" not in lemmas and "சொல்" not in lemmas
