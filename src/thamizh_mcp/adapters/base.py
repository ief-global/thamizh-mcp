"""Uniform adapter interface: normalized word in → fields + provenance + tier out (blueprint §8).

Every grounding source hides behind this. An adapter NEVER guesses: no entry → NoEntry, and the
merge layer records the gap. Timeouts are adapter-level and produce NoEntry(reason="timeout")."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from thamizh_mcp.schema import SourceRef, Tier


@dataclass
class AdapterResult:
    """Fields this source can fill for the word, each claim provenance-tagged."""
    fields: dict[str, Any]
    sources: list[SourceRef]
    tier: Tier


@dataclass
class NoEntry:
    """Honest miss: the source has nothing for this word (or timed out)."""
    source: str
    reason: str = "no_entry"
    note: str = ""


class SourceAdapter(ABC):
    """One grounding source. name/tier are class-level metadata for provenance."""
    name: str
    tier: Tier

    @abstractmethod
    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        """Blocking work (subprocess/sync lib) must be pushed off the event loop
        (anyio.to_thread.run_sync); network via httpx.AsyncClient; ALWAYS under a timeout."""
