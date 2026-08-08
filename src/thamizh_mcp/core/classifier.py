"""Origin classification (objective 1) — இயற்சொல் / வடசொல் / loanword, grounded in Tamil
orthography, not guessed by the model. Like decoder.py: linguistic rules live in code, are
tested once, and carry their own citations.

Honesty boundary (blueprint §2): the classical four-way origin frame also has திரிசொல் (literary)
and திசைச்சொல் (regional) — those need lexical/dialectal corpus knowledge we do NOT have offline,
so they are NEVER auto-asserted here. When the offline signals cannot ground a class, we return
`unknown` with an explicit evidence note — never a fabricated class.

Signals, strongest first:
  1. Grantha letters (ஶ ஜ ஷ ஸ ஹ க்ஷ) — outside the native Tamil எழுத்து set → certainly BORROWED,
     source undetermined. Grantha marks a non-native sound, NOT a source language; it writes
     English, Portuguese and Urdu loans as readily as Sanskrit ones.
  2. முதல் எழுத்து violation — a mei that cannot begin a native word (Tholkappiyam மொழிமரபு).
  3. இறுதி எழுத்து violation — a bare vallinam final, which native words never take.
  4. Attested English romanization (Dakshina) — names English, but ONLY inside a branch
     where 1/2/3 already proved non-nativeness. Never consulted on its own.
  5. S2PT attestation as a வடசொல் headword — the lists are Sanskrit-scoped, so this names a source
     language, but the source is PROVISIONAL so the confidence is capped (see the branch).
  5. Clean native ThamizhiMorph FST parse + no non-native markers → இயற்சொல் (moderate: a fully
     naturalized தற்பவம் borrowing can look native).
"""
from __future__ import annotations

from typing import Optional

from tamil import utf8

from thamizh_mcp.schema import EquivalentCandidate, Origin, SenseOrigin, SourceRef

# --- citable rule sources ---
# Tholkappiyam-first (design rule): the எழுத்து / மொழிமரபு rules are Tholkappiyam's; Nannūl codifies
# the same முதல்/இறுதி எழுத்து lists. open-tamil supplies the concrete Grantha letter set.
THOLKAPPIYAM_MOZIMARABU = SourceRef(
    name="Tholkappiyam", tier="anchor", authority="Tholkappiyam",
    ref="எழுத்ததிகாரம், மொழிமரபு — முதல்/இறுதி எழுத்து; native எழுத்து set excludes Grantha",
    retrieved="classical (edition-pinned in Phase 4)")
OPEN_TAMIL_LETTERSET = SourceRef(
    name="open-tamil letter set", tier="anchor",
    ref="tamil.utf8.sanskrit_letters (Grantha: ஶ ஜ ஷ ஸ ஹ க்ஷ)", retrieved="open-tamil>=1.1")
_S2PT_NAME = "Sanskrit-To-Pure-Tamil (community தனித்தமிழ் lists)"

THAMIZHIMORPH_PARSE = SourceRef(
    name="ThamizhiMorph", tier="anchor",
    ref="native FST parse (lemma found in primary FSTs)", retrieved="see data/PINS.md")

# Grantha/Sanskrit base consonants — single code points that never occur in a native Tamil word
# (க்ஷ contains ஷ, so it is covered by the ஷ check).
_GRANTHA_BASES = frozenset("ஶஜஷஸஹ")

# Tholkappiyam மொழிமரபு: eight mei that cannot BEGIN a native Tamil word (all vowels may).
_FORBIDDEN_INITIAL_MEI = frozenset(("ட்", "ண்", "ர்", "ல்", "ழ்", "ள்", "ற்", "ன்"))

# The six vallinam mei — a native word never ends in a bare one of these (இறுதி எழுத்து).
_VALLINAM_MEI = frozenset(("க்", "ச்", "ட்", "த்", "ப்", "ற்"))


def _base_mei(grapheme: str) -> Optional[str]:
    """Base consonant (mei, with pulli) of one grapheme, or None if it is a bare vowel.

    Returns None rather than raising when open-tamil cannot split the grapheme. Real input
    contains malformed-but-Tamil-codepoint sequences — `நுா` (நு followed by a second vowel sign)
    occurs in crowd-sourced data and passes `normalize()`, since every codepoint IS Tamil.
    `utf8.splitMeiUyir` raises ValueError on it, which crashed `classify_origin` and would have
    surfaced as a 500 from the web head. An unsplittable grapheme simply carries no consonant
    signal, so the honest answer is "no mei", not a traceback.
    """
    try:
        split = utf8.splitMeiUyir(grapheme)
    except Exception:
        return None
    if isinstance(split, tuple):      # உயிர்மெய் → (mei, uyir)
        return split[0]
    if split.endswith("்"):           # already a pure mei (e.g. 'ஸ்')
        return split
    return None                       # a bare உயிர் vowel — no consonant


def grantha_letters_in(word: str) -> list[str]:
    """The Grantha/Sanskrit base letters present in the word (empty if none)."""
    return [ch for ch in _GRANTHA_BASES if ch in word]


def forbidden_initial(word: str) -> Optional[str]:
    """The offending word-initial mei if the word cannot begin a native Tamil word, else None."""
    letters = utf8.get_letters(word)
    if not letters:
        return None
    mei = _base_mei(letters[0])
    return mei if mei in _FORBIDDEN_INITIAL_MEI else None


def forbidden_final(word: str) -> Optional[str]:
    """The offending bare vallinam final if the word cannot end a native Tamil word, else None."""
    letters = utf8.get_letters(word)
    if not letters:
        return None
    last = letters[-1]
    return last if last in _VALLINAM_MEI else None


def looks_orthographically_native(word: str) -> bool:
    """Does the word survive every rule that can prove NON-nativeness?

    This is the honest half of the orthographic signals (D-015): they can never prove a word IS
    native, but they do prove when one is not. That is exactly what is needed to filter a synonym
    list -- en.wiktionary lists ரோடு as a synonym of சாலை's road sense, and ரோடு is English. Offering
    it as a "pure Tamil equivalent" would be worse than offering nothing.

    Non-Tamil script is excluded outright: a synonym field can carry a stray Latin token.
    """
    if not word or not all("\u0b80" <= ch <= "\u0bff" or ch in "\u200c\u200d" for ch in word):
        return False
    return not grantha_letters_in(word) and not forbidden_initial(word) and not forbidden_final(word)


WIKTIONARY_SYNONYM = SourceRef(
    name="English Wiktionary (synonyms)", tier="evolving",
    ref="{{syn|ta|...}} listed under the borrowed sense")


def _sense_alternatives(sense: dict, citation: Optional[str]) -> list[EquivalentCandidate]:
    """Tamil alternatives for ONE borrowed sense.

    Saran's ruling (2026-08-05): the native sense leads, but a reader who meant the BORROWED sense
    should still be handed the Tamil word -- கார் 'car' carries மகிழுந்து / சீருந்து / தானுந்து.
    The page's own synonym list is the attestation; the orthographic rules drop any synonym that is
    itself demonstrably borrowed (ரோடு).

    NOT presented as "pure Tamil": those rules prove non-nativeness only, so naturalized Sanskrit
    passes them -- தானம் 'place' yields சுவர்க்கம் (< स्वर्ग) and சக்தி (< शक्ति). `attested` refers to
    the word being attested on the page. Confidence 0.6, tier `evolving`. The loanword lexicon
    (Madras Tamil Lexicon, next build rung) is what would let this claim nativeness.
    """
    out: list[EquivalentCandidate] = []
    for w in sense.get("synonyms") or []:
        if not looks_orthographically_native(w):
            continue
        out.append(EquivalentCandidate(
            equivalent=w, source=WIKTIONARY_SYNONYM.name, tier="evolving",
            attestation="attested", confidence=0.6, citation=citation))
        if len(out) == 5:      # keep the answer readable; the citation carries the rest
            break
    return out


def _etymology_source(ety: dict) -> SourceRef:
    return SourceRef(name="English Wiktionary (etymology)", tier="evolving",
                     ref=ety.get("citation"), retrieved=ety.get("retrieved"))


def _sense_class(s: dict) -> str:
    """The Tholkappiyam origin class for ONE sense."""
    if s["relation"] == "inherited":
        return "இயற்சொல்"
    # vadasol is precisely "borrowed from Sanskrit"; any other source language is a loanword.
    return "வடசொல்" if s.get("source_lang") == "sa" else "loanword"


def _sense_phrase(s: dict) -> str:
    lang, word = s.get("source_lang_name", "?"), s.get("source_word")
    return f"{lang} {word}" if word else lang


def _sense_origins(senses: list[dict], citation: Optional[str] = None) -> list[SenseOrigin]:
    """The per-sense breakdown carried on every multi-sense answer (D-015, Session 3)."""
    out = []
    for s in senses:
        native = s["relation"] == "inherited"
        verb = "inherited from" if native else "borrowed from"
        out.append(SenseOrigin(
            sense=s.get("sense"),
            class_=_sense_class(s),
            is_native=native,
            borrowed_from=None if native else s.get("source_lang_name"),
            source_word=s.get("source_word"),
            relation=s["relation"],
            evidence=f"{verb} {_sense_phrase(s)}",
            # only a borrowed sense needs an equivalent; a native sense already IS the Tamil word
            tamil_alternatives=[] if native else _sense_alternatives(s, citation),
        ))
    return out


def _from_etymology(normalized: str, ety: dict, fst_native_parse: Optional[bool]) -> Origin:
    """Turn a stated source language into a Tholkappiyam origin class.

    Confidence is deliberately capped below the orthographic rules' certainty about NON-nativeness,
    because this source is `evolving`: Wiktionary etymologies are crowd-edited and some are
    genuinely contested (pasu is given as Sanskrit pasu while a Dravidian *pacu is also argued). The
    competing class therefore always stays in `alternatives`, and the citation is always attached so
    a scholar can check the claim rather than take our word for it. A `der` template ("derived from",
    possibly through intermediaries) is weaker than an outright borrowing statement and scores lower.
    """
    all_senses = ety.get("senses") or []
    sense_origins = (_sense_origins(all_senses, ety.get("citation"))
                     if len(all_senses) > 1 else [])

    if ety.get("relation") == "ambiguous":
        # HOMOGRAPH -- one form, two or more words, with different origins per sense.
        #
        # This used to return `unknown`: honest, but it threw away evidence we already held, and it
        # made five everyday words (kal, pu, pasu, salai, kar) look like coverage gaps.
        #
        # **Saran's ruling, 2026-08-05: the Tamil sense leads.** This is a Thamizh server, so the
        # reader is pointed at the Tamil word first; the borrowed sense is never suppressed -- it is
        # cited in the evidence, in `alternatives`, and in full under `senses`. Confidence sits
        # below a clean single-etymology answer (0.8) because the headword class is a reporting
        # ruling layered on the evidence, not the evidence alone.
        native = [s for s in all_senses if s["relation"] == "inherited"]
        borrowed = [s for s in all_senses if s["relation"] != "inherited"]

        if native:
            lead = native[0]
            others = ", ".join(
                (f"'{s['sense']}', " if s.get("sense") else "") + f"borrowed from {_sense_phrase(s)}"
                for s in borrowed)
            lead_label = f"'{lead['sense']}', " if lead.get("sense") else ""
            more_native = (f" The same Tamil word also covers "
                           + ", ".join(f"'{s['sense']}'" for s in native[1:] if s.get("sense")) + "."
                           ) if len(native) > 1 and any(s.get("sense") for s in native[1:]) else ""
            return Origin(
                class_="இயற்சொல்", is_native=True,
                confidence=0.7,
                evidence=(f"homograph -- one form, more than one word. The Tamil sense leads: "
                          f"{lead_label}inherited from {_sense_phrase(lead)}.{more_native} "
                          f"The same form is separately {others}; that is a different word sharing "
                          f"the spelling, listed in full under senses. English Wiktionary "
                          f"(evolving source -- evidence, not authority); see the citation."),
                senses=sense_origins,
                alternatives=[{"class": _sense_class(s), "sense": s.get("sense"),
                               "note": f"the distinct sense borrowed from {_sense_phrase(s)}"}
                              for s in borrowed],
                sources=[_etymology_source(ety), THOLKAPPIYAM_MOZIMARABU])

        # No Tamil sense at all -- the senses just disagree about WHICH foreign language. Nothing
        # in the ruling picks a winner there, so the headword stays honest and the senses carry it.
        return Origin(
            class_="unknown", is_native=False, confidence=0.5,
            evidence=("this form is borrowed in every sense, but the senses name different source "
                      "languages: "
                      + "; ".join((f"'{s['sense']}' " if s.get("sense") else "")
                                  + f"from {_sense_phrase(s)}" for s in borrowed)
                      + ". Which applies depends on the sense meant. English Wiktionary; "
                        "see the citation."),
            senses=sense_origins,
            alternatives=[{"class": _sense_class(s), "sense": s.get("sense")} for s in borrowed],
            sources=[_etymology_source(ety), THOLKAPPIYAM_MOZIMARABU])

    stated = ety.get("certainty") == "stated"
    conf = 0.8 if stated else 0.65
    lang, code = ety.get("source_lang_name", "?"), ety.get("source_lang")
    src_word = ety.get("source_word")
    origin_phrase = f"{lang} {src_word}" if src_word else lang
    verb = "borrowed from" if ety.get("relation") == "borrowed" else "inherited from"
    evidence = (f"English Wiktionary states the Tamil word is {verb} {origin_phrase} "
                f"({{{{{ety.get('template')}}}}} template). Evolving source -- evidence, not "
                f"authority; see the citation.")

    if ety.get("is_native"):
        # Positive evidence of nativeness -- the one thing the FST parse alone could never give.
        return Origin(
            class_="இயற்சொல்", is_native=True,
            confidence=conf, evidence=evidence, senses=sense_origins,
            alternatives=[{"class": "வடசொல்",
                           "adaptation": "தற்பவம்",
                           "note": "a fully naturalized borrowing can be recorded as inherited"}],
            sources=[_etymology_source(ety), THAMIZHIMORPH_PARSE] if fst_native_parse
            else [_etymology_source(ety)])

    if code == "sa":
        # vadasol is precisely "borrowed from Sanskrit" in the Tholkappiyam frame.
        return Origin(
            class_="வடசொல்", is_native=False,
            borrowed_from="Sanskrit", confidence=conf, evidence=evidence, senses=sense_origins,
            alternatives=[{"class": "loanword",
                           "note": "if the Sanskrit derivation is disputed"}],
            sources=[_etymology_source(ety), THOLKAPPIYAM_MOZIMARABU])

    # Any other language: a borrowing that is NOT Sanskrit -- `loanword`, with the source named.
    return Origin(
        class_="loanword", is_native=False, borrowed_from=lang, confidence=conf, evidence=evidence,
        senses=sense_origins,
        alternatives=[{"class": "வடசொல்",
                       "note": "if the source is ultimately Sanskrit"}],
        sources=[_etymology_source(ety), THOLKAPPIYAM_MOZIMARABU])


DAKSHINA_ROMANIZATION = SourceRef(
    name="Google Dakshina (attested romanizations)", tier="anchor",
    ref="Roark et al. 2020 (LREC) — CC BY-SA 4.0; see data/PINS.md")


def _from_english_loan(loan: dict, non_native_reason: str) -> Origin:
    """Name English as the source, having ALREADY established the word is not native.

    The split is D-015's: orthography proves NON-nativeness, positive evidence names the language.
    This function only ever runs inside a branch that has proved the former, so it answers "which
    language" and never "is it borrowed". Ungated, the same evidence mislabels கால் as "call" and
    கார் as "car" — see adapters/loanwords.py.
    """
    english, n = loan["english"], loan.get("attestations", 0)
    return Origin(
        class_="loanword", is_native=False, borrowed_from="English", confidence=0.8,
        evidence=(f"{non_native_reason} The source is English: the word is attested in Latin script "
                  f"as \u201c{english}\u201d by {n} independent annotators in the Google Dakshina "
                  "romanization lexicon, and that spelling is an English word. Attested usage, not "
                  "a phonetic guess \u2014 but a romanization lexicon records how speakers write a "
                  "word, so it is evidence of an English source rather than a dictionary etymology."),
        alternatives=[{"class": "\u0bb5\u0b9f\u0b9a\u0bca\u0bb2\u0bcd",
                       "note": "if the word reached Tamil through Sanskrit rather than English"}],
        sources=[THOLKAPPIYAM_MOZIMARABU, DAKSHINA_ROMANIZATION])


def classify_origin(
    normalized: str, *, fst_native_parse: Optional[bool], in_s2pt: bool,
    etymology: Optional[dict] = None, english_loan: Optional[dict] = None,
) -> Origin:
    """Classify one normalized Tamil word's origin.

    fst_native_parse: True = parses through the native FST, False = ran with no analysis,
    None = FST unavailable (foma not installed) — the native signal is then simply absent.
    in_s2pt: the word is an attested வடசொல் headword in the Sanskrit-To-Pure-Tamil lists.
    english_loan: attested-English-romanization evidence from `adapters/loanwords.py`, or None.
    Consulted ONLY inside a branch that has already proved non-nativeness — it names a language,
    it never decides whether the word is borrowed.
    etymology: a source-language claim from `adapters/etymology.py`, or None when the lookup was
    not run (enrichment disabled) or found nothing. This is the ONLY signal that can name a source
    language; every rule below it can prove non-nativeness but not provenance.
    """
    if etymology:
        return _from_etymology(normalized, etymology, fst_native_parse)

    grantha = grantha_letters_in(normalized)
    if grantha:
        if english_loan:
            return _from_english_loan(english_loan, (
                f"contains Grantha letter(s) {' '.join(grantha)} — outside the native Tamil "
                "எழுத்து set (Tholkappiyam எழுத்ததிகாரம்), so the word is certainly borrowed."))
        # Grantha proves the word is NOT NATIVE. It does NOT prove the word is Sanskrit.
        #
        # Grantha is simply how Tamil writes sounds its own எழுத்து set lacks — whatever language
        # they came from. Treating it as a Sanskrit signal labelled பஸ் (bus), ஸ்கூல் (school),
        # ஹோட்டல் (hotel), ஆபீஸ் (office), நர்ஸ் (nurse), ஸ்டேஷன் (station), கிளாஸ் (class),
        # ஹாஸ்பிட்டல் (hospital), ஜன்னல் (Portuguese janela), ஜாமீன் and ஜில்லா (Urdu) as வடசொல் —
        # eleven confident-wrong answers in a 108-word everyday sweep, every one at 0.9.
        #
        # So: assert what the orthography actually licenses (is_native=False) and leave the SOURCE
        # language undetermined, unlike the S2PT branch below. Promoting to வடசொல் needs a
        # positive Sanskrit signal — a lexicon — which we do not have offline. Honest gap over a
        # confident guess (blueprint §2).
        return Origin(
            class_="unknown", is_native=False, confidence=0.5,
            evidence=f"contains Grantha letter(s) {' '.join(grantha)} — outside the native Tamil "
                     "எழுத்து set (Tholkappiyam எழுத்ததிகாரம்), so the word is certainly borrowed. "
                     "Grantha marks a non-native SOUND, not a source language: it is used for "
                     "Sanskrit, English, Portuguese and Urdu borrowings alike, so the source is "
                     "undetermined without a lexicon.",
            alternatives=[{"class": "வடசொல்", "note": "if the source is Sanskrit"},
                          {"class": "loanword", "note": "if the source is any other language"}],
            sources=[THOLKAPPIYAM_MOZIMARABU, OPEN_TAMIL_LETTERSET])

    bad_initial = forbidden_initial(normalized)
    if bad_initial:
        if english_loan:
            return _from_english_loan(english_loan, (
                f"word-initial ‘{bad_initial}’ cannot begin a native Tamil word (Tholkappiyam "
                "மொழிமரபு, முதல் எழுத்து rule), so the word is certainly borrowed."))
        # Same defect as the Grantha branch above: a முதல் எழுத்து violation proves the word is NOT
        # NATIVE; it says nothing about WHICH language it came from. Sanskrit borrowings break this
        # rule as readily as English ones — ரூபம் (Skt rūpa) and ராஜா sit beside ரயில் and லாரி.
        #
        # Calling them all `loanword` (which in the Tholkappiyam frame means a NON-Sanskrit borrowing)
        # got ரயில்/ரேடியோ/லாரி right and ரூபம் wrong — but all four by the same ungrounded
        # inference. Three lucky hits are still guesses, so they go too.
        return Origin(
            class_="unknown", is_native=False, confidence=0.5,
            evidence=f"word-initial ‘{bad_initial}’ cannot begin a native Tamil word "
                     "(Tholkappiyam மொழிமரபு, முதல் எழுத்து rule), so the word is certainly "
                     "borrowed — but the rule marks non-nativeness, not a source language: "
                     "Sanskrit borrowings break it too (ரூபம், ராஜா), so the source is "
                     "undetermined without a lexicon.",
            alternatives=[{"class": "வடசொல்", "note": "if the source is Sanskrit"},
                          {"class": "loanword", "note": "if the source is any other language"}],
            sources=[THOLKAPPIYAM_MOZIMARABU])

    bad_final = forbidden_final(normalized)
    if bad_final:
        if english_loan:
            return _from_english_loan(english_loan, (
                f"ends in bare vallinam ‘{bad_final}’ — native Tamil words do not end in "
                "க்/ச்/ட்/த்/ப்/ற் (Tholkappiyam மொழிமரபு, இறுதி எழுத்து rule)."))
        # NOT the same defect as the two rules above, and deliberately left asserting `loanword`.
        # Those two turn on WHICH LETTERS appear, which is neutral about the source language. This
        # one turns on MORPHOLOGICAL ASSIMILATION: a word ending in a bare vallinam has not been
        # adapted to Tamil at all. Sanskrit borrowings are adapted — தற்சமம்/தற்பவம் — and take Tamil
        # endings (ரூபம், யோகம், மந்திரம், மனிதன்), so they do not surface this way. An unadapted
        # final really is evidence of a non-Sanskrit (typically modern European) loan.
        # Reviewable: if Saran knows a Sanskrit borrowing that keeps a bare vallinam final, this
        # branch should join the other two in returning `unknown`.
        return Origin(
            class_="loanword", is_native=False, confidence=0.75,
            evidence=f"ends in bare vallinam ‘{bad_final}’ — native Tamil words do not end in "
                     "க்/ச்/ட்/த்/ப்/ற் (Tholkappiyam மொழிமரபு, இறுதி எழுத்து rule)",
            alternatives=[{"class": "வடசொல்", "note": "source language undetermined"}],
            sources=[THOLKAPPIYAM_MOZIMARABU])

    if in_s2pt:
        # The lists are **வடசொல்-scoped**, not "borrowed in general" — upstream is
        # narVidhai/Sanskrit-To-Pure-Tamil-Dictionary, README titled "வடசொல் to தமிழ்", and its four
        # sub-lists are all வடமொழி→தமிழ் purist glossaries. So membership IS positive evidence of a
        # Sanskrit source. We previously returned `unknown` here, saying "no orthographic marker
        # distinguishes வடசொல் from loanword" — true, but it ignored what the source is ABOUT, and
        # threw away the one thing the list actually attests.
        #
        # Confidence 0.55 — deliberately the lowest committing score in this module, BELOW the
        # 0.8 an en.wiktionary etymology earns, because the source is PROVISIONAL: no upstream
        # LICENCE file, last commit 2020, and its own upstreams are four scraped community sites
        # with unstated terms. This branch only runs when en.wiktionary had nothing (etymology is
        # checked first), so it is a floor, never an override.
        #
        # The evidence string names the weakness on purpose. A reader who inspects our sources
        # should find that we already told them — that is what makes the provenance worth trusting.
        return Origin(
            class_="வடசொல்", is_native=False, borrowed_from="Sanskrit", confidence=0.55,
            evidence="attested as a வடசொல் headword in the Sanskrit-To-Pure-Tamil தனித்தமிழ் lists "
                     "(விருபா · தமிழ்ச்சொல் · ThamizhDNA · தமிழ்மந்திரம், aggregated upstream). Those lists "
                     "exist to give Tamil replacements for SANSKRIT words, so membership is evidence "
                     "of a Sanskrit source. Weak evidence, deliberately scored low: the aggregate is "
                     "a community compilation, unmaintained since 2020, with no stated licence and "
                     "scraped upstreams — evidence, NOT authority. No en.wiktionary etymology was "
                     "available for this word, or it would have been preferred.",
            alternatives=[{"class": "loanword",
                           "note": "if the word is borrowed from a non-Sanskrit source and the "
                                   "purist list mis-scoped it"},
                          {"class": "unknown",
                           "note": "if the community compilation is not accepted as evidence"}],
            sources=[SourceRef(name=_S2PT_NAME, tier="evolving",
                               ref="https://github.com/narVidhai/Sanskrit-To-Pure-Tamil-Dictionary"
                                   " — attested as a வடசொல் headword (provisional source)")])

    if fst_native_parse:
        return Origin(
            class_="இயற்சொல்", is_native=True, confidence=0.6,
            evidence="parses through the native ThamizhiMorph FST and obeys Tamil எழுத்து rules "
                     "(no Grantha letters, valid முதல்/இறுதி எழுத்து); no borrowed attestation",
            alternatives=[{"class": "வடசொல்", "adaptation": "தற்பவம்",
                           "note": "a fully naturalized borrowing can look native"}],
            sources=[THOLKAPPIYAM_MOZIMARABU, THAMIZHIMORPH_PARSE])

    reason = ("native FST parse unavailable (foma not installed)"
              if fst_native_parse is None else "no native FST analysis")
    return Origin(
        class_="unknown", is_native=False, confidence=0.0,
        evidence=f"no positive signal: not attested as borrowed, no non-native orthographic "
                 f"markers, and {reason}",
        sources=[])
