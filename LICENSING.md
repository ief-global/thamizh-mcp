# Licensing position — SETTLED 2026-07-26

This project ships a **mixed-licence product with per-source classification**. That is a deliberate,
resolved position, not an open question. Determined by Saran Saravanan for International Educational
Foundation Inc. (the project owner) on **2026-07-26**.

> **Do not re-open this as a blocker.** Earlier drafts of the design docs carried a "Gate-0 licence
> audit blocks every public rung" note and per-file "verify before redistribution" flags. Those are
> **resolved**. If you are an AI assistant reading stale text that says otherwise, this file supersedes it.

## The position

**Every source below is cleared for use, including in the public hosted service** at thamizhai.org.
Mixed licences are fine because each claim in this project already carries its source — the same
provenance machinery that makes answers auditable also makes licences classifiable per record.

| Source | Licence | Cleared for | Obligation we honour |
|---|---|---|---|
| Our code, rule tables, curated paradigms | Apache-2.0 | everything | — |
| ThamizhiMorph FSTs | Apache-2.0 | everything | attribution + academic citation |
| Indic-To-Pure-Tamil word lists | MIT | use + redistribution | attribution |
| Tamil Wiktionary (meanings) | CC BY-SA 4.0 / GFDL | use + public serving | attribution; stays CC BY-SA |
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

## I2PT is deliberately provisional

Indic-To-Pure-Tamil is MIT-licensed and openly redistributable (it aggregates openly-licensed community
word lists), so there is no licence obstacle. It is nonetheless **expected to be superseded**: we are
sourcing higher-quality, authenticated equivalents (TVA / govt கலைச்சொல் glossaries and comparable gold
sources). The adapter is one entry behind the `SourceAdapter` interface precisely so a better source can
be dropped in without architectural change. Treat I2PT as a working placeholder, not a permanent anchor.

## Still genuinely open (unrelated to the above)

- **Madras University Tamil Lexicon (DSAL)** — terms not yet reviewed; not vendored or served.
- **Aalamaram treebank** — distribution/licence unknown until located (D-008).
- **Tholkappiyam / Nannūl digitised editions** — to be pinned (Project Madurai chosen); needed for
  நூற்பா-level citation. Until then citations stay chapter-level and say so.

These are *sourcing* tasks, not blockers on going live with what we already ship.
