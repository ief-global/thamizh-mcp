"""Madras University Tamil Lexicon via DSAL (ANCHOR, pinned Sep-2023) — meaning + etymology notes.
No official API: Phase 1 decides scrape-at-query vs offline digitized copy (blueprint §10)."""
from __future__ import annotations

from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter


class MadrasLexiconAdapter(SourceAdapter):
    name = "Madras Tamil Lexicon"
    tier = "anchor"

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        raise NotImplementedError("Wired in Phase 1 — blueprint §4 (meaning row) + §10 access question")
