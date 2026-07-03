"""Native-equivalent sources (objective 5): TVA/govt கலைச்சொல் glossaries (ANCHOR) +
Indic-To-Pure-Tamil / தனித்தமிழ் lists (EVOLVING). HARD RULE: every candidate carries its
attestation source; unsourced candidates are dropped in merge; purist coinages marked
attestation="proposed". No attested equivalent → empty candidates + note, never an invention."""
from __future__ import annotations

from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter


class KalaicholAdapter(SourceAdapter):
    name = "TVA கலைச்சொல்"
    tier = "anchor"

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        raise NotImplementedError("Wired in Phase 1 — blueprint §4 (native_equivalent row)")
