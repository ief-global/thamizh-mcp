"""Native-equivalent source (objective 5) — Sanskrit-To-Pure-Tamil (S2PT) தனித்தமிழ் lists.

EVOLVING tier, but LOCAL data (vendored CSVs, no network): four attributable sub-lists
(viruba, tamilchol, thamizhdna-org, tamilmandram) mapping a **வடசொல்** (Sanskrit-derived) word → its
attested pure-Tamil equivalents. combined_all.csv is their dedup merge; we load the sub-lists
so every candidate cites the actual list(s) that attest it.

HARD RULE (blueprint §4, kalaichol docstring): every candidate carries its attestation source;
an equivalent we cannot attest in a named list never surfaces. No entry → NoEntry, never an
invention. The TVA govt கலைச்சொல் anchor glossary is a separate (network-snapshot) source —
see adapters/kalaichol.py.

NAME (corrected 2026-08-08): upstream is `narVidhai/Sanskrit-To-Pure-Tamil-Dictionary`, README
titled "வடசொல் to தமிழ்". We had called it "Indic-To-Pure-Tamil"; GitHub redirects the old path, so
the stale name went unnoticed. The scope is Sanskrit specifically — which is why membership is an
origin signal at all (see core/classifier.py).

⚠️ PROVISIONAL source. Upstream has **no LICENCE file** and its last commit was 2020; its own
upstreams are four scraped community sites with unstated terms. Earlier docs claimed MIT — no basis
was found (D-017). It stays because it is attested and unique at its job, but its claims are
confidence-capped and its evidence string says what it is. Pin: data/PINS.md.
"""
from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.schema import SourceRef

_SOURCE_NAME = "Sanskrit-To-Pure-Tamil (community தனித்தமிழ் lists)"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def _sublist_label(filename: str) -> str:
    """'viruba.csv' → 'viruba' — the human name used in per-candidate citations."""
    return Path(filename).stem


def load_index(data_dir: Path, sublists: tuple[str, ...]) -> dict[str, dict[str, list[str]]]:
    """Build {normalized INDIC word → {equivalent → [attesting sub-lists]}} from the CSVs.

    Each row is 'INDIC,TAMIL' where TAMIL is a comma-separated list of equivalents. Values are
    NFC-normalized and de-duplicated; the attesting sub-lists are unioned across files so a word
    present in several lists yields one candidate citing all of them. Missing files are skipped
    (a partial vendored set is still usable), never fatal.
    """
    index: dict[str, dict[str, list[str]]] = {}
    for filename in sublists:
        path = data_dir / filename
        if not path.exists():
            continue
        label = _sublist_label(filename)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                indic = _nfc(row.get("INDIC", ""))
                raw = row.get("TAMIL", "") or ""
                if not indic or not raw:
                    continue
                bucket = index.setdefault(indic, {})
                for equivalent in (_nfc(part) for part in raw.split(",")):
                    if not equivalent:
                        continue
                    attesting = bucket.setdefault(equivalent, [])
                    if label not in attesting:
                        attesting.append(label)
    return index


class SanskritToPureTamilAdapter(SourceAdapter):
    """Look up a வடசொல் word's attested pure-Tamil equivalents in the S2PT lists."""

    name = _SOURCE_NAME
    tier = "evolving"

    def __init__(self, data_dir: Path | None = None, sublists: tuple[str, ...] | None = None):
        self.data_dir = Path(data_dir or config.EQUIVALENTS_DIR)
        self.sublists = sublists or config.S2PT_SUBLISTS
        self._index = load_index(self.data_dir, self.sublists)

    def _source_ref(self) -> SourceRef:
        return SourceRef(name=self.name, tier="evolving",
                         ref="https://github.com/narVidhai/Sanskrit-To-Pure-Tamil-Dictionary",
                         retrieved=config.S2PT_PIN)

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        # In-memory, deterministic, no I/O — the CSVs were indexed once at construction.
        entry = self._index.get(_nfc(normalized_word))
        if not entry:
            return NoEntry(source=self.name, reason="no_entry",
                           note="no attested pure-Tamil equivalent in the S2PT community lists")
        # More attesting lists first, then alphabetical — deterministic candidate ordering.
        candidates = []
        for equivalent, attesting in sorted(entry.items(),
                                            key=lambda kv: (-len(kv[1]), kv[0])):
            candidates.append({
                "equivalent": equivalent,
                "source": self.name,
                "tier": "evolving",
                "attestation": "attested",
                "citation": "attested in: " + ", ".join(attesting),
            })
        return AdapterResult(fields={"candidates": candidates},
                             sources=[self._source_ref()], tier="evolving")
