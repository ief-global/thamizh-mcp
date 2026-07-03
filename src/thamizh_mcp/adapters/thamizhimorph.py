"""ThamizhiMorph FST (ANCHOR) — lemma, POS, inflection tags; sandhi-aware. Stateless: no cache.

flookup subprocess pushed off the event loop via anyio.to_thread.run_sync, with a timeout —
a hung FST must produce an honest NoEntry, never a stalled server. Guesser FSTs are excluded
(config.PRIMARY_FSTS): a guessed analysis is an unsourced guess.
Pin + citation: data/PINS.md.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import anyio

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.schema import MorphAnalysis, SourceRef


def parse_flookup(output: str) -> list[MorphAnalysis]:
    """'மரத்தில்\\tமரம்+noun+infInc+loc' lines → MorphAnalysis list; '+?' means no analysis."""
    analyses: list[MorphAnalysis] = []
    for line in output.splitlines():
        if "\t" not in line:
            continue
        _, analysis = line.split("\t", 1)
        analysis = analysis.strip()
        if not analysis or analysis == "+?" or "+" not in analysis:
            continue
        lemma, *tags = analysis.split("+")
        if not lemma or not tags:
            continue
        analyses.append(MorphAnalysis(lemma=lemma, pos=tags[0], tags=tags[1:]))
    return analyses


class ThamizhiMorphAdapter(SourceAdapter):
    name = "ThamizhiMorph"
    tier = "anchor"

    def __init__(self, flookup: str | None = None, fst_dir: Path | None = None,
                 fsts: tuple[str, ...] | None = None, timeout_s: float | None = None):
        self.flookup = flookup or config.FLOOKUP
        self.fst_dir = Path(fst_dir or config.FST_DIR)
        self.fsts = fsts or config.PRIMARY_FSTS
        self.timeout_s = timeout_s or config.FLOOKUP_TIMEOUT_S

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if config.FLOOKUP_LIB:
            env["LD_LIBRARY_PATH"] = config.FLOOKUP_LIB + ":" + env.get("LD_LIBRARY_PATH", "")
        return env

    def _run_all(self, word: str) -> list[MorphAnalysis] | str:
        """Sync worker: query each primary FST; returns analyses or an error reason string."""
        analyses: list[MorphAnalysis] = []
        seen: set[tuple] = set()
        for fst in self.fsts:
            fst_path = self.fst_dir / fst
            if not fst_path.exists():
                continue
            try:
                proc = subprocess.run(
                    [self.flookup, str(fst_path)], input=word + "\n",
                    capture_output=True, text=True, timeout=self.timeout_s, env=self._env())
            except subprocess.TimeoutExpired:
                return f"timeout after {self.timeout_s}s on {fst}"
            if proc.returncode != 0:
                return f"flookup failed on {fst}: {proc.stderr.strip()[:200]}"
            for a in parse_flookup(proc.stdout):
                key = (a.lemma, a.pos, tuple(a.tags))
                if key not in seen:
                    seen.add(key)
                    analyses.append(a)
        return analyses

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        if not self.flookup or not self.fst_dir.is_dir():
            return NoEntry(source=self.name, reason="unavailable",
                           note="flookup binary or FST models not found — see data/PINS.md setup")
        result = await anyio.to_thread.run_sync(self._run_all, normalized_word)
        if isinstance(result, str):
            return NoEntry(source=self.name, reason="timeout" if "timeout" in result else "error", note=result)
        if not result:
            return NoEntry(source=self.name, reason="no_entry",
                           note="no analysis in primary FSTs (guessers deliberately excluded)")
        return AdapterResult(
            fields={"all_analyses": result},
            sources=[SourceRef(name=self.name, tier="anchor",
                               ref="https://github.com/sarves/thamizhi-morph",
                               retrieved=config.THAMIZHIMORPH_PIN)],
            tier="anchor")
