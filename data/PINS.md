# Anchor version pins (blueprint §4 — reproducibility is part of authenticity)

| Anchor | Pin | Retrieved | Licence |
|---|---|---|---|
| ThamizhiMorph FSTs (`data/fst/*.fst`) | github.com/sarves/thamizhi-morph @ `adbacceda5e8aa902e4b6ed58a3edf5f78cd46fb` | 2026-07-02 | Apache-2.0 |
| foma / flookup | 0.10.0 (Ubuntu jammy debs in `data/vendor/`) | 2026-07-02 | Apache-2.0 |

Citation: Sarveswaran, K., Dias, G., Butt, M. "ThamizhiMorph: A morphological parser for the Tamil
language", Machine Translation (Springer) 2021. DOI 10.1007/s10590-021-09261-5.

Sandbox note (no root): extract debs to ~/local and export
`PATH=$HOME/local/usr/bin:$PATH LD_LIBRARY_PATH=$HOME/local/usr/lib/x86_64-linux-gnu`.

Smoke test (2026-07-02): மரம்→`மரம்+noun+nom`; மரத்தில்→`மரம்+noun+infInc+loc|soc` (both analyses kept).

| Sanskrit-To-Pure-Tamil (S2PT) CSVs (`data/equivalents/sanskrit-to-pure-tamil/`) | github.com/narVidhai/**Sanskrit-To-Pure-Tamil-Dictionary** @ `f734646675579d3d3eb8d44b288f6a13701feaa9` | 2026-07-02 | ⚠️ **LICENCE UNSTATED — corrected 2026-08-08 (D-017).** Upstream has NO LICENCE file and no licence statement; last upstream commit 2020. Its own upstreams are four scraped community sites with unstated terms. This table previously said "MIT — cleared for use and redistribution"; **no basis for that was found.** PROVISIONAL: confidence-capped in `core/classifier.py`, supersession tracked in LICENSING.md. |

| English-loanword artifact (`data/loanwords/english_loans.json`) | Derived from **Google Dakshina v1.0** (2020-05-27) + `dwyl/english-words`; built 2026-08-08 by `scripts/build_english_loans.py` (source checksums inside the artifact's `_meta`) | 2026-08-08 | **CC BY-SA 4.0** — inherited from Dakshina, **NOT Apache-2.0**, never relicensed. Attribution travels with every claim. Wordlist is Unlicense. Rebuild/verify: `--verify`. |

## Classical grammar texts (D-011) — pinned 2026-08-02

### ⚠️ Running heads absorbed into Nannūl verses — 2 ruled, 15 awaiting ruling

Project Madurai's Nannūl text sometimes carries the NEXT section's subject word at the end of the
preceding நூற்பா. This matters now that the runtime QUOTES verses to users (D-018).

**Ruled 2026-08-08 (Saran):** நூற்பா **133** (trailing `பகுதி`) and **140** (trailing `இடைநிலை`) are
running heads and are trimmed by `scripts/build_classical.py`. நூற்பா **142** is GENUINE — its
trailing `இடைநிலை` is the verse's own predicate (`…தரும் தொழில் இடைநிலை`) — and must never be trimmed.

**No heuristic can separate these**, which is why the trim list is curated per verse: the
discriminator is whether the verse's sentence completes without the term, a reading judgement.

The remaining candidates are **NOT trimmed** pending ruling — quoting one extra word is a smaller
error than silently deleting scripture. The verdict column is *our reading, offered as a proposal*,
not an authority:

| நூற்பா | trailing term | our reading | verse tail |
|---|---|---|---|
| 1 | `பாயிரம்` | **GENUINE?** | …ை நூன்முகம் புறவுரை தந்துரை புனைந்துரை பாயிரம் |
| 3 | `பாயிரம்` | **GENUINE?** | …்றாம் ஐந்தும் எல்லாநூற்கும் இவை பொதுப் பாயிரம் |
| 61 | `பெயர்` | **TRIM?** | …ு விரி ஒன்று ஒழி முந்நூற்று எழுபான் என்ப பெயர் |
| 139 | `விகுதி` | **GENUINE?** | …விளம்பிய பகுதி வேறு ஆதலும் விதியே விகுதி |
| 143 | `இடைநிலை` | **GENUINE** | … இடத்தின் ஐம்பால் நிகழ்பொழுது அறை வினை இடைநிலை |
| 145 | `வடமொழியாக்கம்` | **TRIM?** | …திர்மறை மும்மையும் ஏற்கும் ஈங்கே வடமொழியாக்கம் |
| 151 | `புணர்ப்பே` | **GENUINE** | …ரு மொழிகள் இயல்பொடு விகாரத்து இயைவது புணர்ப்பே |
| 181 | `அல்வழி` | **GENUINE?** | …வன்தொடர் அல்லன முன்மிகா அல்வழி |
| 182 | `வேற்றுமை` | **TRIM?** | …ின் மிகாநெடில் உயிர்த்தொடர் முன்மிகா வேற்றுமை |
| 203 | `வேற்றுமை` | **GENUINE?** | …ம் அட்டு உறின் ஐ கெட்டு அந்நீள்வுமாம் வேற்றுமை |
| 242 | `சாரியை` | **TRIM?** | …்கும் மன் அப்பெயர் வேற்றுமைப் புணர்ப்பே சாரியை |
| 274 | `சொல்` | **GENUINE?** | …னும் ஈர் எழுத்தானும் இயைவன வடசொல் பெயர்ச் சொல் |
| 290 | `வேற்றுமை` | **TRIM?** | … பிறிதைத் தொல்முறை உரைப்பன ஆகு பெயரே வேற்றுமை |
| 291 | `வேற்றுமை` | **GENUINE** | … ஈறாய்ப் பொருள் வேற்றுமை செய்வன எட்டே வேற்றுமை |
| 322 | `வினை` | **GENUINE** | …ி ஒன்றற்கு உரியவும் பொதுவும் ஆகும் முற்று வினை |

To rule one: add it to `NANNUL_RUNNING_HEADS` in `scripts/build_classical.py`, re-run the build, and
re-sync any verbatim quote in `data/grammar/concept_map.json` (the citation guard will fail until you
do, which is intended).


Built by `scripts/build_classical.py` into `data/classical/{tholkappiyam,nannul}.json`. Re-run with
`--verify` to detect upstream drift; the `source_sha256` below is over the raw fetched bytes.

| Anchor | Pin | Retrieved | Licence |
|---|---|---|---|
| Tholkappiyam — எழுத்ததிகாரம் | tamilnation.org/literature/grammar/mp100a · sha256 `22f70b3d7547…` | 2026-08-02 | Project Madurai — free distribution with header intact |
| Tholkappiyam — சொல்லதிகாரம் | tamilnation.org/literature/grammar/mp100b · sha256 `ab144c62aeb4…` | 2026-08-02 | ″ |
| Tholkappiyam — பொருளதிகாரம் | tamilnation.org/literature/grammar/mp100c · sha256 `a99c78000a86…` | 2026-08-02 | ″ |
| Nannūl — primary (rev. 2021-08-31) | projectmadurai.org/pm_etexts/utf8/pmuni0147.html · sha256 `bfc865ddc2e4…` | 2026-08-02 | ″ |
| Nannūl — supplement (rev. 2002-05-15), gap-fill only | projectmadurai.org/pm_etexts/utf8/pmuni0152.html · sha256 `fde8734d0b8b…` | 2026-08-02 | ″ |

Attribution (required, travels with the text — reproduced in both artifacts):

> © Project Madurai 1999-2001. Project Madurai is an open, voluntary, worldwide initiative devoted
> to preparation of electronic texts of tamil literary works and to distribute them free on the
> Internet. Details at http://www.projectmadurai.org — You are welcome to freely distribute this
> file, provided this header page is kept intact.

Edition credits: Tholkappiyam — etext Dr. K. Kalyanasundaram, proof-reading N. D. Logasundaram.
Nannūl — etext Dr. Thomas Malten (Univ. of Köln), conforming to the edition of Mani
Thirunavukkarasu Mudaliar (Vavilla Ramasamy Sastrulu & Sons, Madras, 1926); proof-reading
N. D. Logasundaram.

**Coverage.** Tholkappiyam 1486 நூற்பா across 3 அதிகாரம் / 26 இயல்; the grammar-critical இயல்
(எழுத்ததிகாரம்/புணரியல், சொல்லதிகாரம்/வேற்றுமையியல்) are gap-free. Four verses elsewhere in
பொருளதிகாரம்/வினையியல் remain unextracted; see the `coverage` block in the artifact.
**Nannūl is complete — all 462.** நூற்பா 73 and 176 are absent from the primary etext (72→74,
175→177) and are filled from Project Madurai's older Nannūl page, marked per-verse in
`supplemented`. The primary is deliberately NOT switched: pmuni0147 is the 2021 revision with
modern word-split orthography, pmuni0152 is 2002 with the older joined orthography, so those two
verses differ in style from the rest by design rather than by accident.

**Page furniture.** The Nannūl source's markup leaks into verse text in three ways, all stripped by
the build and guarded by `tests/test_citations.py`: the table of contents mimics verse openers
(`1.0 …`), section headings repeat mid-body with verse ranges (`2. எழுத்ததிகாரம் 56 - 257`) and
would otherwise OVERWRITE the real நூற்பா 2 and 3, and the colophon + webpage footer are glued onto
நூற்பா 462. The colophon (`நன்னூல் முற்றிற்று`) is kept as artifact metadata — not as a verse,
since Nannūl has exactly 462.

**Upstream repair.** The three Tholkappiyam pages declare `charset=windows-1252` while serving UTF-8;
the mis-transcode baked U+FFFD into the text. `build_classical.py` repairs it mechanically — every
Tamil-context U+FFFD is **ஃ** (the only character that transcode lost: அஃறிணை, னஃகான், அஃது,
ஒன்பஃது) and the header one is ©. 25 ஃ and 3 © restored; counts recorded in the artifact. No other
substitution is made. Nannūl needed no repair.

⚠️ **Numbering.** Tholkappiyam நூற்பா RESTART per இயல் — always cite அதிகாரம் › இயல் › நூற்பா.
Nannūl is continuous 1–462, so a bare number suffices. **Secondary sources renumber:** the TVA
course books give the இர்/ஈர் verse as 336 and the தெரிநிலை-வினை verse as 319, where this edition
has **337** and **320**. `tests/test_citations.py` enforces that every cited verse resolves here.
