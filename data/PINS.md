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

| Indic-To-Pure-Tamil CSVs (`data/equivalents/indic-to-pure-tamil/`) | github.com/narVidhai/Indic-To-Pure-Tamil @ `f734646675579d3d3eb8d44b288f6a13701feaa9` | 2026-07-02 | MIT (verify in repo) |
