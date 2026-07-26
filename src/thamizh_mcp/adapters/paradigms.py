"""Curated verb-paradigm fallback (ANCHOR) — fills ThamizhiMorph lexicon gaps for common verbs.

The primary FSTs miss a quarter to a third of everyday finite verb forms across all three tenses —
past (போனான், சொன்னான், கொடுத்தான், கற்றான், விற்றான், தூங்கினான்), present (வருகிறான், கொடுக்கிறான்,
கேட்கிறான்) and future (வருவான், கொடுப்பான், கேட்பான்) — because those lemmas or their irregular
tense stems are absent from the lexicon.
The guesser FSTs are NOT the answer: they return wrong lemmas (கொடுத் for கொடு, வந் for வா), i.e.
confident errors instead of honest gaps.

Instead this matches against a hand-verified paradigm table (`data/verb_paradigms.json`): an explicit
list of lemma + irregular past stem, combined with the regular PNG suffix set. Same grounding model as
core/decoder.py's rule tables — a human-encoded rule table at design time, cited per claim at runtime
(D-011). Only listed lemmas match; anything else still returns an honest NoEntry.

Emits the FST's own tag shape (`past=<marker>`, `<png>=<suffix>`) so decoder/grammar consume it unchanged.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Optional

from tamil import utf8

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.schema import MorphAnalysis, SourceRef

_PULLI = "்"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def join_surface(stem: str, suffix: str) -> str:
    """Join a stem to a suffix in Tamil script. A stem-final mei plus a suffix-initial உயிர் form ONE
    உயிர்மெய் glyph — போன் + ஆன் → போனான், not 'போன்ஆன்'. Plain concatenation is wrong here."""
    if stem.endswith(_PULLI) and suffix and suffix[0] in utf8.uyir_letters:
        return stem[:-2] + utf8.joinMeiUyir(stem[-2:], suffix[0]) + suffix[1:]
    return stem + suffix


class VerbParadigmAdapter(SourceAdapter):
    """Anchor-tier fallback for verbs the FST lexicon does not cover."""

    name = "thamizh-mcp curated verb paradigms"
    tier = "anchor"

    def __init__(self, table_path: Optional[Path] = None):
        self.table_path = Path(table_path or config.VERB_PARADIGMS_FILE)
        self._png: dict[str, str] = {}
        self._paradigms: dict[str, list[dict]] = {}   # tense code (past/pres/fut) → entries
        self._excluded: dict[str, list[str]] = {}     # tense → PNG codes that don't apply
        self._verified = ""
        try:
            data = json.loads(self.table_path.read_text("utf-8"))
            self._png = {k: _nfc(v) for k, v in data.get("png_suffixes", {}).items()}
            self._excluded = data.get("png_excluded_by_tense", {})
            self._paradigms = {
                tense: [{**e, "stem": _nfc(e["stem"]), "lemma": _nfc(e["lemma"])} for e in entries]
                for tense, entries in data.get("paradigms", {}).items()
            }
            self._verified = data.get("verified_date", "")
        except (OSError, ValueError, KeyError):
            pass   # table missing/corrupt → adapter simply never matches (honest NoEntry)

    def _source(self) -> SourceRef:
        return SourceRef(name=self.name, tier="anchor",
                         ref="data/verb_paradigms.json — hand-verified irregular past stems",
                         retrieved=self._verified or "curated")

    def analyses_for(self, word: str) -> list[MorphAnalysis]:
        """Generate each listed stem × PNG suffix surface form (per tense) and match the word against
        it. Generation (not prefix-matching) is what makes the Tamil mei+uyir join correct.
        Tags mirror ThamizhiMorph's own convention (past=/pres=/fut= + marker), so the decoder and
        grammar layers consume this identically to real FST output."""
        w = _nfc(word)
        out: list[MorphAnalysis] = []
        for tense, entries in self._paradigms.items():
            skip = set(self._excluded.get(tense, ()))
            for entry in sorted(entries, key=lambda e: -len(e["stem"])):
                matched = False
                for png, suffix in self._png.items():
                    if png in skip:
                        continue
                    if join_surface(entry["stem"], suffix) == w:
                        out.append(MorphAnalysis(
                            lemma=entry["lemma"], pos="verb",
                            tags=["fin", "sim", f"{tense}={entry['marker']}", f"{png}={suffix}"]))
                        matched = True
                if matched:
                    break   # longest stem wins within a tense — skip shorter accidental stems
        return out

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        analyses = self.analyses_for(normalized_word)
        if not analyses:
            return NoEntry(source=self.name, reason="no_entry",
                           note="not a listed irregular verb form (curated table is deliberately "
                                "closed — no guessing)")
        return AdapterResult(fields={"all_analyses": analyses},
                             sources=[self._source()], tier="anchor")
