# CLAUDE.md — Thamizh MCP (developer context for Claude Code)

Thamizh MCP is a Model Context Protocol server for Tamil word-grammar
(சொல் இலக்கணம்) analysis. It grounds every answer in authentic Tamil sources
(Tholkappiyam-first) and self-enriches from evolving internet Tamil data instead
of a hand-maintained dictionary. Public repo: github.com/ief-global/thamizh-mcp
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

## Current state (2026-08-11) — 266 tests pass (5 skip without live foma)

**Everything below is live and merged to `main`.** Nine MCP tools + web/REST + CLI over ONE engine
(blueprint §8 — the web head needed zero engine changes, which validated that design).

| Layer | What |
|---|---|
| Anchors | ThamizhiMorph FST via `flookup` · curated verb paradigms (`data/verb_paradigms.json`) · pinned Tholkappiyam + Nannūl (`data/classical/`), **read at RUNTIME so claims QUOTE their நூற்பா** (`core/classical.py`, D-018) · cited grammar tables (`data/grammar/`) |
| Evolving | ta.wiktionary (meanings) · **en.wiktionary (etymology → source language)** · S2PT (native equivalents, PROVISIONAL — licence unstated) |
| Store | zero-config SQLite, per-claim provenance + `transactions` gold log (on by default) |
| Registry | **`data/sources.json` (D-017)** — every source's evidential GRADE (A–D) and legal REDISTRIBUTION MODE, as independent axes. `core/sources.py` stamps the grade onto every `SourceRef`; the web app shows it. |

**Tools:** `analyze_word` `classify_origin` `get_root` `get_meaning` `suggest_native_equivalent`
`enrich_word` `explain_formation` `explain_grammar` `refresh_sources`. Only optional
`validate_pure_tamil`/`generate_forms`/`transliterate` remain from blueprint §6.

### Measured quality (108-word everyday sweep, re-measured 2026-08-11 — unchanged)

| | result |
|---|---|
| **Origin** | 94 correct · 11 honest `unknown` · **1 wrong** (பட்டன்; was 59/30/17 → 82/23/1 → 87/18/1 → now) |
| **Formation** | 26/29 **in-scope** decoded · 3 gaps (`கொடுக்க` `கொடுத்து` `கொடுக்கும்` non-finite) · `வீட்டிற்கு` is **out of scope**, not a gap — புணர்ச்சி engine owns it (Saran's ruling 2026-08-08) |

⚠️ **The formation figure overstates quality — see KNOWN DECODER DEFECTS below.** The sweep counts a word as decoded if it yields MORE THAN ONE component; it never checks the split is right.

Re-run: `uv run python scripts/quality_sweep.py` (network on; ~3 min). It is the only honest
read on quality — expected labels inside are ASSESSMENTS, not authority, and need Saran's eye.
⚠️ It MUST use `default_engine()`: a hand-built `Engine` omits `morph_fallback=VerbParadigmAdapter()`
and the 11 covered irregular verbs then look like FST gaps.

### ⚠️ KNOWN DECODER DEFECTS — found 2026-08-11, both still OPEN

Neither of these is among the 3 "no analysis" gaps. **They affect words the sweep counts as
DECODED**, which is why the formation figure reads better than the decoder actually is.

**1 · The formation decode never checks its answer against the word.** `decode_formation()` builds
components from FST TAGS ONLY and never reconstructs the surface to compare. Anything present in the
word but absent from the tags is dropped in silence. Found by Saran via **காத்திருந்தாள்**, which
decodes as `காத்திரு + த் + ஆள்` — **the ந் is missing entirely.**

Root cause: the FST's `past=த்` is a tense CATEGORY, not the surface letters. It returns the *same
tag* for `ந்த` (காத்திருந்தாள், இருந்தான், அமர்ந்தான், நடந்தது), for `த்த` (படித்தான், பார்த்தான்)
and for plain `த` (செய்தான்). The decoder treats that tag as if it were the surface.

- **Saran's ruling 2026-08-11:** `காத்திருந்தாள் = காத்திரு(பகுதி) + ந்(சந்தி) + த்(இடைநிலை) + ஆள்(விகுதி)`.
  This agrees with **நன்னூல் 142**, which lists the past இடைநிலை as த்/ட்/ற்/இன் only — ந் is not
  among them, so it cannot BE the இடைநிலை.
- Affected inside the sweep's own list, all counted as decoded today: வந்தான், வந்தனன், வந்தார்கள்,
  வந்தீர்கள், நடந்தன.
- **FIX SITES.** `core/decoder.py` → `decode_formation()`: reconstruct and compare; unaccounted
  material must be NAMED or declared a gap, never dropped — the module docstring already promises
  *"a join we cannot classify is left unnamed, never invented"*, which the code cannot honour today
  because it never sees the join. Then `data/grammar/idainilai.json` → `idainilai.past.from_fst`:
  the machinery already exists (it maps `த்த்` → சந்தி + இடைநிலை); the nasal clusters `ந்த்`,
  `ன்ற்`, `ண்ட்` simply have no entries.
- **`scripts/quality_sweep.py` is blind to this by construction** — it counts a word as decoded if
  it produces MORE THAN ONE component and never checks the split. Any fix should add a guard that a
  decoded formation must rebuild its own surface or declare a gap. Expect the headline number to
  FALL; the current one is measuring the wrong thing.

**2 · `map_idainilai` labels strong-verb doubling as சந்தி, which Saran has RULED WRONG.**
`idainilai.json`'s `known_gap` says it plainly: *"It is not சந்தி (ruled) … `map_idainilai` currently
splits the doubling off AS சந்தி and emits a வல்லினம் மிகுதல் SandhiEvent. Both are wrong and must
change."* Today படிக்கிறான் still returns `படி + க்(சந்தி) + கிறு + ஆன்`.

⛔ **BLOCKED — do NOT guess the label.** It is not சந்தி (ruled); it is not one of the listed
இடைநிலை, which are all single; and TVA C0212 §6.3.1's பகுதி-இரட்டித்தல் is defined only for the case
where there is NO இடைநிலை, which is not this case. Fixing defect 1 will EXPOSE this immediately on
படித்தான், கொடுத்தான், பார்த்தான், செய்வித்தான். Scope once ruled touches every strong-verb form
already decoded (கொடுக்கிறான், படிக்கிறான், படிப்பான், கொடுப்பான் …), not only the new ones — which
is exactly why the note says getting the label wrong means doing the rework twice.

### How origin works now (the hard-won part)

Orthography proves a word is **not native**; it can NEVER say which language it came from.
- **Grantha (ஸ ஷ ஜ ஹ ஶ) marks a non-native SOUND, not Sanskrit.** Reading it as Sanskrit labelled
  பஸ்/ஸ்கூல்/ஹோட்டல்/ஜன்னல் as வடசொல் — 11 confident-wrong at 0.9. Same for the முதல் எழுத்து rule
  (ரூபம் is Sanskrit). Both now return "borrowed, source undetermined".
- **இறுதி எழுத்து is different and still asserts `loanword`** — it turns on morphological
  assimilation, not letters; Sanskrit borrowings take Tamil endings, so a bare vallinam final really
  does indicate a non-Sanskrit loan. Reviewable, reasoning in code.
- **Origin is per-SENSE, not per-headword (D-015, Session 3).** en.wiktionary carries one
  `===Etymology N===` block per sense and they disagree: கால் is leg/canal/forest (inherited) AND
  time (Sanskrit); பூ is flower AND earth; பசு is green AND cow; சாலை is road AND hall; கார் is
  blackness AND English car. The parser reads each block on its own — ranking templates across the
  whole section picked `bor` over `inh` every time and labelled four core native words வடசொல் at
  0.8. Each sense's origin lands in `Origin.senses[]`, mirroring `Meaning.senses`.
  **Saran's ruling (2026-08-05): the Tamil sense LEADS at headword level — for EVERY source
  language**, Sanskrit, English, Urdu, Marathi, Telugu alike. This is a Thamizh server, so the
  reader is pointed at the Tamil word first; the borrowed sense is never suppressed — it rides in
  the evidence, in `alternatives`, and in full in `senses[]`. Confidence 0.7, below a clean
  single-etymology 0.8, because the headword class is a reporting ruling layered on the evidence.
  A sense whose block states no relation at all is omitted, not padded in. 16 of the 108 sweep
  words carry a breakdown. `Origin.is_native` stays `Optional` for the case no Tamil sense exists
  (senses differ only in WHICH foreign language, e.g. கிளாஸ் = class AND glass).
- **A borrowed sense hands back the Tamil word for it.** `SenseOrigin.tamil_alternatives` —
  கார்'s English 'car' sense returns மகிழுந்து/சீருந்து/தானுந்து; கிளாஸ் returns வகுப்பு for its
  'class' sense and கண்ணாடி for 'glass'. Saran's reasoning: the reader may well have meant the
  borrowed sense, and now they also know the Tamil word for it. Sourced from the page's own
  `{{syn|ta|…}}` under that sense, **filtered by `classifier.looks_orthographically_native`** —
  en.wiktionary lists ரோடு (English) as a synonym of சாலை's road sense, so an unfiltered list would
  hand back a borrowing.
  ⚠️ **Named `tamil_alternatives`, NOT `native_equivalents`, on purpose.** The orthographic rules
  prove non-nativeness only, so naturalized Sanskrit passes them — தானம் 'place' yields சுவர்க்கம்
  (< स्वर्ग) and சக்தி (< शक्ति), மந்திரம் yields மண்டபம் (< मण्डप). Do not re-label these "pure Tamil"
  until the loanword lexicon lands; that is the same native-by-default weakness as build rung 1.
  Evolving tier, confidence 0.6. They also feed the headword `native_equivalent` when S2PT misses —
  S2PT is keyed on borrowed HEADWORDS and has no கார் row at all, so `suggest_native_equivalent`
  was silent for every homograph before this. (Renamed from “I2PT” in D-017; GitHub's silent
  redirect hid the rename for weeks, so treat the old name as a staleness marker wherever it appears.)
- **`adapters/etymology.py`** resolves the source from en.wiktionary's machine-readable templates
  (`{{bor+|ta|pt|janela}}`, `{{inh+|ta|dra-pro|*maran}}`). Evolving tier — evidence, not authority;
  confidence caps at 0.8, competing class stays in `alternatives`, citation always travels.
  Cached per-claim, pulled only under `allow_enrichment`, falls back to offline rules when absent.

## Next tasks (build order)

0. ⛔ **BLOCKED ON SARAN — open rulings. Do NOT guess these**; they are recorded as `inferred`/open
   precisely so they stay marked until he rules.
   - **(a) The four verb-paradigm entries** — `data/grammar/concept_map.json` →
     `concepts.விகாரம்.inferred`. **விற் is RULED (2026-08-11): the root is வில், ல்→ற் is the
     விகாரம், and the following ற் is a நூற்பா-142-listed இடைநிலை** — so it joins கல்/கேள்/நில்/கொள்
     rather than standing alone. **சொல், கல், கேள் remain open.** `verb_paradigms.json` is
     deliberately NOT restructured yet: the lemma is the lookup key, so விற்→வில் lands with the
     other three as one change.
   - **(b) The 15 running-head candidates** in `data/PINS.md` — our reading is a PROPOSAL. Note it
     contradicts itself in two places: 139/242 share a structure but get opposite verdicts, as do
     181/182.
   - **(c) எச்சவினை விகுதி** — FOUND: தொல். சொல். வினையியல் 31 and நன்னூல் 343 both enumerate the
     class, so this is a Tholkappiyam-FIRST citation. Open part: they name the FORMS, not the விகுதி
     letters, and **நன்னூல் 140 lists `து` where `vikuthi.json` (following TVA) has `உ`**.
   - **(d) What the doubled `த்` slot is called** — see KNOWN DECODER DEFECTS above.

1. **▶ NEXT — the ந் surface-reconciliation fix** (defect 1 above). Unblocked by Saran's 2026-08-11
   ruling, and it should ship with a guard test asserting a decoded formation rebuilds its own
   surface or declares a gap. Landing it will expose defect 2, which is blocked on ruling (d).
2. **Loanword lexicon** — the last unprincipled branch is native-by-default (no Grantha + legal
   phonotactics + no attestation ⇒ assumed native). It is the 1 remaining wrong (பட்டன், English
   button, no en.wiktionary page) and part of the 11 unknowns. Needs a lexicon, not a rule.
   **Madras Tamil Lexicon** (dsal.uchicago.edu) is the intended ANCHOR upgrade over Wiktionary.
3. **FST coverage:** non-finite forms (infinitive கொடுக்க, verbal participle கொடுத்து, adjectival
   கொடுக்கும்) + more lemmas beyond the 11 curated. ⛔ Non-finite is BLOCKED on ruling (a) below.
   வீட்டிற்கு is NOT on this list — Saran ruled it புணர்ச்சி-engine work, not பகுபத உறுப்பிலக்கணம்.
4. **Storage backend abstraction (D-013)** — `store/knowledge.py` is SQLite-coupled (`import sqlite3`,
   `INSERT OR REPLACE`, `AUTOINCREMENT`). `thamizh-ai.org` runs Postgres; **the MCP product keeps
   zero-config SQLite and must NEVER require containers or Postgres.** Both backends tested,
   SQLite default.
5. **Phase 4 eval** (`thamizh-eval`, D-005) — paused, harness resumable. Coverage fixes raised the
   ceiling so a re-measure is now meaningful. Prior finding: bare Opus ~97% on BASIC morphology, so
   headroom is in weaker models + harder items.
6. **Release rungs** — CI runs the suite on every PR (`.github/workflows/tests.yml`,
   Python 3.10 + 3.14, foma installed so the 5 FST tests RUN rather than skip). **`ci-ok` is the
   required status check on `main`** — an aggregating job, NOT the matrix legs: requiring
   `test (3.10)` by name would block every PR forever the day the matrix changes. Both repos'
   `main` carry the same `protect-main` ruleset (PR-only, no force-push, no delete). Version is
   still `0.1.0`; no published release yet.
   uvx → PyPI + Docker/GHCR. Registry + tamil-nlp-catalog listings after.
7. Network session (batch): TVA கலைச்சொல் snapshot · locate/license Aalamaram (D-008).
8. Lift `classify_origin` further with Thamizhi Validator.

### Every source declares its grade and its licence (D-017)

`data/sources.json` is the registry; `core/sources.py` reads it at runtime. Before it, licence and
quality facts lived in three prose places (`LICENSING.md`, `data/PINS.md`, adapter docstrings) and
**nothing checked that a shipped adapter had been through any of them** — which is how S2PT stayed
load-bearing for weeks under a "MIT" claim with no upstream basis.

- **`grade` (A–D) is EVIDENTIAL; `redistribution` is LEGAL. They are INDEPENDENT axes (D-016).**
  The Madras Tamil Lexicon is grade **A** *and* consult-and-cite. Never derive one from the other.
- **`tests/test_sources_registry.py` fails if a shipped `SourceAdapter` has no entry, or an entry
  states no licence.** `licence_status: "unstated"` PASSES — recording "we do not know" is the
  honest fact. What must never pass is silence.
- **The grade travels with the answer.** `_grade_sources()` in `engine.py` walks the finished
  analysis once, so a source cannot ship ungraded by being wired somewhere the author forgot.
- Caps are a **ceiling, never a score** — every cap currently sits at or above what the classifier
  emits, so the sweep is unchanged. It binds the day someone raises a confidence past its source.
- Framing to keep: **authenticity comes from every claim carrying a graded, citable provenance the
  user can check — not from every source being impeccable.** A grade D source is fine to ship, as
  long as the answer says it is grade D.

### Verse grounding is RUNTIME now, not just a test (D-018)

`data/classical/` was previously read only by `tests/test_citations.py` — a design-time guard proving
every cited நூற்பா number exists. Nothing in `src/` opened it, so `SourceRef.verse` was always None
and a user asking "on whose authority?" got a chapter name. **`core/classical.py` now serves verses at
runtime**, `SourceRef.verse_text` carries the நூற்பா verbatim, and the web app quotes it.

- **Nannūl** is continuous 1–462 → `classical.nannul_verse(133)`.
- **Tholkappiyam** numbers RESTART per இயல் and collide, so there is deliberately **no bare-number
  API** — `classical.tholkappiyam_verse(அதிகாரம், இயல், n)`. A bare number is a bug, not a shortcut.
- **As of 2026-08-11 every decoder `SourceRef` is verse-cited.** The last three (`COLLATIKARAM` → பெயரியல் 4+5, `VETRUMAI` → வேற்றுமையியல் 3, `VINAIYIYAL` → வினையியல் 1) carried `verse=None`. Note பெயரியல் **4 and 5**: Tholkappiyam does NOT state four word classes
  in one நூற்பா — 4 names பெயர்/வினை, 5 adds இடை/உரி — so both travel rather than crediting one
  verse with classes it does not name.
- **The rule still stands and is not a licence to guess.** An unconfirmed நூற்பா keeps `verse=None` and cites the section. Never fill one in from memory or a secondary source — TVA
  renumbers (its 336 is 337 here). Build refs through `classical.cite_*`, never by hand, so the
  quoted text comes from the pinned artifact. `tests/test_citations.py` now asserts both.
- **Quoting obliges attribution.** Project Madurai grants distribution provided its header travels
  with the text, so any surface that quotes must show the credit (`classical.attribution`).

The cost of not having had this: settling what the six உறுப்பு even are took several exchanges, and
**நன்னூல் 133** — which names all six — was sitting in the repo the whole time. It had to be grepped
by hand.

⚠️ **133 does NOT settle what the second `த்` in வா + த் + த் + ஏன் is called.** An earlier version of
this file implied it did, by noting that 133 names சந்தி among the six. `idainilai.json`'s
`known_gap` records Saran's ruling that a doubled consonant is **not** சந்தி — so that reading is
ruled OUT, not merely unconfirmed. The slot is still unnamed; see KNOWN DECODER DEFECTS.

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
- Runbook: `TESTING-ON-LINUX.md` · Pins: `data/PINS.md` · Contract: `src/thamizh_mcp/schema.py`
- **Source registry (D-017): `data/sources.json`** — grade, licence, redistribution mode, pin,
  maintenance, supersession. Read by `core/sources.py`; enforced by `tests/test_sources_registry.py`.
  `LICENSING.md` keeps the REASONING and points here for the facts — do not restate a licence in both.
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
