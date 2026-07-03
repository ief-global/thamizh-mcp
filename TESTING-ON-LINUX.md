# Testing thamizh-mcp on the Ubuntu server (Claude Code)

Why this route: the Cowork sandbox blocks ta.wiktionary.org / dsal.uchicago.edu / tamilvu.org
(the "all packages" egress setting opens package registries like PyPI only). The Linux server has
open network + real foma, so live evolving-source tests and the lexicon-snapshot job belong there.

## 1. Get the repo onto the server
Copy the whole `thamizh-mcp/` folder from `E:\COWORK\PROJECTS\THAMIZH MCP\` (scp, WinSCP, or a share).
`data/` travels with it — FSTs and the I2PT CSVs are already pinned inside (see `data/PINS.md`).
Then on the server (recommended, matches the distribution roadmap):
```bash
cd ~/thamizh-mcp && git init && git add -A && git commit -m "scaffold + phase 1"
```

## 2. One-time setup
```bash
sudo apt update && sudo apt install -y foma            # real flookup on PATH (NOT foma-bin — that deb is empty)
curl -LsSf https://astral.sh/uv/install.sh | sh        # uv
cd ~/thamizh-mcp && uv sync --extra dev
which flookup && echo "மரம்" | flookup data/fst/noun.fst   # expect: மரம்	மரம்+noun+nom
```
No env vars needed: `config.py` auto-detects flookup on PATH and `data/fst/`.

## 3. Test ladder (run in order)
```bash
uv run pytest -v                       # expect 22 passed, 0 skipped (live FST tests included)
uv run python scripts/analyze.py மரத்தில்            # lemma மரம், both loc|soc kept, Tholkappiyam cites
uv run python scripts/analyze.py புத்தகம் --include meaning   # FIRST LIVE Wiktionary pull
uv run python scripts/analyze.py புத்தகம் --include meaning   # again → must serve from cache
sqlite3 data/knowledge.sqlite3 'select word,field,source,tier,retrieved from claims;'  # write-back proof
```
What to verify on the live pull: senses carry `citation` URLs; `sources[].retrieved` is today's date;
a nonsense/rare word returns a meaning **gap**, not a guess. That's the Phase 4 honesty behaviour.

## 4. Register with Claude Code as a real MCP server
```bash
claude mcp add thamizh -- uv --directory ~/thamizh-mcp run thamizh-mcp
claude mcp list                        # should show thamizh (stdio)
```
Then inside a Claude Code session try: "Use analyze_word on மரத்தில் and show me the provenance."
Optional deeper poke: `npx @modelcontextprotocol/inspector uv run thamizh-mcp` (needs Node).

## 5. Jobs that NEED this server (network-open)
1. **Madras Tamil Lexicon snapshot** — source the digitized data, pin it in `data/` (anchor
   discipline; blueprint §10 open decision). Ask Claude Code there to research + fetch it.
2. **TVA / govt கலைச்சொல் glossaries** — same: snapshot + pin.
3. Live Wiktionary adapter shakedown across the 7 fixture words (`tests/fixtures/words.json`).

## Gotchas
- Keep edits flowing through git once initialized — the E:\ copy stays the design/docs home,
  the server copy becomes the build home; don't let them drift (push to a private GitHub repo).
- `data/knowledge.sqlite3` is gitignored — it's the self-enriching cache, machine-local by design.
- Wiktionary licence (CC BY-SA) caching question is still open — fine for private testing,
  resolve before any public release (blueprint §10).
