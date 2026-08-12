"""Linguistic decoding — lives in code, tested once, never re-derived by the model.

Implemented: FST POS tag → சொல் வகை (Tholkappiyam Collatikāram word classes);
FST case tag → வேற்றுமை (Tholkappiyam வேற்றுமையியல், eight cases);
FST tags → பகுபத உறுப்பு Formation (Nannūl six-part labels) + verb tense/PNG grammar.

Formation honesty boundary (blueprint §2, tamil-grammar.md §3): decode only what the FST grounds.
Verbs hand over surface forms (past=த், 3sgm=ஆன்) → பகுதி/இடைநிலை/விகுதி are read directly. Nouns give
feature tags (infInc, loc) → விகுதி is the case உருபு matched against the surface; சாரியை/விகாரம் are
asserted ONLY where a confident classical rule applies (e.g. -அம் noun → அத்து சாரியை, ம்→த் திரிதல்).
A join we cannot classify is left unnamed, never invented.
"""
from __future__ import annotations

from typing import NamedTuple, Optional

from thamizh_mcp import config
from thamizh_mcp.core import classical
from thamizh_mcp.schema import (
    Formation, FormationComponent, GrammarCase, MorphAnalysis, Pos, SandhiEvent,
    WordClass, WordType,
)

# Citations QUOTE the நூற்பா (D-018). `retrieved` used to say "edition-pinned in Phase 4" — stale
# since D-011 closed and both editions ARE pinned; core/classical.py fills it from the artifact's
# own edition line.
#
# As of 2026-08-11 EVERY SourceRef here is verse-cited; the last three (COLLATIKARAM, VETRUMAI,
# VINAIYIYAL) carried `verse=None` and cited only a section. The rule that allowed that still
# stands and is not a licence to guess: a நூற்பா whose number has not been confirmed against
# data/classical/ keeps `verse=None` and cites the section, which is the honest interim D-011
# requires. Do NOT fill one in from memory or from a secondary source; TVA renumbers (its 336 is
# 337 here). Build these through `classical.cite_*`, never by hand — that way the quoted text
# comes from the pinned artifact and cannot drift from the edition.
# The four-way word-class frame is stated across TWO நூற்பா, not one, and the citation says so:
# பெயரியல் 4 names பெயர் and வினை as the two சொல்; பெயரியல் 5 adds இடைச்சொல் and உரிச்சொல் as
# arising "அவற்று வழி மருங்கின்" — in their train. Citing 4 alone for a four-class decode would
# credit that verse with two classes it does not name, so both travel with the claim.
THOLKAPPIYAM_COLLATIKARAM = classical.cite_tholkappiyam(
    "சொல்லதிகாரம்", "பெயரியல்", 4,
    "சொல்லதிகாரம், பெயரியல் — பெயர் and வினை, the two primary word classes")
THOLKAPPIYAM_COLLATIKARAM_IDAI_URI = classical.cite_tholkappiyam(
    "சொல்லதிகாரம்", "பெயரியல்", 5,
    "சொல்லதிகாரம், பெயரியல் — இடைச்சொல் and உரிச்சொல், which arise in their train")
# வேற்றுமையியல் 1 counts seven, 2 makes it eight with விளி, and 3 lists all eight ஈறு
# (பெயர் ஐ ஒடு கு இன் அது கண் விளி) — the verse `_CASE_MAP` actually mirrors, and the same one
# verrumai_urubu.json uses as its citation_format example.
THOLKAPPIYAM_VETRUMAI = classical.cite_tholkappiyam(
    "சொல்லதிகாரம்", "வேற்றுமையியல்", 3,
    "சொல்லதிகாரம், வேற்றுமையியல் — the eight வேற்றுமை and their ஈறு")
# நன்னூல் 133 names the six உறுப்பு outright — பகுதி விகுதி இடைநிலை சாரியை சந்தி விகாரம். Verified
# against the pinned edition and already cited by sariyai.json and vikaram.json.
NANNOOL_PAKUPADAM = classical.cite_nannul(133, "பகுபத உறுப்பிலக்கணம் — the six உறுப்பு labels")
# எழுத்ததிகாரம் › புணரியல் › 7 names the three விகாரம் — மெய் பிறிது ஆதல் / மிகுதல் / குன்றல்.
# Verified; already cited by vikaram.json, and it is the verse behind Saran's 2026-08-02 ruling that
# the decoder emits Tholkappiyam's விகாரம் names rather than Nannūl's.
THOLKAPPIYAM_PUNARIYAL = classical.cite_tholkappiyam(
    "எழுத்ததிகாரம்", "புணரியல்", 7, "எழுத்ததிகாரம், புணரியல் — சந்தி/விகாரம்")
# வினையியல் 1 defines வினை as what is thought of WITH காலம் ("...காலமொடு தோன்றும்") — the
# authority for the decoder attaching tense to a verb at all. வினையியல் 2 adds that the காலம் are
# three; that count is already carried by the tense decode itself.
THOLKAPPIYAM_VINAIYIYAL = classical.cite_tholkappiyam(
    "சொல்லதிகாரம்", "வினையியல்", 1,
    "சொல்லதிகாரம், வினையியல் — வினை appears with காலம் (tense/முற்று)")

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
# The parenthesised form is the உருபு and ONLY the உருபு. A சொல்லுருபு (உடன், உடைய, கொண்டு …) is a
# separate category and must never appear here — the earlier map showed "அது/உடைய" and
# "இன்/இலிருந்து", presenting a word-postposition (and, for இலிருந்து, a modern form in neither
# authority) as if it were the case marker. Tholkappiyam's form leads where the two differ.
_CASE_MAP: dict[str, tuple[int, str, str]] = {
    "nom": (1, "முதல் வேற்றுமை (எழுவாய் — உருபு இல்லை)", "subject"),
    "acc": (2, "இரண்டாம் வேற்றுமை (ஐ)", "direct object"),
    "inst": (3, "மூன்றாம் வேற்றுமை (ஒடு/ஆல்/ஆன்)", "instrument/agency"),
    "soc": (3, "மூன்றாம் வேற்றுமை (ஒடு/ஓடு)", "sociative/accompaniment"),
    "dat": (4, "நான்காம் வேற்றுமை (கு)", "dative/recipient"),
    "abl": (5, "ஐந்தாம் வேற்றுமை (இன்/இல்)", "ablative/comparison"),
    "gen": (6, "ஆறாம் வேற்றுமை (அது/ஆது/அ)", "genitive/possession"),
    "loc": (7, "ஏழாம் வேற்றுமை (கண் ஆதி)", "locative/இடப்பொருள்"),
    "voc": (8, "எட்டாம் வேற்றுமை (விளி — உருபு இல்லை)", "vocative/address"),
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


# --- Formation / grammar decoding (Nannūl six-part உறுப்பு + Tholkappiyam elements) ---

# Verb tense marker (இடைநிலை): FST hands over a SURFACE form (pres=கிற்); the grammatical உறுப்பு is
# a different thing (கிறு). data/grammar/idainilai.json maps one to the other and splits off any
# வல்லினம் doubling as its own சந்தி உறுப்பு. See NANNOOL_IDAINILAI below.
_TENSE_ROLE: dict[str, str] = {
    "past": "இறந்தகாலம்", "pres": "நிகழ்காலம்", "fut": "எதிர்காலம்",
}


def _load_table(path, key: Optional[str] = None) -> dict:
    """Load a cited rule table (best-effort: a missing file must never break analysis)."""
    import json
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get(key, {}) if key else data


_IDAINILAI = _load_table(config.GRAMMAR_IDAINILAI_FILE, "idainilai")
_VIKUTHI = _load_table(config.GRAMMAR_VIKUTHI_FILE)
_SARIYAI = _load_table(config.GRAMMAR_SARIYAI_FILE)
_VERRUMAI = _load_table(config.GRAMMAR_VERRUMAI_FILE)

# Nannūl 154 names the three விகாரம் தோன்றல்/திரிதல்/கெடுதல்; Tholkappiyam (எழுத்ததிகாரம், புணரியல் 7)
# names them மிகுதல்/பிறிது ஆதல்/குன்றல் and is the primary authority for புணர்ச்சி. Saran's ruling
# (2026-08-02): emit the **Tholkappiyam** name, to nudge readers to Tholkappiyam first.
VIKARAM_MIKUTHAL = "மிகுதல்"      # Nannūl: தோன்றல் — something appears at the join
VIKARAM_KUNDRAL = "குன்றல்"       # Nannūl: கெடுதல் — something drops
VIKARAM_PIRITHU = "பிறிது ஆதல்"   # Nannūl: திரிதல் — something becomes another letter


def map_idainilai(tense_code: str, fst_surface: str) -> tuple[str, Optional[str], str]:
    """FST surface tense marker → (canonical இடைநிலை, சந்தி or None, class name).

    Nannūl names the உறுப்பு, not the surface morph: the FST's `pres=கிற்` is the grammatical
    இடைநிலை **கிறு**, and a strong verb's `pres=க்கிற்` is சந்தி க் + இடைநிலை கிறு (வல்லினம் மிகுதல்
    is புணர்ச்சி, not part of the marker). Unknown surfaces pass through unchanged rather than being
    guessed at — an unmapped form is reported as-is, never invented.
    """
    entry = _IDAINILAI.get(tense_code, {})
    hit = entry.get("from_fst", {}).get(fst_surface)
    cls = entry.get("class", "")
    if not hit:
        return fst_surface, None, cls
    return hit.get("idainilai", fst_surface), hit.get("sandhi"), cls


class Vikuthi(NamedTuple):
    """One விகுதி, decomposed the way Nannūl names it rather than the way the FST splits it."""
    vikuthi: str
    role: str
    sariyai: Optional[str] = None          # e.g. 3pln=அன is சாரியை அன் + விகுதி அ
    modern_plural: Optional[str] = None    # ‘கள்’ — modern accretion, NOT a classical விகுதி


def map_vikuthi(png_code: str, fst_surface: str) -> Vikuthi:
    """FST PNG suffix → the classical விகுதி, splitting off what is not part of it.

    Two things the FST's surface hides (D-014):
      · `2pl=ஈர்கள்` / `3ple=ஆர்கள்` — the classical விகுதி is ஈர்/ஆர் (நன்னூல் 337). ‘கள்’ is a
        MODERN plural accretion; per Saran's ruling (2026-08-02) it is emitted as its own component
        and labelled as modern, rather than silently dropped or folded into the விகுதி.
      · `3pln=அன` — Nannūl analyses நடந்தன as சாரியை அன் + விகுதி அ, i.e. TWO உறுப்புகள்.

    An unmapped surface passes through unchanged, never guessed.
    """
    role = _PNG_ROLE.get(png_code, "")
    hit = _VIKUTHI.get("from_fst", {}).get(f"{png_code}={fst_surface}")
    if not hit:
        return Vikuthi(fst_surface, role)
    cls = _VIKUTHI.get("classes", {}).get(hit.get("class_key", ""), {}).get("class", "")
    return Vikuthi(
        hit.get("vikuthi", fst_surface), role or cls,
        sariyai=hit.get("sariyai"), modern_plural=hit.get("modern_plural"),
    )


def map_sariyai(fst_tag: str, fst_surface: str) -> Optional[str]:
    """FST increment tag → the classical சாரியை, or None if unmapped.

    ThamizhiMorph tags this `euph` (‘euphonic’); Nannūl names it சாரியை — one of the six
    பகுபத உறுப்பு (133), with அன் among the seventeen பொதுச் சாரியை (244). The decoder previously
    had no handler at all, so வந்தனன் silently lost an உறுப்பு.
    """
    hit = _SARIYAI.get("from_fst", {}).get(f"{fst_tag}={fst_surface}")
    return hit.get("sariyai") if hit else None


def case_urubu_forms(case_tag: str) -> list[str]:
    """Every உருபு the cited table lists for a case, Tholkappiyam's form first.

    Replaces a one-form-per-case dict that could not represent inst ஒடு/ஆல்/ஆன், abl இன்/இல்,
    gen அது/ஆது/அ, or the கண்-headed open locative list.
    """
    return list(_VERRUMAI.get("cases", {}).get(case_tag, {}).get("urubu", []))


# Voice/derivation இடைநிலை that sit BETWEEN பகுதி and the tense marker (செய்+வி+த்+ஆன்).
# The FST supplies the surface form (caus=வி); order here is the surface order.
#
# RULING (Saran, 2026-08-02): causative வி is an **இடைநிலை**, not a பிறவினை விகுதி. TVA C0212 §6.1.7
# lists வி/பி among the பிறவினை விகுதி, but Nannūl's positional definition governs — இடைநிலை is what
# stands between முதனிலை and இறுதிநிலை — நன்னூல் 141 — and வி does. Settled; do not re-open.
_MID_ROLE: dict[str, str] = {
    "caus": "பிறவினை (causative)", "pass": "செயப்பாட்டு வினை (passive)",
}
# Verb terminal ending (விகுதி): PNG code → முற்று role (person·gender·number).
_PNG_ROLE: dict[str, str] = {
    "1sg": "தன்மை ஒருமை", "2sg": "முன்னிலை ஒருமை",
    "3sgm": "படர்க்கை ஆண்பால் ஒருமை", "3sgf": "படர்க்கை பெண்பால் ஒருமை",
    "3sgn": "படர்க்கை ஒன்றன்பால் ஒருமை",
    "3pln": "படர்க்கை பலவின்பால்",
    "1pl": "தன்மை பன்மை", "2pl": "முன்னிலை பன்மை",
    "3pl": "படர்க்கை பலர்பால்", "3ple": "படர்க்கை பலர்பால்",
    "3sgh": "படர்க்கை உயர்திணை ஒருமை (மரியாதை)", "3sghe": "படர்க்கை உயர்திணை (மரியாதை)",
    "3plh": "படர்க்கை உயர்திணை பன்மை",
    "opt": "வியங்கோள்",
}
_PULLI = "்"


def _split_tags(tags: list[str]) -> tuple[list[str], dict[str, str]]:
    """Split FST tags into bare tags and feature=form pairs ('past=த்' → {'past': 'த்'})."""
    bare: list[str] = []
    feats: dict[str, str] = {}
    for t in tags:
        if "=" in t:
            name, form = t.split("=", 1)
            feats[name] = form
        else:
            bare.append(t)
    return bare, feats


def _is_verb(pos: str) -> bool:
    return pos.lower() in ("verb", "vb")


def decode_verb_grammar(analysis: MorphAnalysis) -> tuple[Optional[str], Optional[str]]:
    """Verb காலம் (tense) and முற்று (person-number-gender) roles for grammar, or (None, None)."""
    if not _is_verb(analysis.pos):
        return None, None
    _, feats = _split_tags(analysis.tags)
    tense = next((_TENSE_ROLE[k] for k in _TENSE_ROLE if feats.get(k) not in (None, "", "∅")), None)
    png = next((_PNG_ROLE[k] for k in _PNG_ROLE if feats.get(k) not in (None, "", "∅")), None)
    return tense, png


def _am_stem(lemma: str) -> Optional[str]:
    """Oblique stem of an -அம் noun (மரம் → மர), or None if not an -அம் noun."""
    return lemma[:-2] if lemma.endswith("ம" + _PULLI) else None


def _decode_noun(lemma: str, word: str, bare: list[str],
                 comps: list[FormationComponent], sandhi: list[SandhiEvent]) -> bool:
    """Fill noun/pronoun உறுப்புகள். Returns whether the word is inflected."""
    inflected = False
    stem = _am_stem(lemma)
    # சாரியை — the oblique increment. Confident only for the -அம் declension (மரம் → மரத்து).
    if "infInc" in bare and stem is not None:
        inflected = True
        comps.append(FormationComponent(
            part="சாரியை", form="அத்து", role="oblique increment (சாரியை)", authority="Nannūl"))
        # மரம் + ஐ > மர + அத்து + ஐ (TVA C0214 §4.2.1). The ம் DROPS and the அத்து சாரியை APPEARS —
        # two விகாரம். It is not ‘ம் becomes த்’: the த் belongs to the சாரியை, nothing transforms.
        sandhi.append(SandhiEvent(
            type=VIKARAM_KUNDRAL,
            detail=f"{lemma} → {stem} — ஈற்று ‘ம்’ கெட்டது before the சாரியை",
            authority="Tholkappiyam"))
        sandhi.append(SandhiEvent(
            type=VIKARAM_MIKUTHAL,
            detail="‘அத்து’ சாரியை தோன்றியது — the ‘த்’ in மரத்து- belongs to it",
            authority="Tholkappiyam"))
    # விகுதி — plural கள் and/or the case உருபு.
    if "pl" in bare:
        inflected = True
        if stem is not None:
            sandhi.append(SandhiEvent(
                type=VIKARAM_PIRITHU, detail=f"{lemma} → {stem}ங் before the பன்மை விகுதி கள்",
                authority="Tholkappiyam"))
        comps.append(FormationComponent(
            part="விகுதி", form="கள்", role="பன்மை விகுதி (plural)", authority="Nannūl"))
    case_tags = [t for t in bare if t in _CASE_MAP and t != "nom"]
    urubu = _select_urubu(word, case_tags)
    if urubu is not None:
        inflected = True
        names = list(dict.fromkeys(_CASE_MAP[t][1] for t in case_tags))
        comps.append(FormationComponent(
            part="விகுதி", form=urubu, role=(" / ".join(names) + " உருபு"), authority="Nannūl"))
        if urubu == "கு" and "க்கு" in word:
            sandhi.append(SandhiEvent(
                type=VIKARAM_MIKUTHAL,
                detail="வல்லினம் மிகுதல் — க் doubles at the dative join (க்கு)",
                authority="Tholkappiyam"))
    return inflected


# An உருபு is listed in its standalone form (இல், இன், அது), but on the surface its initial uyir
# fuses into the preceding mei as a vowel sign — மரம்+இல் surfaces as மரத்த்+ில் = மரத்தில். Matching
# the standalone form against the surface therefore NEVER succeeds for a vowel-initial உருபு, which
# silently pushed every such case onto the fallback. These are the combining signs; அ is inherent in
# the consonant and so has no sign of its own.
_UYIR_SIGN: dict[str, str] = {
    "அ": "", "ஆ": "ா", "இ": "ி", "ஈ": "ீ", "உ": "ு", "ஊ": "ூ",
    "எ": "ெ", "ஏ": "ே", "ஐ": "ை", "ஒ": "ொ", "ஓ": "ோ", "ஔ": "ௌ",
}


def _surface_forms(urubu: str) -> list[str]:
    """The உருபு as written, plus how it actually appears once joined to a stem."""
    forms = [urubu]
    if urubu and urubu[0] in _UYIR_SIGN:
        forms.append(_UYIR_SIGN[urubu[0]] + urubu[1:])
    return [f for f in forms if f]


def _select_urubu(word: str, case_tags: list[str]) -> Optional[str]:
    """Pick the case உருபு the surface actually ends with, across EVERY form the case allows.

    Each case may carry several உருபு (inst ஒடு/ஆல்/ஆன், abl இன்/இல், gen அது/ஆது/அ, and a
    கண்-headed open list for loc), so the match runs over all of them, longest first. Falling back
    to the first listed form yields Tholkappiyam's, since the tables are ordered Tholkappiyam-first.
    """
    per_case = [(c, case_urubu_forms(c)) for c in case_tags]
    per_case = [(c, fs) for c, fs in per_case if fs]
    if not per_case:
        return None
    # Match on the SURFACE realisation, then report the canonical (standalone) உருபு.
    matched = [
        (len(sf), f)
        for _, fs in per_case for f in fs
        for sf in _surface_forms(f) if word.endswith(sf)
    ]
    if matched:
        return max(matched)[1]
    # No surface match — fall back to the FIRST TAGGED CASE's first form (Tholkappiyam's, since the
    # tables are ordered Tholkappiyam-first). Never to a merged list: for an ambiguous tag like
    # loc|abl that would hand back another case's உருபு entirely.
    return per_case[0][1][0]


def decode_formation(word: str, analysis: MorphAnalysis) -> Formation:
    """Decode one FST analysis into a பகுபத உறுப்பு Formation. Grounds only what the FST provides;
    unclassifiable joins are left unnamed (no invented split)."""
    lemma, pos = analysis.lemma, analysis.pos
    bare, feats = _split_tags(analysis.tags)
    comps: list[FormationComponent] = [FormationComponent(
        part="பகுதி", form=lemma, role="root/base (அடிச்சொல்)", authority="Nannūl")]
    sandhi: list[SandhiEvent] = []
    inflected = False

    if _is_verb(pos):
        # voice/derivation இடைநிலை first — it precedes the tense marker on the surface
        for mcode, mrole in _MID_ROLE.items():
            if feats.get(mcode) not in (None, "", "∅"):
                inflected = True
                comps.append(FormationComponent(
                    part="இடைநிலை", form=feats[mcode], role=mrole, authority="Nannūl"))
                break
        for tcode, trole in _TENSE_ROLE.items():
            if feats.get(tcode) not in (None, "", "∅"):
                inflected = True
                # FST surface → canonical Nannūl உறுப்பு, splitting off வல்லினம் doubling as சந்தி.
                marker, sandhi_form, cls = map_idainilai(tcode, feats[tcode])
                if sandhi_form:
                    comps.append(FormationComponent(
                        part="சந்தி", form=sandhi_form,
                        role="வல்லினம் மிகுதல் (strong-verb doubling)", authority="Tholkappiyam"))
                    sandhi.append(SandhiEvent(
                        type=VIKARAM_MIKUTHAL,
                        detail=f"வல்லினம் மிகுதல் — ‘{sandhi_form}’ doubles before the "
                               f"{cls or 'இடைநிலை'}",
                        authority="Tholkappiyam"))
                comps.append(FormationComponent(
                    part="இடைநிலை", form=marker, role=f"{trole} ({cls})" if cls else trole,
                    authority="Nannūl"))
                break
        # சாரியை — the FST tags it `euph` (‘euphonic’); Nannūl names it சாரியை and places it
        # between the இடைநிலை and the விகுதி (வந்தனன் = வா+த்+த்+அன்+அன்). Previously dropped.
        for scode in ("euph",):
            if (surface := feats.get(scode)) not in (None, "", "∅"):
                if form := map_sariyai(scode, surface):
                    inflected = True
                    comps.append(FormationComponent(
                        part="சாரியை", form=form,
                        role="இடைநிலைக்கும் விகுதிக்கும் இடையில் (சாரியை)", authority="Nannūl"))
                break
        for pcode in _PNG_ROLE:
            if (surface := feats.get(pcode)) not in (None, "", "∅"):
                inflected = True
                vk = map_vikuthi(pcode, surface)
                # A single FST suffix may hide a சாரியை in front of the விகுதி (3pln=அன).
                if vk.sariyai and not any(c.part == "சாரியை" for c in comps):
                    comps.append(FormationComponent(
                        part="சாரியை", form=vk.sariyai,
                        role="இடைநிலைக்கும் விகுதிக்கும் இடையில் (சாரியை)", authority="Nannūl"))
                comps.append(FormationComponent(
                    part="விகுதி", form=vk.vikuthi, role=vk.role, authority="Nannūl"))
                # ‘கள்’ is a modern accretion, not part of the classical விகுதி (நன்னூல் 337).
                # Emitted as its own component and labelled so, per Saran's ruling 2026-08-02.
                if vk.modern_plural:
                    comps.append(FormationComponent(
                        part="விகுதி", form=vk.modern_plural,
                        role="நவீன பன்மை விகுதி — modern plural accretion, NOT part of the "
                             "classical விகுதி (நன்னூல் 337 gives இர்/ஈர் alone)",
                        authority=None))  # deliberately none: no classical authority sanctions it
                break
    else:
        inflected = _decode_noun(lemma, word, bare, comps, sandhi)

    word_type: WordType = "பகுபதம்" if (inflected or word != lemma) else "பகாப்பதம்"
    sources = [NANNOOL_PAKUPADAM, THOLKAPPIYAM_PUNARIYAL]
    if _is_verb(pos):
        sources.append(THOLKAPPIYAM_VINAIYIYAL)
    elif any(c.part == "விகுதி" for c in comps):
        sources.append(THOLKAPPIYAM_VETRUMAI)
    return Formation(word_type=word_type, components=comps, sandhi=sandhi, sources=sources)
