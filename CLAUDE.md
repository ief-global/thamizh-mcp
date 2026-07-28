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

## Current state (2026-07-17)
**Phase 1 core DONE.** FastMCP server with `analyze_word` end-to-end: ThamizhiMorph
FST anchor (foma), SQLite per-claim knowledge store + self-enriching
pull→write-back→cache loop, Wiktionary adapter (descriptive UA + real ta.wiktionary
template-style parser).
**Native equivalents live (2026-07-17):** `IndicToPureTamilAdapter` over the vendored I2PT
sub-lists (per-candidate attestation, attested-only), wired into the engine
(`_fill_native_equivalent`) and exposed as the `suggest_native_equivalent` MCP tool.
**Origin classifier live (2026-07-17):** `core/classifier.py` — rule-based, Tholkappiyam-grounded
(Grantha letters via open-tamil; முதல்/இறுதி எழுத்து phonotactics) fused with the FST native-parse
and I2PT attestation. Classes இயற்சொல்/வடசொல்/loanword; honest `unknown` for திரிசொல்/திசைச்சொல் and
language-undetermined borrowings (never guessed). Exposed as `classify_origin`; origin now gates
`native_equivalent` (native word → not applicable).
**Root + meaning + enrich tools live (2026-07-17):** thin `get_root` (FST lemma/POS, keeps all
analyses), `get_meaning` (self-enriching store → Wiktionary pull, provenance-tagged), and
`enrich_word` (forces the pull→write-back loop, reports what the store now caches; the one
non-readOnly tool) MCP heads over the existing engine paths.
**Formation decoder live (2026-07-18):** `core/decoder.py` `decode_formation` — FST tags →
பகுபத உறுப்பு (Nannūl six parts) + Tholkappiyam சந்தி. Verbs read பகுதி/இடைநிலை/விகுதி straight from
the FST `=forms`; nouns get சாரியை/உருபு surface-grounded; joins classified only where a confident
classical rule applies (no invented split). Grammar now also carries verb tense + முற்று. Exposed as
`explain_formation` and `explain_grammar`.
**refresh_sources live (2026-07-18):** batch coverage-growth tool — force-refreshes evolving claims
(explicit `words` and/or `stale_days` sweep of the store), bounded by `limit`, overwriting the cache;
per-word report with honest errors. Adds a `force_refresh` path to the engine + `KnowledgeStore.stale_words`.
**Nine MCP tools now** (only optional `validate_pure_tamil`/`generate_forms`/`transliterate` left from §6).
**FST coverage gaps fixed (2026-07-20):** the primary FSTs miss ~25% of everyday past-tense verbs
(போனான், சொன்னான், கொடுத்தான், கற்றான், விற்றான், தூங்கினான்) — those lemmas/irregular past stems aren't in
the lexicon. Guessers stay excluded (they return WRONG lemmas: கொடுத் for கொடு). Instead
`adapters/paradigms.py` + `data/verb_paradigms.json` = a curated ANCHOR rule table (irregular past stem
× regular PNG suffixes), used ONLY on an FST miss, emitting the FST's own tag shape so decoder/grammar
work unchanged. Surface forms are GENERATED with a proper Tamil mei+uyir join (போன்+ஆன்→போனான், not
string concat). Table is closed (unlisted word → honest gap).
Also fixed: causative இடைநிலை was dropped by the decoder (செய்வித்தான் → செய்+**வி**+த்+ஆன்).
**Extended to all three tenses (2026-07-20):** paradigms are keyed by tense (`past`/`pres`/`fut`) using
ThamizhiMorph's own marker convention (`pres=க்கிற்`, `fut=ப்ப்`…), incl. the literary `கின்ற்` variant.
Future **excludes 3sgn** — Tamil future neuter is `-உம்` (வரும்), which the FST itself tags NONFINITE
`futANDadjpart`, so it is not invented as a finite form. Coverage on the common-verb sweep:
past 18/24 → **24/24**, present 12/18 → **18/18**, future 12/18 → **18/18**.
**Transaction logging live (2026-07-18):** every resolved `analyze()` is logged to a `transactions`
table as gold data (blueprint §12) — full WordAnalysis + tool label + `eval_fixture` contamination flag
(from `data/eval_fixtures.json`). On by default (`THAMIZH_TXN_LOG=0` disables); a non-fatal background
side-output. Captures the FST/rule-based segmentation+origin gold the `claims` cache never held. The
`thamizh-data-curation` skill reads this table directly. `KnowledgeStore.transaction_stats()` for growth.
**Web/REST head live (2026-07-26):** `src/thamizh_mcp/web.py` + `static/index.html` — FastAPI head over
the SAME engine (blueprint §8 "heads: MCP | REST | CLI over one engine"; zero engine changes were
needed, which validates that design). `GET /` UI · `GET /api/analyze?word=…&meaning=…` · `GET /healthz`.
**Network/meaning is OFF by default** so a demo or test can never hang. **Why it exists:** terminals do
NOT shape Tamil script (vowel signs detach/reorder) — CLI output is unreadable for demos; browsers shape
it correctly. Runs 24/7 on minnaham via `deploy/thamizh-web.service` (systemd) at
**http://minnaham:8080** — every word tested there also feeds the `transactions` gold log.
Also: `scripts/demo.py` (projector-readable CLI view) and a Dockerfile fix (`foma`, not the empty
transitional `foma-bin` — the container had shipped with no working FST).
**109 tests pass** (107 without live foma). Design repo at `~/projects/thamizh-mcp-design/` →
`ief-global/thamizh-mcp-design` (blueprint, tamil-grammar.md, DECISIONS, roadmap, CODE-STATUS.md).

## Test ladder (run in order, from repo root)
```bash
uv sync                                              # installs deps incl. pytest
which flookup && echo "மரம்" | flookup data/fst/noun.fst
uv run pytest -v                                     # expect 109 passed with foma
uv run python scripts/analyze.py மரத்தில் --include formation  # பகுதி மரம் + சாரியை அத்து + விகுதி இல்
uv run python scripts/analyze.py ரயில் --include origin       # loanword: முதல் எழுத்து rule
uv run python scripts/analyze.py ஜோதி --include origin        # வடசொல்: Grantha letter
uv run python scripts/analyze.py மரத்தில்            # lemma மரம், loc|soc kept, Tholkappiyam cites
uv run python scripts/analyze.py புத்தகம் --include meaning   # first live Wiktionary pull
uv run python scripts/analyze.py புத்தகம் --include meaning   # again → must serve from cache
sqlite3 data/knowledge.sqlite3 'select word,field,source,tier,retrieved from claims;'
```
Register as an MCP server: `claude mcp add thamizh -- uv --directory ~/projects/thamizh-mcp run thamizh-mcp`

## Next tasks (build order)
1. ~~**Kalaichol / equivalents adapter** over the pinned I2PT CSVs →
   `suggest_native_equivalent`.~~ **DONE (2026-07-17):** local I2PT adapter +
   engine wiring + MCP tool + tests. **Remaining under this objective:** (a) mine
   ta.wiktionary `{{சொல்வளம்N|...}}` synonym templates as a second *network* evolving
   source (must honor `allow_enrichment`); (b) TVA govt கலைச்சொல் **anchor** glossary
   (`kalaichol.py` still a stub — network snapshot, see task 5).
2. ~~**Origin classifier** → four Tholkappiyam classes.~~ **DONE (2026-07-17):**
   `core/classifier.py` (open-tamil Grantha + Tholkappiyam முதல்/இறுதி எழுத்து rules +
   FST parse + I2PT), `classify_origin` tool, gates `native_equivalent`. **Remaining/deferred:**
   திரிசொல்/திசைச்சொல் need a lexical/dialectal corpus (return `unknown` for now, never guessed);
   Thamizhi Validator + a real loanword dataset can slot in later as stronger signals to lift
   the many honest `unknown`s (e.g. புத்தகம், கம்ப்யூட்டர்).
3. ~~**Remaining MCP tools:** classify_origin, get_root, get_meaning,
   suggest_native_equivalent, enrich_word, explain_formation, explain_grammar.~~
   **DONE + `refresh_sources` (2026-07-18) → 9 tools.** Only optional
   `validate_pure_tamil`/`generate_forms`/`transliterate` remain from blueprint §6.
4. ~~**Formation decoder** (FST tags → பகுபத உறுப்பு) — Phase 3.~~ **DONE (2026-07-18):**
   `decode_formation` + verb tense/முற்று grammar. **Deferred (honest boundary):** precise
   விகாரம்/சந்தி naming beyond the confident rules (e.g. verb root வா→வந்) — the FST doesn't hand
   the join over, so it's left unnamed for now, never invented.
5. ~~FST coverage gaps~~ **DONE (2026-07-20)** — see Current state. Remaining coverage work:
   **non-finite forms** (infinitive கொடுக்க, verbal participle கொடுத்து, adjectival கொடுக்கும்) — very
   common in running text and still gapping for the curated lemmas; and **more lemmas** beyond the ~11
   verified (ஆகு, தா, வை, செல், காண்…).
6. **Storage backend abstraction (for the public app).** `thamizh-ai.org` (domain bought 2026-07-26)
   is a **separate deliverable** from this MCP product — see D-013. It runs as a container + **Postgres**;
   **the MCP product keeps zero-config SQLite and must NEVER require containers or Postgres.** So
   `store/knowledge.py` needs a thin backend abstraction (it is SQLite-coupled today: `import sqlite3`,
   `INSERT OR REPLACE`, `AUTOINCREMENT` in `schema.sql`), with both backends tested and SQLite the default.
   App layers: browser UI → FastAPI head → same engine → Postgres (growing data) + pinned anchor data in
   the image. Hosting stays on minnaham; public access via Tailscale Funnel when needed.
7. **▶ NEXT (2026-07-26, Saran's direction): TESTING-DRIVEN development from the web app.**
   Saran is testing at http://minnaham:8080 and will bring back observed gaps + questions + UI tweaks.
   Those findings drive what we build next — fix what real use exposes, rather than working the backlog
   blind. Expect: web-UI tweaks, clarification questions, and code fixes to already-delivered features.
8. **Phase 4 eval** (morphological lift, `thamizh-eval` — D-005). Paused mid-run; harness is resumable
   (`--model`/`--max-new`/`--grounded`, budget-spaced). Note the coverage fixes raised the achievable
   ceiling, so a re-measure is now more meaningful. Prior finding: bare Opus ~97% on BASIC morphology →
   little headroom there; real headroom is on weaker models + harder items.
9. Lift `classify_origin` (Thamizhi Validator + loanword dataset) · **network session (batch):**
   Madras Lexicon + TVA கலைச்சொல் snapshots + locate/license Aalamaram (D-008) + pin a digitized
   Tholkappiyam/Nannūl edition for D-011 நூற்பா citations (**edition chosen: Project Madurai**;
   `SourceRef.verse` field already exists — NEVER hardcode verse numbers from memory).
   Program roadmap: `~/projects/thamizh-mcp-design/DESIGN.md` (supersedes TAMIL-HIGH-RESOURCE-ROADMAP.md).

## Design rules (do not violate)
- **Tholkappiyam-first:** cite Tholkappiyam before Nannool for grammar claims.
- **Self-enriching, no static dictionary:** fill gaps from live sources, cache
  per-claim with provenance (source + tier + retrieved date).
- **Honesty over guessing:** unknown → return a **gap**, never a fabricated answer.

## Gotchas
- Install package **`foma`**, NOT `foma-bin` (empty transitional deb).
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
- **Design repo (separate, private):** `~/projects/thamizh-mcp-design` → `ief-global/thamizh-mcp-design`
  — blueprint, DESIGN.md, DECISIONS.md, tamil-grammar.md, CODE-STATUS.md, PRESENTATION-SOURCE.md,
  thamizh-eval/. NEVER nest it here or commit design docs into this public repo.
