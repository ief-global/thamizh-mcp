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
  4. I2PT attestation as a borrowed word (no orthographic marker → source language undetermined).
  5. Clean native ThamizhiMorph FST parse + no non-native markers → இயற்சொல் (moderate: a fully
     naturalized தற்பவம் borrowing can look native).
"""
from __future__ import annotations

from typing import Optional

from tamil import utf8

from thamizh_mcp.schema import Origin, SourceRef

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
    """Base consonant (mei, with pulli) of one grapheme, or None if it is a bare vowel."""
    split = utf8.splitMeiUyir(grapheme)
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


def classify_origin(
    normalized: str, *, fst_native_parse: Optional[bool], in_i2pt: bool
) -> Origin:
    """Classify one normalized Tamil word's origin from offline signals.

    fst_native_parse: True = parses through the native FST, False = ran with no analysis,
    None = FST unavailable (foma not installed) — the native signal is then simply absent.
    in_i2pt: the word is an attested INDIC key in the Indic-To-Pure-Tamil lists.
    """
    grantha = grantha_letters_in(normalized)
    if grantha:
        # Grantha proves the word is NOT NATIVE. It does NOT prove the word is Sanskrit.
        #
        # Grantha is simply how Tamil writes sounds its own எழுத்து set lacks — whatever language
        # they came from. Treating it as a Sanskrit signal labelled பஸ் (bus), ஸ்கூல் (school),
        # ஹோட்டல் (hotel), ஆபீஸ் (office), நர்ஸ் (nurse), ஸ்டேஷன் (station), கிளாஸ் (class),
        # ஹாஸ்பிட்டல் (hospital), ஜன்னல் (Portuguese janela), ஜாமீன் and ஜில்லா (Urdu) as வடசொல் —
        # eleven confident-wrong answers in a 108-word everyday sweep, every one at 0.9.
        #
        # So: assert what the orthography actually licenses (is_native=False) and leave the SOURCE
        # language undetermined, exactly as the I2PT branch below does. Promoting to வடசொல் needs a
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

    if in_i2pt:
        # Attested borrowed, but no orthographic marker tells வடசொல் from loanword — honest unknown.
        return Origin(
            class_="unknown", is_native=False, confidence=0.5,
            evidence="attested as a borrowed word in the Indic-To-Pure-Tamil lists, but no "
                     "orthographic marker distinguishes வடசொல் from loanword — source language undetermined",
            alternatives=[{"class": "வடசொல்"}, {"class": "loanword"}],
            sources=[SourceRef(name="Indic-To-Pure-Tamil", tier="evolving",
                               ref="attested as a borrowed headword")])

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
