"""Pydantic contract for one Tamil word analysis.

Mirrors schemas/word_analysis_schema.json (the canonical contract from the blueprint, §3).
Contract deviations logged here per blueprint:
  - v0.1: `Grammar.word_class` gains "unknown" so a schema-valid all-gaps object can exist
    before sources are wired (gap is still recorded explicitly in `WordAnalysis.gaps`).

Non-negotiables encoded in this shape (blueprint §2):
  provenance on every field (SourceRef: tier + authority + retrieved), honest gaps (Gap),
  all ambiguous analyses kept (all_analyses / alternatives), attested-only equivalents
  (EquivalentCandidate requires `source` + `attestation`).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["anchor", "evolving"]
Authority = Literal["Tholkappiyam", "Nannūl"]

OriginClass = Literal["இயற்சொல்", "திரிசொல்", "திசைச்சொல்", "வடசொல்", "loanword", "unknown"]
Pos = Literal["பெயர்ச்சொல்", "வினைச்சொல்", "இடைச்சொல்", "உரிச்சொல்", "unknown"]
WordClass = Literal["பெயர்", "வினை", "இடை", "உரிச்சொல்", "unknown"]
WordType = Literal["பகுபதம்", "பகாப்பதம்", "unknown"]
ComponentPart = Literal["பகுதி", "விகுதி", "இடைநிலை", "சாரியை", "சந்தி", "விகாரம்"]
# The three விகாரம், under BOTH authorities' names. Tholkappiyam (எழுத்ததிகாரம், புணரியல் 7) names
# them மிகுதல் / குன்றல் / பிறிது ஆதல்; Nannūl 154 restates them as தோன்றல் / கெடுதல் / திரிதல்.
# Same three events. The decoder emits the **Tholkappiyam** name (Saran's ruling, 2026-08-02 —
# Tholkappiyam-first, and it nudges readers to the older authority); the Nannūl names stay valid so
# a caller or an older record is not rejected. 'வல்லினம்மிகுதல்'/'வல்லினம்மிகாமை' are DESCRIPTIONS
# of an event, not classical விகாரம் names — retained for back-compatibility only; new code should
# put that wording in `detail` and set `type` to மிகுதல்.
SandhiType = Literal[
    "மிகுதல்", "குன்றல்", "பிறிது ஆதல்",              # Tholkappiyam — preferred
    "தோன்றல்", "கெடுதல்", "திரிதல்",                  # Nannūl — equivalent
    "வல்லினம்மிகுதல்", "வல்லினம்மிகாமை",              # descriptive, legacy
]
Adaptation = Literal["தற்சமம்", "தற்பவம்"]
Register = Literal["technical", "literary", "everyday"]
Attestation = Literal["attested", "proposed"]


class SourceRef(BaseModel):
    """Provenance for one claim. Anchors pin a version; evolving pulls pin a retrieval date."""
    name: str
    tier: Optional[Tier] = None
    authority: Optional[Authority] = None
    ref: Optional[str] = None
    retrieved: Optional[str] = None
    verse: Optional[str] = None   # D-011: the நூற்பா address. Nannūl is continuous so "நூற்பா 133"
    #                               suffices; Tholkappiyam numbers RESTART per இயல், so its label
    #                               carries அதிகாரம் › இயல் › நூற்பா. None = the edition does not
    #                               print it — the honest interim, never a fabricated number.
    verse_text: Optional[str] = None  # The நூற்பா ITSELF, quoted from the pinned edition (D-018).
    #                               A citation tells a scholar where to look; this shows them the
    #                               verse. Populated by core/classical.py; None when unavailable.

    # D-017 — the source's standing, stamped from data/sources.json by core/sources.annotate().
    # `grade` is EVIDENTIAL; `redistribution` is LEGAL. They are independent axes (D-016): the
    # Madras Tamil Lexicon is grade A AND consult-and-cite. A confidence number a reader cannot
    # interpret is not provenance — the grade is what makes it checkable.
    grade: Optional[str] = None            # A / B / C / D — see data/sources.json → grades
    licence: Optional[str] = None          # verbatim from the registry; "UNSTATED" is a real value
    redistribution: Optional[str] = None   # redistribute | serve-with-attribution | consult-and-cite


class EquivalentCandidate(BaseModel):
    """Attested-only: `source` + `attestation` are REQUIRED. The merge layer drops any
    candidate lacking an attestation source — an invented coinage can never surface."""
    model_config = ConfigDict(populate_by_name=True)

    equivalent: str
    source: str
    tier: Optional[Tier] = None
    register_: Optional[Register] = Field(default=None, alias="register")
    attestation: Attestation
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    citation: Optional[str] = None


class SenseOrigin(BaseModel):
    """Origin of ONE sense of a headword (D-015, Session 3).

    Origin is really a property of a WORD, and a homograph is two words sharing a form: கால் is
    leg (inherited from Proto-Dravidian *kāl) AND time (borrowed from Sanskrit काल). Modelling
    origin per-headword forced those into a single `unknown`, which is honest but discards
    evidence we already hold. This mirrors `Meaning.senses` so the two line up.
    """
    model_config = ConfigDict(populate_by_name=True)

    sense: Optional[str] = None            # the sense this origin belongs to — "leg", "time"
    class_: OriginClass = Field(default="unknown", alias="class")
    is_native: Optional[bool] = None
    borrowed_from: Optional[str] = None    # display name of the source language
    source_word: Optional[str] = None      # the etymon itself — *kāl, काल, car
    relation: Optional[str] = None         # inherited | borrowed | derived
    evidence: str = ""
    # Tamil alternatives for THIS sense — populated only when the sense is borrowed (a native
    # sense already IS the Tamil word). Saran's ruling, 2026-08-05: a reader who meant the English
    # word should still be handed the Tamil one — கார்'s 'car' sense carries மகிழுந்து / சீருந்து /
    # தானுந்து. Same attested-only contract as NativeEquivalent (source + attestation required).
    #
    # NOT called `native_equivalents`, deliberately. These come from the page's own {{syn|ta|…}}
    # list filtered through the orthographic rules, which prove NON-nativeness only — so obvious
    # borrowings (ரோடு) are excluded but naturalized Sanskrit still passes (தானம் 'place' offers
    # சுவர்க்கம் < स्वर्ग). Calling them "pure Tamil" would over-claim. The curated S2PT lists behind
    # `NativeEquivalent` are the anchor-tier answer; these are `evolving` evidence at 0.6.
    tamil_alternatives: list[EquivalentCandidate] = Field(default_factory=list)


class Origin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    class_: OriginClass = Field(default="unknown", alias="class")
    # None = genuinely undetermined, not False. Kept Optional for the case `senses` cannot resolve
    # (every sense borrowed from a different language); where a native sense exists it is True, per
    # Saran's ruling below.
    is_native: Optional[bool] = False
    borrowed_from: Optional[str] = None
    adaptation: Optional[Adaptation] = None
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    # One entry per sense when the headword is a homograph whose senses differ in origin; empty
    # for the ordinary single-origin word. **Saran's ruling (2026-08-05): where a Tamil sense and a
    # borrowed sense share a form, the Tamil sense leads at headword level** — this is a Thamizh
    # server, so it nudges the reader to the Tamil word first — and the borrowed sense is always
    # cited here and in `alternatives` for full disclosure, never suppressed.
    senses: list[SenseOrigin] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class MorphAnalysis(BaseModel):
    """One of possibly several valid analyses — never silently disambiguate."""
    lemma: str
    pos: str
    tags: list[str] = Field(default_factory=list)


class Sense(BaseModel):
    gloss_ta: Optional[str] = None
    gloss_en: Optional[str] = None
    pos: Optional[str] = None
    citation: Optional[str] = None


class Meaning(BaseModel):
    senses: list[Sense] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class FormationComponent(BaseModel):
    part: ComponentPart
    form: str
    role: Optional[str] = None
    authority: Optional[Authority] = None   # six-part labels: Nannūl; underlying elements: Tholkappiyam


class SandhiEvent(BaseModel):
    type: SandhiType
    detail: Optional[str] = None
    authority: Optional[Authority] = None   # புணர்ச்சி/விகாரம்: Tholkappiyam (எழுத்ததிகாரம், புணரியல்)


class Formation(BaseModel):
    word_type: WordType = "unknown"
    components: list[FormationComponent] = Field(default_factory=list)
    sandhi: list[SandhiEvent] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class GrammarCase(BaseModel):
    number: int = Field(ge=1, le=8)
    name: Optional[str] = None      # e.g. ஏழாம் வேற்றுமை
    function: Optional[str] = None  # e.g. locative / இடப்பொருள்


class Grammar(BaseModel):
    word_class: WordClass = "unknown"
    case: Optional[GrammarCase] = None
    tense: Optional[str] = None
    person_number_gender: Optional[str] = None
    authority: Optional[Authority] = None
    notes: Optional[str] = None
    sources: list[SourceRef] = Field(default_factory=list)


class NativeEquivalent(BaseModel):
    applicable: bool = False
    candidates: list[EquivalentCandidate] = Field(default_factory=list)
    note: Optional[str] = None
    sources: list[SourceRef] = Field(default_factory=list)


class Gap(BaseModel):
    """An explicit honest gap — a field no source could ground."""
    field: str
    note: str


class WordAnalysis(BaseModel):
    """The canonical word analysis object (blueprint §3)."""
    word: str
    normalized: str
    origin: Origin = Field(default_factory=Origin)
    lemma: str = ""
    all_analyses: list[MorphAnalysis] = Field(default_factory=list)
    pos: Pos = "unknown"
    meaning: Meaning = Field(default_factory=Meaning)
    formation: Formation = Field(default_factory=Formation)
    grammar: Grammar = Field(default_factory=Grammar)
    native_equivalent: NativeEquivalent = Field(default_factory=NativeEquivalent)
    gaps: list[Gap] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, indent=2)


STUB_NOTE = "no grounding source wired yet (scaffold stub — Phase 1/3 pending)"


def empty_analysis(word: str, normalized: str) -> WordAnalysis:
    """Schema-valid, all-gaps analysis: every unfilled field is an explicit Gap, never a guess."""
    return WordAnalysis(
        word=word,
        normalized=normalized,
        origin=Origin(evidence=STUB_NOTE),
        native_equivalent=NativeEquivalent(
            applicable=False, note="origin unresolved — equivalent check not applicable yet"
        ),
        gaps=[
            Gap(field=f, note=STUB_NOTE)
            for f in ("origin", "lemma", "pos", "meaning", "formation", "grammar", "native_equivalent")
        ],
    )
