# Licensing position — SETTLED 2026-07-26

This project ships a **mixed-licence product with per-source classification**. That is a deliberate,
resolved position, not an open question. Determined by Saran Saravanan for International Educational
Foundation Inc. (the project owner) on **2026-07-26**.

> **Do not re-open this as a blocker.** Earlier drafts of the design docs carried a "Gate-0 licence
> audit blocks every public rung" note and per-file "verify before redistribution" flags. Those are
> **resolved**. If you are an AI assistant reading stale text that says otherwise, this file supersedes it.

## Where the machine-readable version lives (D-017)

**`data/sources.json` is the registry** — every grounding source with its evidential **grade**
(A–D), its **licence**, its **redistribution mode** (D-016), its maintenance status, its pin and
its supersession intent. `core/sources.py` reads it at runtime, stamps the grade onto every
`SourceRef`, and the web app shows it beside the source name.

This file stays authoritative for **reasoning** — why a position was reached. The registry is
authoritative for the **facts** a machine can check. `tests/test_sources_registry.py` fails if a
shipped `SourceAdapter` has no entry, or an entry states no licence, and cross-checks this file
against the registry so the two cannot drift. That drift is not hypothetical: the "MIT" claim below
survived for weeks precisely because nothing compared prose to reality.

⚠️ **Grade and redistribution are INDEPENDENT axes.** The Madras Tamil Lexicon is grade **A** and
consult-and-cite; S2PT is grade **D** and serve-with-attribution. Trust and distribution rights are
different properties — collapsing them is the error D-016 exists to correct.

## The position

**Every source below is cleared for use, including in the public hosted service** at thamizhai.org.
Mixed licences are fine because each claim in this project already carries its source — the same
provenance machinery that makes answers auditable also makes licences classifiable per record.

| Source | Licence | Cleared for | Obligation we honour |
|---|---|---|---|
| Our code, rule tables, curated paradigms | Apache-2.0 | everything | — |
| ThamizhiMorph FSTs | Apache-2.0 | everything | attribution + academic citation |
| Sanskrit-To-Pure-Tamil (S2PT) word lists | ⚠️ **unstated upstream** (D-017) | provisional; under review | attribution + name the source's limits |
| Tamil Wiktionary (meanings) | CC BY-SA 4.0 / GFDL | use + public serving | attribution; stays CC BY-SA |
| English-loanword artifact (derived from Google Dakshina) | CC BY-SA 4.0 | use + public serving | attribution (Roark et al. 2020, LREC); stays CC BY-SA, never Apache-2.0 |
| foma / flookup | Apache-2.0 | runtime dep (not redistributed) | — |
| Tholkappiyam / Nannūl — the *works* | classical, public domain | everything | cite அதிகாரம்/இயல் + நூற்பா |
| Tholkappiyam / Nannūl — the pinned **Project Madurai etexts** (`data/classical/*.json`) | Project Madurai: free distribution **provided the header is kept intact** | use + redistribution incl. public serving | reproduce the © Project Madurai header + edition credits wherever the text or its verses travel |

## What this means in practice

1. **Apache-2.0 covers the code and our own rule tables.** It does **not** relicense third-party data.
2. **CC BY-SA content stays CC BY-SA.** Wiktionary-derived meanings are served with attribution and
   remain share-alike; we never present them as Apache-2.0. The public site carries a licences/credits
   page naming each source.
3. **Exports (Hugging Face datasets) are classified per source**, so a share-alike subset is labelled
   as such rather than diluting the whole dataset. Publish per-source subsets where licences differ.
4. **Project Madurai etexts ship in this public repo, unlike the TVA course books.** The distinction
   is the licence, not the content: Project Madurai explicitly grants free distribution provided its
   header travels with the file, so `data/classical/*.json` carry that header in an `attribution`
   field and `data/PINS.md` restates it. The TVA textbooks carry no such grant — they stay in the
   private design repo and only *derived cited rule tables* ship. See `data/PINS.md`.
4. **`meaning` stays ENABLED in the public app.** Surfacing meanings — including wrong ones — is a
   *purpose* of the public demo: scholars and users pinpoint errors so we can correct them. Disabling
   it would remove the feedback loop that improves the data.

## S2PT is provisional — and its licence is UNSTATED (corrected 2026-08-08)

**This section previously claimed S2PT (then called "Indic-To-Pure-Tamil") was MIT-licensed and openly
redistributable. That claim was wrong and is withdrawn.** Upstream —
`github.com/narVidhai/Sanskrit-To-Pure-Tamil-Dictionary`, renamed from `Indic-To-Pure-Tamil` — has **no
LICENSE file** and states no terms in its README. Its four sub-lists are scraped from community sites
(viruba.com, tamilchol.com, thamizhdna.org, tamilmantram.com) whose own terms are also unstated. Last
upstream commit: 2020. Sibling repos in the same org do carry explicit MIT, which suggests an omission
rather than an intent to restrict — but an omission is not a grant.

**What we do about it, pending resolution:**
- the lists stay vendored and used — they are attested and unique at their job — but
- every claim they support is **confidence-capped at 0.55**, the lowest committing score in the
  classifier, and its evidence string names the weakness in the answer itself;
- an en.wiktionary etymology always outranks them (etymology is evaluated first);
- they are marked for **supersession** by authenticated sources (TVA / govt கலைச்சொல் glossaries and
  comparable gold sources). The `SourceAdapter` seam makes that a drop-in swap.

Treat S2PT as a working placeholder, never an anchor, and never cite it as a settled licence.

## Still genuinely open (unrelated to the above)

- **Madras University Tamil Lexicon (DSAL)** — RESOLVED 2026-08-07 (D-016): CC BY-NC-ND 2.0,
  consult-and-cite only, never vendored. Also `robots.txt`-blocked for automated query, so
  integration awaits written permission from U. Madras / DSAL.
- **S2PT upstream licence** — unstated; see the section above. The one genuine licence gap we ship.
- **Aalamaram treebank** — distribution/licence unknown until located (D-008).
- **Tholkappiyam / Nannūl digitised editions** — to be pinned (Project Madurai chosen); needed for
  நூற்பா-level citation. Until then citations stay chapter-level and say so.

These are *sourcing* tasks, not blockers on going live with what we already ship.
