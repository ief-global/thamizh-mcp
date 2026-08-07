# THAMIZH MCP

[![tests](https://github.com/ief-global/thamizh-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/ief-global/thamizh-mcp/actions/workflows/tests.yml)

Source-grounded Tamil word-grammar (**சொல் இலக்கணம்**) analysis, exposed as an MCP server.

Give it one Tamil word and it returns: **origin**
(இயற்சொல் / திரிசொல் / திசைச்சொல் / வடசொல் / loanword), **root + meaning**, **formation**
(பகுபத உறுப்பு, புணர்ச்சி), **grammar** (Tholkappiyam-first), and — for borrowings only —
**attested** native equivalents.

Three rules the project does not bend:

- **Tholkappiyam-first.** Tholkappiyam is the primary authority; Nannūl is the fallback. Both are
  pinned as version-locked texts and cited down to the **நூற்பா**.
- **Honesty over guessing.** An unknown returns an explicit *gap*, never a plausible-looking answer.
- **Self-enriching, not a static dictionary.** Coverage grows from live sources, cached per claim
  with its provenance.

Apache-2.0, built by the nonprofit [International Educational Foundation](https://ief-global.org).
Design, decisions and roadmap live in the companion repo
[`ief-global/thamizh-mcp-design`](https://github.com/ief-global/thamizh-mcp-design).

## Status

**Working server, in active development.** Nine MCP tools over one engine, plus REST and CLI heads.
171 tests pass.

| | |
|---|---|
| MCP tools | `analyze_word` · `classify_origin` · `get_root` · `get_meaning` · `suggest_native_equivalent` · `enrich_word` · `explain_formation` · `explain_grammar` · `refresh_sources` |
| Heads | MCP (stdio) · REST/web (FastAPI) · CLI |
| Anchors | ThamizhiMorph FST (foma) · curated verb paradigms · pinned Tholkappiyam + Nannūl |
| Evolving | Tamil Wiktionary (meanings) · English Wiktionary (etymology → source language) |
| Store | zero-config SQLite, per-claim provenance |

Not done yet: non-finite verb forms and a full புணர்ச்சி sandhi engine. See the design repo's roadmap.

**Origin accuracy** on a 108-word everyday sweep: 82 correct, 23 honest `unknown`, 1 wrong. Origin
resolves the source language from etymology evidence rather than guessing it from spelling — Grantha
letters mark a non-native *sound*, not a source language, so ஜன்னல் is Portuguese and பஸ் is English,
not வடசொல். A headword whose senses differ in origin (கால் = leg, inherited / time, Sanskrit) is
reported as ambiguous rather than resolved to one.

## Install

```bash
uv sync                 # core deps
uv sync --extra web     # + FastAPI/uvicorn for the web head
```

### System dependency: foma / flookup (NOT pip-installable)

ThamizhiMorph is a foma FST queried through the native `flookup` binary.

```bash
sudo apt install foma          # Debian/Ubuntu
brew install foma              # macOS
```

⚠️ Install **`foma`**, not `foma-bin` — on current Debian/Ubuntu `foma-bin` is an empty transitional
package and leaves you with no working FST. On Windows use WSL.

FST models: [sarves/thamizhi-morph](https://github.com/sarves/thamizhi-morph) (Apache-2.0), pinned
in `data/PINS.md`.

## Run

```bash
uv run thamizh-mcp                      # MCP server, stdio transport
uv run thamizh-web                      # web + REST head on :8080
uv run python scripts/demo.py மரத்தில்   # readable CLI view
uv run pytest                           # 171 tests
```

Register with Claude Code:

```bash
claude mcp add thamizh -- uv --directory /path/to/thamizh-mcp run thamizh-mcp
```

**A note on terminals:** most terminals do not shape Tamil script correctly — vowel signs detach or
reorder, so CLI output can look wrong when the data is right. The web head exists for this reason;
use a browser to read Tamil output.

## Grounding — how a claim earns its citation

Every claim carries its source, tier and retrieval date. Grammar claims go further: the classical
rule inventories are encoded as **cited JSON tables** in `data/grammar/`, so a Tamil scholar can
audit the linguistics as data without reading a line of Python.

```
data/classical/    Tholkappiyam + Nannūl, version-locked, verse-addressable
data/grammar/      rule tables — இடைநிலை, விகுதி, சாரியை, வேற்றுமை உருபு, விகாரம்
```

Each rule table names its governing authority in a `source_priority` block and cites the நூற்பா that
settles it. `tests/test_citations.py` enforces that every cited verse resolves in the pinned texts.

⚠️ **Citing a நூற்பா:** Tholkappiyam verse numbers **restart in every இயல்**, so a bare number is
ambiguous — always qualify it (`தொல்காப்பியம், சொல்லதிகாரம், வேற்றுமையியல், நூற்பா 3`). Nannūl
numbering is continuous 1–462, so a bare number is fine there.

Rebuild the classical texts from source, or check for upstream drift:

```bash
uv run python scripts/build_classical.py            # rebuild
uv run python scripts/build_classical.py --verify   # report drift, write nothing
```

## Licensing

Apache-2.0 for the code and our own rule tables. This is a **mixed-licence product** — third-party
data keeps its own licence and is classified per source in [`LICENSING.md`](LICENSING.md). In short:

| Source | Licence | Obligation |
|---|---|---|
| ThamizhiMorph FSTs | Apache-2.0 | attribution + academic citation |
| Indic-To-Pure-Tamil lists | MIT | attribution |
| Tamil Wiktionary meanings | CC BY-SA | attribution; **stays** CC BY-SA, never relicensed |
| Tholkappiyam / Nannūl etexts | Project Madurai | keep their header intact wherever the text travels |

## Credits

**ThamizhiMorph** — Sarveswaran, K., Dias, G., Butt, M. "ThamizhiMorph: A morphological parser for
the Tamil language", *Machine Translation* (Springer) 2021. DOI
[10.1007/s10590-021-09261-5](https://doi.org/10.1007/s10590-021-09261-5). Apache-2.0.

**Project Madurai** — the pinned Tholkappiyam and Nannūl etexts come from Project Madurai, an open,
voluntary, worldwide initiative devoted to preparing electronic texts of Tamil literary works and
distributing them free on the Internet. The community's work validating these texts is what makes
verse-level citation possible here.

> © Project Madurai 1999-2001. Details at [projectmadurai.org](http://www.projectmadurai.org).
> You are welcome to freely distribute this file, provided this header page is kept intact.

Tholkappiyam etext: Dr. K. Kalyanasundaram; proof-reading N. D. Logasundaram. Nannūl etext:
Dr. Thomas Malten (Univ. of Köln), after the edition of Mani Thirunavukkarasu Mudaliar (1926);
proof-reading N. D. Logasundaram.

**Tamil Virtual Academy** (Government of Tamil Nadu) — degree-level accredited course material,
used to verify the rule tables against the classical sources.
