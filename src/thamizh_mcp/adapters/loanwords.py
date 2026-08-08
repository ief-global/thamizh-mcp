"""English-loanword evidence (ANCHOR, pinned artifact) — names the source of a modern borrowing.

This closes the last unprincipled branch in origin classification. Orthography can prove a word is
NOT native (Grantha letters, a முதல்/இறுதி எழுத்து violation) but can never say WHICH language it
came from, and en.wiktionary has no page for many everyday modern loans (பட்டன், ஸ்கூல், ஹோட்டல்).
Those fell through to `unknown`, or worse, to native-by-default.

The evidence is a human-annotated romanization lexicon: **Google Dakshina** records how Tamil
speakers actually write Tamil words in Latin script, and for a borrowing that spelling is very often
the English source word itself — ஸ்கூல் is attested as "school" by four annotators. A Tamil word
whose attested romanization is a real English word is positive evidence of an English source. That
is a fact about attested usage, not a phonetic guess.

TIER. `anchor`: a version-pinned artifact built once by `scripts/build_english_loans.py` and
committed, so lookups are offline, deterministic, and reviewable in a diff. Confidence is not
capped the way an evolving source is — but see the gate below, which is what earns that.

⚠️ THE GATE IS LOAD-BEARING — DO NOT LOOK A WORD UP WITHOUT IT. This adapter answers "which
language", never "is it borrowed". `core/classifier.py` consults it ONLY inside a branch where
orthography has already proved non-nativeness. Measured ungated on the 108-word sweep, the method
fires on 15 of 56 native words — கால் → "call", கை → "kai", தீ → "thee", and கார் → "car"(4), the
word Saran ruled must lead native (2026-08-05). The artifact itself only contains words that pass
the gate, so a native word cannot be looked up even by mistake; the gate in the classifier is the
second lock, not the only one.

LICENCE. The artifact is **CC BY-SA 4.0**, inherited from Dakshina — NOT Apache-2.0, and never
relicensed. Attribution travels with every claim (D-012's mixed-licence, per-source model). Pins and
checksums: `data/PINS.md`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.schema import SourceRef

_SOURCE_NAME = "Google Dakshina (attested romanizations)"
_CITATION = ("Roark et al. 2020, Processing South Asian Languages Written in the Latin Script: "
             "the Dakshina Dataset (LREC 2020) — CC BY-SA 4.0")


def load_loans(path: Optional[Path] = None) -> dict[str, tuple[str, int]]:
    """The pinned artifact as {tamil_word: (english_word, attestation_count)}.

    A missing or malformed artifact is an empty mapping, never an exception: the classifier simply
    loses one signal and falls back to the orthographic rules, which is the honest degradation.
    """
    p = path or config.ENGLISH_LOANS_FILE
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {w: (v[0], int(v[1])) for w, v in raw.get("loans", {}).items()
                if isinstance(v, list) and len(v) >= 2}
    except Exception:
        return {}


class EnglishLoanwordAdapter(SourceAdapter):
    """Attested-English-romanization evidence for one Tamil word. Offline; never raises."""

    name = _SOURCE_NAME
    tier = "anchor"

    def __init__(self, path: Optional[Path] = None):
        self._path = path
        self._loans: Optional[dict[str, tuple[str, int]]] = None

    @property
    def loans(self) -> dict[str, tuple[str, int]]:
        if self._loans is None:                      # lazy: cost nothing when the signal is unused
            self._loans = load_loans(self._path)
        return self._loans

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        hit = self.loans.get(normalized_word)
        if hit is None:
            return NoEntry(source=self.name, reason="no_entry",
                           note="no attested English romanization for this word")
        english, count = hit
        return AdapterResult(
            fields={"english_loan": {"english": english, "attestations": count,
                                     "citation": _CITATION}},
            sources=[SourceRef(name=self.name, tier="anchor", ref=_CITATION,
                               retrieved=config.ENGLISH_LOANS_PIN)],
            tier="anchor")
