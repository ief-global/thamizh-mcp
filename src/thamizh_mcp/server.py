"""THAMIZH MCP server — thin MCP head over the plain-Python engine (blueprint §8).

Keep this layer thin: tools validate input, call thamizh_mcp.core.engine, serialize output.
All linguistic logic lives in core/; other heads (FastAPI REST, CLI) reuse the same engine.
"""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from thamizh_mcp.core import engine
from thamizh_mcp.normalize import normalize

mcp = FastMCP("thamizh_mcp")

_SECTIONS = ("origin", "root", "meaning", "formation", "grammar", "native_equivalent")


class AnalyzeWordInput(BaseModel):
    """Input for analyze_word."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    word: str = Field(..., min_length=1, max_length=100,
                      description="One Tamil word in Tamil script, e.g. மரத்தில் or கம்ப்யூட்டர்.")
    include: Optional[list[str]] = Field(
        default=None,
        description=f"Sections to compute (default: all). Subset of {list(_SECTIONS)}.")
    allow_enrichment: bool = Field(
        default=True,
        description="Permit evolving-tier internet pulls (Tamil Wiktionary etc.) on anchor miss; "
                    "results are cached with provenance.")


@mcp.tool(
    name="analyze_word",
    annotations={
        "title": "Analyze a Tamil word (சொல் இலக்கணம்)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def analyze_word(params: AnalyzeWordInput) -> str:
    """Full grounded analysis of one Tamil word: origin (இயற்சொல்/திரிசொல்/திசைச்சொல்/வடசொல்/loan),
    root+meaning, formation (பகுபத உறுப்பு, புணர்ச்சி), grammar (Tholkappiyam-first), and — only
    for non-native words — ATTESTED native Tamil equivalents.

    Every field carries provenance (source, tier, authority, retrieval date). Fields no source
    can ground are returned in `gaps` — never invented. Ambiguous morphology returns ALL analyses.

    Args:
        params: word (required, Tamil script), include (optional section filter),
                allow_enrichment (default true).

    Returns:
        str: JSON WordAnalysis object (see schemas/word_analysis_schema.json). SCAFFOLD STATUS:
        currently returns the schema-valid all-gaps object — grounding sources land in Phase 1/3.

    Error handling:
        Non-Tamil / multi-word / empty input returns "Error: ..." with what to fix.
    """
    try:
        normalized = normalize(params.word)
    except ValueError as exc:
        return f"Error: {exc}"
    include = params.include
    if include is not None:
        bad = sorted(set(include) - set(_SECTIONS))
        if bad:
            return f"Error: unknown include section(s) {bad}. Valid: {list(_SECTIONS)}."
    analysis = await engine.analyze_word(
        params.word, normalized, include=include, allow_enrichment=params.allow_enrichment
    )
    return analysis.to_json()


def main() -> None:
    """stdio transport (local v1); streamable HTTP arrives with the Cloud Run deploy (Phase 3+)."""
    mcp.run()


if __name__ == "__main__":
    main()
