#!/usr/bin/env python3
"""Presentation demo — human-readable Tamil word analysis for a live audience.

    uv run python scripts/demo.py மரத்தில்
    uv run python scripts/demo.py வந்தான் வருகிறான்        # several words in one go
    uv run python scripts/demo.py புத்தகம் --meaning        # also fetch meaning (needs network)

Unlike scripts/analyze.py (raw JSON), this prints a clean block sized for a projector. Network is
OFF by default so a demo can never hang on stage — add --meaning to enable the live lookup.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.core import engine          # noqa: E402
from thamizh_mcp.normalize import normalize   # noqa: E402

W = 62
BAR = "═" * W


def line(label: str, value: str) -> None:
    if value:
        print(f"  {label:<24}{value}")


async def show(word: str, with_meaning: bool) -> None:
    try:
        norm = normalize(word)
    except ValueError as exc:
        print(f"\n  ⚠  {exc}\n")
        return

    include = ["origin", "root", "formation", "grammar", "native_equivalent"]
    if with_meaning:
        include.append("meaning")
    a = await engine.analyze_word(word, norm, include=include, allow_enrichment=with_meaning)

    print(f"\n{BAR}\n   {word}\n{BAR}")

    line("வேர்ச்சொல் (root)", a.lemma or "—")
    line("சொல் வகை (class)", a.grammar.word_class if a.grammar.word_class != "unknown" else "")
    if a.grammar.case:
        line("வேற்றுமை (case)", a.grammar.case.name or "")
    line("காலம் (tense)", a.grammar.tense or "")
    line("முற்று (person)", a.grammar.person_number_gender or "")

    if a.formation.components:
        print(f"\n  பகுபத உறுப்பு  [{a.formation.word_type}]")
        for c in a.formation.components:
            role = f"   — {c.role}" if c.role else ""
            print(f"     {c.part:<10} {c.form}{role}")
    if a.formation.sandhi:
        print("\n  புணர்ச்சி / சந்தி")
        for s in a.formation.sandhi:
            print(f"     {s.type}: {s.detail}")

    print()
    line("பிறப்பு (origin)", f"{a.origin.class_}"
         + (f"   (confidence {a.origin.confidence})" if a.origin.confidence else ""))
    if a.origin.evidence:
        for chunk in _wrap(a.origin.evidence, W - 8):
            print(f"        {chunk}")
    # A homograph is one form carrying more than one word: the Tamil sense leads above, and every
    # sense — the borrowed one included — is listed here rather than collapsed away (D-015).
    if a.origin.senses:
        print("\n  சொல்லுக்குச் சொல் (origin by sense)")
        for sn in a.origin.senses:
            print(f"     {sn.sense or '—'}: {sn.class_} — {sn.evidence}")

    ne = a.native_equivalent
    if ne.candidates:
        print("\n  தனித்தமிழ் நிகரானவை (attested equivalents)")
        for c in ne.candidates[:4]:
            print(f"     {c.equivalent:<16} [{c.citation or c.source}]")

    if with_meaning and a.meaning.senses:
        print("\n  பொருள் (meaning)")
        for s in a.meaning.senses[:2]:
            for chunk in _wrap(s.gloss_ta or s.gloss_en or "", W - 8):
                print(f"     {chunk}")

    if a.gaps:
        print("\n  ⓘ honest gaps (no source could ground these):")
        print("     " + ", ".join(g.field for g in a.gaps))

    names = list(dict.fromkeys(s.name for s in a.sources))
    if names:
        print("\n  சான்று (sources)")
        for chunk in _wrap(" · ".join(names), W - 8):
            print(f"     {chunk}")
    print()


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Thamizh MCP — live demo view")
    ap.add_argument("words", nargs="+", help="Tamil word(s) in Tamil script")
    ap.add_argument("--meaning", action="store_true",
                    help="also fetch meaning (live network lookup; off by default)")
    args = ap.parse_args()
    for w in args.words:
        asyncio.run(show(w, args.meaning))


if __name__ == "__main__":
    main()
