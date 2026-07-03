# THAMIZH MCP

Source-grounded Tamil word-grammar (சொல் இலக்கணம்) analysis, exposed as an MCP server.
Given one Tamil word: origin (இயற்சொல்/திரிசொல்/திசைச்சொல்/வடசொல்/loan), root + meaning,
formation (பகுபத உறுப்பு, புணர்ச்சி), grammar (Tholkappiyam-first), and — for borrowings —
attested native equivalents only. Honest gaps, provenance on every claim, self-enriching
knowledge store. Design: `../THAMIZH-MCP-blueprint.md`.

## Status
Scaffold. `analyze_word` returns a schema-valid, all-gaps object. Grounding sources are wired in
Phase 1/3 (see blueprint §11).

## Install (uv)
```
uv sync                 # core deps
uv sync --extra full    # + stanza (contextual POS; not needed for single-word v1)
```

## System dependency: foma / flookup (NOT pip-installable)
ThamizhiMorph is a foma FST queried via the native `flookup` binary:
- Debian/Ubuntu: `apt install foma-bin`  ·  macOS: `brew install foma`  ·  Windows: use WSL or the foma release binaries.
FST models: https://github.com/sarves/thamizhi-morph (Apache-2.0).

## Run
```
uv run thamizh-mcp          # stdio transport
uv run pytest               # tests
```

## Credits
ThamizhiMorph: Sarveswaran, K., Dias, G., Butt, M. "ThamizhiMorph: A morphological parser for the
Tamil language", Machine Translation (Springer) 2021. DOI 10.1007/s10590-021-09261-5. Apache-2.0.
