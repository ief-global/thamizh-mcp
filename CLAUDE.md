# CLAUDE.md — Thamizh MCP (developer context for Claude Code)

Thamizh MCP is a Model Context Protocol server for Tamil word-grammar
(சொல் இலக்கணம்) analysis. It grounds every answer in authentic Tamil sources
(Tholkappiyam-first) and self-enriches from evolving internet Tamil data instead
of a hand-maintained dictionary. Public repo: github.com/ief-admin/thamizh-mcp
(Apache-2.0, nonprofit org IEF).

## Machine roles
- **minnaham (this Ubuntu box)** = build + live-test home. Real `foma` on PATH,
  open network (ta.wiktionary / dsal / tamilvu reachable), repo cloned on `develop`.
  All test runs, live enrichment pulls, and git happen here.
- **Windows / Cowork** = design + docs home (blueprint, memory, planning). Its
  sandbox blocks the Tamil sources and its E:\ mount corrupts git — never build there.

## Git identity — use everywhere, no exceptions
Commit as **Saran Saravanan <saravanan3@duck.com>**, GitHub **ssaravanan3**.
`git config --global` is already set to this on this box. NEVER commit under the
legacy `asaravanan75@gmail.com` / `asaravanan75-eng`. Verify: `git log --format='%an <%ae>' -1`.

## Branch workflow
`main` = stable, **protected** (PR-only, no force-push, no delete). `develop` =
integration. Loop: work on `develop` here → push → open PR `develop → main` at
milestones. After any history rewrite, other clones must `git reset --hard origin/main`
(not merge/rebase).

## Current state (2026-08-05) — 171 tests pass (169 without live foma)

**Everything below is live and merged to `main`.** Nine MCP tools + web/REST + CLI over ONE engine
(blueprint §8 — the web head needed zero engine changes, which validated that design).

| Layer | What |
|---|---|
| Anchors | ThamizhiMorph FST via `flookup` · curated verb paradigms (`data/verb_paradigms.json`) · pinned Tholkappiyam + Nannūl (`data/classical/`) · cited grammar tables (`data/grammar/`) |
| Evolving | ta.wiktionary (meanings) · **en.wiktionary (etymology → source language)** · I2PT (native equivalents) |
| Store | zero-config SQLite, per-claim provenance + `transactions` gold log (on by default) |

**Tools:** `analyze_word` `classify_origin` `get_root` `get_meaning` `suggest_native_equivalent`
`enrich_word` `explain_formation` `explain_grammar` `refresh_sources`. Only optional
`validate_pure_tamil`/`generate_forms`/`transliterate` remain from blueprint §6.

### Measured quality (108-word everyday sweep, 2026-08-05)

| | result |
|---|---|
| **Origin** | 82 correct · 23 honest `unknown` · **1 wrong** (was 59/30/17 before the D-011/D-014 work) |
| **Formation** | 26/30 decoded · 4 gaps (`கொடுக்க` `கொடுத்து` `கொடுக்கும்` non-finite; `வீட்டிற்கு` noun dative) |

Re-run: `uv run python scripts/quality_sweep.py` (network on; ~3 min). It is the only honest
read on quality — expected labels inside are ASSESSMENTS, not authority, and need Saran's eye.
⚠️ It MUST use `default_engine()`: a hand-built `Engine` omits `morph_fallback=VerbParadigmAdapter()`
and 12 covered irregular verbs then look like FST gaps.

### How origin works now (the hard-won part)

Orthography proves a word is **not native**; it can NEVER say which language it came from.
- **Grantha (ஸ ஷ ஜ ஹ ஶ) marks a non-native SOUND, not Sanskrit.** Reading it as Sanskrit labelled
  பஸ்/ஸ்கூல்/ஹோட்டல்/ஜன்னல் as வடசொல் — 11 confident-wrong at 0.9. Same for the முதல் எழுத்து rule
  (ரூபம் is Sanskrit). Both now return "borrowed, source undetermined".
- **இறுதி எழுத்து is different and still asserts `loanword`** — it turns on morphological
  assimilation, not letters; Sanskrit borrowings take Tamil endings, so a bare vallinam final really
  does indicate a non-Sanskrit loan. Reviewable, reasoning in code.
- **`adapters/etymology.py`** resolves the source from en.wiktionary's machine-readable templates
  (`{{bor+|ta|pt|janela}}`, `{{inh+|ta|dra-pro|*maran}}`). Evolving tier — evidence, not authority;
  confidence caps at 0.8, competing class stays in `alternatives`, citation always travels.
  Cached per-claim, pulled only under `allow_enrichment`, falls back to offline rules when absent.

## Next tasks (build order)

1. **▶ SESSION 3 FOCUS — Tamil/Sanskrit homographs.** A headword can carry different origins per
   SENSE: கால் = leg (inherited, dra-pro *kāl) AND time (Skt காល); பூ = flower AND earth (Skt भू);
   பசு = cow (Skt पशु) AND green (dra-pro *pac-); சாலை = road (native சால்+ஐ) AND hall (Skt शाला);
   கார் = black (native) AND car (English). We currently return `unknown` + both alternatives, which
   is honest but throws away real information — 5 of the 23 unknowns are this.
   **The fix is architectural, not a rule tweak:** origin is currently per-HEADWORD but is really
   per-SENSE. Options to weigh: (a) `Origin.senses[]` so the response carries one origin per sense,
   (b) keep headword-level but return a `senses` breakdown alongside, (c) let the caller pass a sense
   hint. Note the schema already has `Meaning.senses` — aligning origin to it is the natural move.
   The adapter already parses both senses (`relation: "ambiguous"` + `senses[]`), so the data is
   there; only the schema and the presentation need deciding.
2. **Loanword lexicon** — the last unprincipled branch is native-by-default (no Grantha + legal
   phonotactics + no attestation ⇒ assumed native). It is the 1 remaining wrong (பட்டன், English
   button, no en.wiktionary page) and part of the 23 unknowns. Needs a lexicon, not a rule.
   **Madras Tamil Lexicon** (dsal.uchicago.edu) is the intended ANCHOR upgrade over Wiktionary.
3. **FST coverage:** non-finite forms (infinitive கொடுக்க, verbal participle கொடுத்து, adjectival
   கொடுக்கும்) + noun dative வீட்டிற்கு + more lemmas beyond the ~11 curated.
4. **Storage backend abstraction (D-013)** — `store/knowledge.py` is SQLite-coupled (`import sqlite3`,
   `INSERT OR REPLACE`, `AUTOINCREMENT`). `thamizh-ai.org` runs Postgres; **the MCP product keeps
   zero-config SQLite and must NEVER require containers or Postgres.** Both backends tested,
   SQLite default.
5. **Phase 4 eval** (`thamizh-eval`, D-005) — paused, harness resumable. Coverage fixes raised the
   ceiling so a re-measure is now meaningful. Prior finding: bare Opus ~97% on BASIC morphology, so
   headroom is in weaker models + harder items.
6. **Release rungs** — no CI exists yet (`.github/workflows/` absent); version still `0.1.0`.
   uvx → PyPI + Docker/GHCR. Registry + tamil-nlp-catalog listings after.
7. Network session (batch): TVA கலைச்சொல் snapshot · locate/license Aalamaram (D-008).
8. Lift `classify_origin` further with Thamizhi Validator.

## Design rules (do not violate)
- **Tholkappiyam-first:** cite Tholkappiyam before Nannool for grammar claims. This drifted once
  (2026-08-02) — tables were written citing Nannūl for வேற்றுமை and புணர்ச்சி, which Tholkappiyam
  governs, simply because the TVA lessons quote Nannūl. The rule on paper did not hold; the
  **mechanism** does: every `data/grammar/*.json` carries a `source_priority` block, and
  `tests/test_citations.py` fails without one. Priority table: `tamil-grammar.md` (design repo),
  restated in `DESIGN.md` §4a.
- **Self-enriching, no static dictionary:** fill gaps from live sources, cache
  per-claim with provenance (source + tier + retrieved date).
- **Honesty over guessing:** unknown → return a **gap**, never a fabricated answer.

## Gotchas
- Install package **`foma`**, NOT `foma-bin` (empty transitional deb).
- **NEVER write a நூற்பா number from memory — or from a secondary source.** TVA renumbers: its
  336/319/136 are **337/320/137** in the pinned edition. All three were wrong in shipped tables
  before `data/classical/` existed. Look the verse up in `data/classical/*.json`.
- **தொல்காப்பியம் நூற்பா numbers RESTART in every இயல்** and collide across இயல் and அதிகாரம் — a
  citation must name அதிகாரம் › இயல் › நூற்பா. நன்னூல் numbering is continuous 1–462, so a bare
  number is unambiguous there.
- Wikimedia blocks default UAs → descriptive UA lives in the adapter
  (`THAMIZH_HTTP_UA` overrides).
- `--include meaning` skips morphology by design (empty lemma there is not a bug).
- `data/knowledge.sqlite3` is gitignored — the self-enriching cache is machine-local.
- Wiktionary text is CC BY-SA (share-alike) and is **cleared for use incl. the public
  service** (2026-07-26) — serve it WITH attribution, keep it marked CC BY-SA, never
  relicense it as Apache-2.0. Mixed-licence product, classified per source: `LICENSING.md`.

## Where things live
- Runbook: `TESTING-ON-LINUX.md` · Pins/citations: `data/PINS.md` · Contract: `src/thamizh_mcp/schema.py`
- **Web app (main test surface): http://minnaham:8080** — `src/thamizh_mcp/web.py`,
  `src/thamizh_mcp/static/index.html`, service unit `deploy/thamizh-web.service`.
  Local run: `uv sync --extra web && uv run thamizh-web`.
  After a dep change: `uv sync --extra web && sudo systemctl restart thamizh-web`
  (the unit runs `.venv/bin/thamizh-web` directly — NOT `uv run`, whose ~/.cache lock is blocked by
  ProtectHome=read-only).
- CLI: `scripts/demo.py <word>` (readable) · `scripts/analyze.py <word>` (raw JSON)
- **Etymology:** `adapters/etymology.py` → source language; feeds `classifier.classify_origin`.
- **Classical texts:** `data/classical/{tholkappiyam,nannul}.json` — verse-addressable, checksummed
  in `data/PINS.md`. Rebuild/verify: `scripts/build_classical.py`. Guard: `tests/test_citations.py`.
- **Grammar rule tables:** `data/grammar/*.json` — each with `source_priority` + நூற்பா citations.
- **Design repo (separate, PUBLIC since 2026-08-02):** `~/projects/thamizh-mcp-design` →
  `ief-global/thamizh-mcp-design` — blueprint, DESIGN.md, DECISIONS.md, tamil-grammar.md,
  CODE-STATUS.md, DECODER-AUDIT-D014.md, sources/, thamizh-eval/. Same develop→PR→main flow as here.
  NEVER nest it inside this repo or commit design docs into this one.
