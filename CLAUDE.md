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
`git config --global` is already set to this on this box. Any other author address is wrong: stop
and fix it before pushing. Never write a personal email address into this public repo.
Verify: `git log --format='%an <%ae>' -1`.

## Branch workflow
`main` = stable, **protected** (PR-only, no force-push, no delete). `develop` =
integration. Loop: work on `develop` here → push → open PR `develop → main` at
milestones. After any history rewrite, other clones must `git reset --hard origin/main`
(not merge/rebase).

## Current state (2026-11-25) — 376 tests pass (the FST tests skip without live foma)

**Everything below is live and merged to `main`.** Nine MCP tools + web/REST + CLI over ONE engine
(blueprint §8 — the web head needed zero engine changes, which validated that design).

| Layer | What |
|---|---|
| Anchors | ThamizhiMorph FST via `flookup` · curated verb paradigms (`data/verb_paradigms.json`) · pinned Tholkappiyam + Nannūl (`data/classical/`), **read at RUNTIME so claims QUOTE their நூற்பா** (`core/classical.py`, D-018) · cited grammar tables (`data/grammar/`) |
| Round-trip | **`core/punarchi.py` + `data/grammar/punarchi.json` (D-023, D-025)** — every formation must rebuild its word under cited join rules, or it declares a gap |
| Evolving | ta.wiktionary (meanings) · **en.wiktionary (etymology → source language)** · S2PT (native equivalents, PROVISIONAL — licence unstated) |
| Store | zero-config SQLite, per-claim provenance + `transactions` gold log (on by default) |
| Registry | **`data/sources.json` (D-017)** — every source's evidential GRADE (A–D) and legal REDISTRIBUTION MODE, as independent axes. `core/sources.py` stamps the grade onto every `SourceRef`; the web app shows it. |

**Tools:** `analyze_word` `classify_origin` `get_root` `get_meaning` `suggest_native_equivalent`
`enrich_word` `explain_formation` `explain_grammar` `refresh_sources`. Only optional
`validate_pure_tamil`/`generate_forms`/`transliterate` remain from blueprint §6.

### Measured quality (108-word everyday sweep, re-measured 2026-11-25)

| | result |
|---|---|
| **Origin** | 92 correct · 12 honest `unknown` · **2 wrong** (காலம், பட்டன்; was 59/30/17 → 82/23/1 → 87/18/1 → 94/11/1 on 2026-08-11 → 91/12/3 on 2026-11-24 before ruling (e) → now) |
| **Formation** | 26/29 **in-scope** decoded AND rebuild their word (25 with every step cited, 1 with a parked stem: சொன்னான்) · 3 gaps (`கொடுக்க` `கொடுத்து` `கொடுக்கும்` non-finite) · `வீட்டிற்கு` is **out of scope**, not a gap — புணர்ச்சி engine owns it (Saran's ruling 2026-08-08) |

⚠️ **The 2026-11-24 origin drop is UPSTREAM DRIFT, not a code change** — en.wiktionary was edited under
three sweep words. மனிதன் is now marked borrowed from **Prakrit** — resolved by ruling (e): it is now classed **பிராகிருதம்**.
காலம்'s Sanskrit origin moved to the new `{{af|ta|sa:…}}` / `{{ety|…}}` template style, which
`adapters/etymology.py` does not read, so it falls through to native-by-default — **a parser gap, ours
to fix.** கொடு now states cognates only → honest `unknown`. Per-word table: design repo `CODE-STATUS.md`.

The formation figure now means something it did not before 2026-11-25: a word counts only if its
split **rebuilds the word** (D-023). The same 26 pass, but five of them (வந்தான், வந்தனன், வந்தார்கள்,
வந்தீர்கள், நடந்தன) used to pass with a letter missing. "Cited" includes `textbook` steps (a TVA
course book quoted verbatim): since D-026 that covers the strong-verb doubled consonant (8 words).
"Parked" = a curated stem whose change is unnamed under ruling (a) (சொன்னான்).

Re-run: `uv run python scripts/quality_sweep.py` (network on; ~3 min). It is the only honest
read on quality — expected labels inside are ASSESSMENTS, not authority, and need Saran's eye.
⚠️ It MUST use `default_engine()`: a hand-built `Engine` omits `morph_fallback=VerbParadigmAdapter()`
and the 11 covered irregular verbs then look like FST gaps.

### The round-trip engine (D-023, built 2026-11-25 as D-025)

**A split is valid only if joining its parts back, under the SAME rules, rebuilds the word.**
`core/punarchi.py` finds the split by SYNTHESIS: it tries the joins in `data/grammar/punarchi.json` at
each boundary between the FST's parts and keeps a split only when the join reproduces the word
exactly. `Formation.round_trip` carries `holds`, `rebuilt`, every `JoinStep` (rule, boundary, effect,
status, quoted verse) and, on failure, the `unaccounted` letters. The engine decodes the first FST
analysis that rebuilds (செய்தான்'s FST lists a noun reading first) and raises a formation Gap if none does.

- **Split and join are one rule set by construction.** Letters ↔ phonemes is தொல். எழுத்து. புணரியல் 36
  (join: a vowel after a pulli fuses with it) and 37 (split: the consonant takes back its own form).
  The guard re-renders all 1,602 pinned verses through that bijection.
- **Each rule cites its நூற்பா by ADDRESS; the text is quoted at runtime.** Tholkappiyam first:
  புணரியல் 12, 23, 31, 36–38 · உருபியல் 13 · குற்றியலுகரப்புணரியல் 6. Nannūl 164 (உகரம் கெடுதல்) and 219
  (ம் → nasal) are sole citations only where a search of எழுத்ததிகாரம் found no Tholkappiyam verse,
  and the table records that search. `tests/test_roundtrip.py` fails a classical rule without a cite.
- **Fixtures are the commentary's own examples**: மரத்தை, மரத்தொடு, நுகத்தை (உருபியல் 13, where
  நச்சினார்க்கினியர் himself says they are finished by புணரியல் 31 + 23), மணிக்கு, கிளியழகிது … rebuild.
- **Defect 1 is FIXED.** காத்திருந்தாள் = காத்திரு + த்(ந்) சந்தி + த் + ஆள். The ந் is a `textbook` rule:
  TVA C0212 §5.3.6 says it verbatim ("த் என்னும் சந்தி ந் என்று மாற்றம் அடைந்தும்"), and it agrees with
  Saran's 2026-08-11 ruling and நன்னூல் 142. The same section gives வா → வ (குறுகல்); A0212 §2.2.1
  pairs வா with வரு (change not named, so no label asserted).
- **Defect 2 is SETTLED PROVISIONALLY (D-026, closing ruling (d), 2026-11-25).** The strong-verb
  doubled consonant is a **சந்தி** on TVA C0212 §5.3.5 ("சந்தி பெரும்பாலும் முதனிலை (பகுதி)க்கும்
  இடைநிலைக்கும் இடையில் வரும்", e.g. நட + த் + தல்), so படிக்கிறான் = படி + க்(சந்தி) + கிறு + ஆன். Rule
  `irattitha_otru`, status `textbook`, with Nannūl 133 (names சந்தி among the six உறுப்பு) alongside.
  Saran ruled the course book sufficient **until an authentic classical உரை on சொல்லதிகாரம் is found;
  that உரை takes PRECEDENCE** (the rule's `supersede_when`; open item in Next tasks). No மிகுதல் event:
  the text names an உறுப்பு, not a change. The withdrawn 2026-08-02/08-08 entries stay withdrawn.
- Statuses: `classical` (a நூற்பா states it) · `textbook` (a TVA course book states it verbatim; a
  classical source found later outranks it, and the search prefers a நூற்பா when both rebuild) ·
  `parked` (named, never labelled). A stem alternant from `verb_paradigms.json` is `parked` too: its
  விகாரம் is ruling (a). நில் → நி + ன்ற் looks odd because the curated marker is `ன்ற்`; that is ruling (a).

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
   - ~~**(d) What the doubled `த்` slot is called.**~~ **RULED 2026-11-25 (D-026): சந்தி, on TVA C0212
     §5.3.5, provisionally** — a classical சொல்லதிகாரம் உரை takes precedence once found (task 1 below).
   - ~~**(e) Does வடசொல் cover Prakrit borrowings?**~~ **RULED 2026-11-24 (D-022): no.** பிராகிருதம் is
     its own origin class, assigned only when a source names Prakrit (`classifier.PRAKRIT_CODES`).
     Pali is NOT included; it stays `loanword` until ruled.

1. 🔶 **The சொல்லதிகாரம் உரை — PINNED 2026-11-25 (D-027); what it means for (d) is SARAN'S CALL.**
   நச்சினார்க்கினியர் and இளம்பூரணர் are pinned from TVA scans (`data/classical/tholkappiyam_sol_urai_*.json`,
   OCR, every unit with its scan leaf). Read against the scan pages (`data/classical/verified_quotations.json`),
   **நச்சினார்க்கினியர் never calls any part of a verb சந்தி.** His parts are முதனிலை, the tense letter
   (க ட த ற after the முதனிலை = past; வினையியல் 5, p. 205), இடைநிலை எழுத்து, ஈறு, and விகாரம். He calls
   வந்தான்'s extra letter "கால வெழுத்திற் கேற்ற இடைநிலை யெழுத்து" (p. 467), causatives take
   "இடைநிலையாகிய வெழுத்துக்கள்" (p. 237), and in feminine nouns a doubled த ஒற்று is among the
   "இடைநிலை யெழுத்துக்கள்" (p. 174). He does NOT split a strong verb's two த் (கொடுத்தான்) explicitly.
   இளம்பூரணர் is silent on tense letters. Under D-026 a commentary that names the slot outranks the
   course book; whether these passages name it (and whether `santhi_tha_na`'s ந் moves too) is open.
   The same page settles the SHAPE of ruling (a) for ல்/ள் roots: "லகாரம் னகாரமாய்த் திரிந்து, தனக்கேற்ற
   றகர வொற்றுப் பெற்று" (கொன்றான்), "ளகாரம் ணகாரமாயும்" (கொண்டான்). Do not apply either until he rules.
   சேனாவரையர் (whom நச்சினார்க்கினியர் says separates the tense letters) is not pinned.
✓ ~~**The ந் surface-reconciliation fix**~~ **DONE 2026-11-25 (D-025)** — the round-trip engine.
   Natural next steps on it: non-finite forms once ruling (a) allows, and the noun joins the sweep
   does not cover yet (இன் சாரியை, so வீட்டிற்கு moves from "out of scope" to rebuildable).
2. **Loanword lexicon** — the last unprincipled branch is native-by-default (no Grantha + legal
   phonotactics + no attestation ⇒ assumed native). It is one of the 3 wrong (பட்டன், English
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

⚠️ **133 does NOT settle what a strong verb's doubled consonant (படி + த் + த் + ஆன்) is called.** An
earlier version of this file implied it did, by noting that 133 names சந்தி among the six. Both earlier
entries on it (2026-08-02 "சந்தி", 2026-08-08 "not சந்தி") are WITHDRAWN as rulings (D-023); since
D-026 the slot is labelled சந்தி on TVA C0212 §5.3.5, which says WHERE சந்தி comes (133 does not),
until a classical சொல்லதிகாரம் உரை is found. Do not confuse it with வந்தான்'s ந்: TVA C0212 §5.3.6 names that one a
சந்தி த் surfacing as ந், and Saran ruled the same on 2026-08-11.

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
- **Round-trip validity (D-023, Saran, 2026-11-24) — a fundamental rule.** A word split is valid only
  if joining its parts back, under the SAME rule tables, rebuilds the word. Split and join follow one
  rule set. A split that does not rebuild its word declares a gap; it never drops material in silence.
- **Rules come from the texts, not from rulings (D-023).** Where the grammar is ambiguous, find the
  rule in a cited source (நூற்பா, or a classical உரை) and follow it. Do not settle an ambiguity by
  asking for a ruling made without a source; park it until the text is found. A TVA course book that
  states the analysis verbatim may carry a label **provisionally** (`textbook`, D-026); a நூற்பா or
  classical உரை found later takes precedence over it.

## Gotchas
- Install package **`foma`**, NOT `foma-bin` (empty transitional deb).
- **Project Madurai's Nannūl page was revised upstream after we pinned it** (sha `bfc865ddc2e4…` →
  `b970b4ee13b4…`). The builder now refuses to overwrite `nannul.json` when the parse falls back to
  the supplement for more than two verses, and keeps the verified pin. Adopting the revision is open
  work: diff verse by verse first, as D-024 did for Tholkappiyam.
- **Assert the text is clean, not that a repair ran.** A repair counter cannot see a corruption no
  one wrote a repair for; that is how 21 `?`-for-ஃ verses shipped for three months.
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
  **Tholkappiyam comes from Project Madurai's OWN etext (pmuni0100) since 2026-11-24 (D-024)** — the
  tamilnation.org mirror it replaced was lossy (ஃ as `?`, dropped ொ, glued verses, மரபியல் misfiled),
  and 1,602 verses now replace 1,486. Never repoint it at a mirror.
- **Classical commentary (D-024):** `data/classical/tholkappiyam_eluthu_urai.json` — நச்சினார்க்கினியர்
  on எழுத்ததிகாரம், 480 units with `urai`, `examples` (எ-டு … என வரும்) and footnotes. Its numbers are
  CONTINUOUS, so it is aligned to our verses BY TEXT (`aligned_to`), never by number. Runtime:
  `classical.tholkappiyam_urai(அதிகாரம், இயல், n)`. Guard: `tests/test_urai.py`. Its worked examples are
  fixtures for the round-trip engine (`tests/test_roundtrip.py`, D-025).
- **சொல்லதிகாரம் commentaries (D-027):** `data/classical/tholkappiyam_sol_urai_{nacchinarkkiniyar,ilampuranar}.json`,
  built by `scripts/build_sol_urai.py` from TVA scans on archive.org (CC BY-SA 4.0). **OCR, not proof-read**:
  every unit carries `pages[].leaf`; quote a passage in a rule only after reading it against the scan
  and adding it to `data/classical/verified_quotations.json`. Runtime:
  `classical.tholkappiyam_urai("சொல்லதிகாரம்", இயல், n, commentator=…)` (default நச்சினார்க்கினியர்).
  The scans and raw OCR are mirrored in the design repo `sources/classical/sol-urai/` (not in git; see
  its README). Guard: `tests/test_sol_urai.py`.
- **Grammar rule tables:** `data/grammar/*.json` — each with `source_priority` + நூற்பா citations.
  `punarchi.json` holds the JOIN rules the round-trip uses (`core/punarchi.py`, guard `tests/test_roundtrip.py`).
- **TVA material is CC BY-SA 4.0 (D-021, 2026-11-24)** — derived data may ship with attribution and
  stays share-alike. tamilvu.org is unreliable: read from `archive.org/details/TamilVirtualAcademy`
  when it is down. TVA's annotated corpus of 56 classical texts (word-level lemma + grammar tags) is at
  `tamilvu.org/coresite/download/annotate/*.pdf` (Latha font with a broken ToUnicode map: glyph names
  carry the codepoints, and vowel signs come out in visual order — both mechanically reversible).
- **Design repo (separate, PUBLIC since 2026-08-02):** `~/projects/thamizh-mcp-design` →
  `ief-global/thamizh-mcp-design` — blueprint, DESIGN.md, DECISIONS.md, tamil-grammar.md,
  CODE-STATUS.md, DECODER-AUDIT-D014.md, sources/, thamizh-eval/. Same develop→PR→main flow as here.
  NEVER nest it inside this repo or commit design docs into this one.
