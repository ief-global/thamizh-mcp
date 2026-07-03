#!/usr/bin/env python3
"""Quick demo CLI: analyze one Tamil word without an MCP client.

  uv run python scripts/analyze.py மரத்தில்
  uv run python scripts/analyze.py புத்தகம் --include meaning     # live Wiktionary + cache write-back
  uv run python scripts/analyze.py புத்தகம் --no-enrich           # cache/anchors only
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.core.engine import analyze_word
from thamizh_mcp.normalize import normalize


def main() -> None:
    ap = argparse.ArgumentParser(description="THAMIZH MCP — one-word analysis demo")
    ap.add_argument("word", help="One Tamil word, e.g. மரத்தில்")
    ap.add_argument("--include", nargs="*", default=None,
                    help="origin root meaning formation grammar native_equivalent")
    ap.add_argument("--no-enrich", action="store_true", help="disable evolving-tier pulls")
    args = ap.parse_args()
    try:
        norm = normalize(args.word)
    except ValueError as exc:
        sys.exit(f"Error: {exc}")
    a = asyncio.run(analyze_word(args.word, norm, include=args.include,
                                 allow_enrichment=not args.no_enrich))
    print(a.to_json())


if __name__ == "__main__":
    main()
