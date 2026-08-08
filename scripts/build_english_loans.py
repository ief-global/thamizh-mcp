#!/usr/bin/env python3
"""Build the pinned English-loanword artifact from Google Dakshina + a public-domain wordlist.

Produces `data/loanwords/english_loans.json`: Tamil word -> (attested English romanization, count).

WHY THIS WORKS. Origin classification's weakest branch is native-by-default — an *absence* of
evidence dressed as a finding. Orthography can prove a word is NOT native but never names a source
language. Dakshina supplies the missing positive evidence: it is a human-annotated lexicon of Tamil
words with their attested romanizations, and for a borrowing the romanization speakers write is
often the English source word itself (ஸ்கூல் -> "school"). If a Tamil word's attested romanization
is a real English word, that is evidence of an English source — not a guess.

    uv run python scripts/build_english_loans.py           # rebuild from the network
    uv run python scripts/build_english_loans.py --verify  # rebuild to temp and diff

TWO FILTERS DO THE REAL WORK, and both were chosen by measurement, not taste:

1. **The orthographic gate.** Only words that FAIL a Tholkappiyam முதல்/இறுதி எழுத்து rule or carry
   a Grantha letter are admitted. Ungated, the method is unsafe: it fires on 15 of 56 native words
   in the 108-word sweep — கால் -> "call", கை -> "kai", தீ -> "thee", and worst, கார் -> "car"(4),
   a word Saran ruled must lead native. The gate is not a tidiness measure; without it this
   artifact would manufacture confident-wrong answers on core vocabulary. It also shrinks the
   artifact from 30,000 candidate words to ~4,000.
2. **A minimum attestation count of 2.** Single-annotator romanizations include phonetic
   coincidences — ஆயுட் (Sanskrit āyus) -> "out"(1) would have become a confident English loan.
   Dropping to >=2 costs one real hit in our sweep (ரேடியோ -> "radio"(1)) and removes ~326
   unaudited single-attestation entries. This project treats a confident-wrong as the release
   blocker and an honest unknown as the design rule working, so the trade goes that way.

S2PT வடசொல் headwords are excluded, because Sanskrit borrowings that English also borrowed (ராஜா ->
"raja") are in the English wordlist and would otherwise be relabelled as English loans.

LICENCES (per-source, D-012 mixed-licence model; recorded in data/PINS.md and LICENSING.md):
  · Google Dakshina v1.0 — CC BY-SA 4.0. Redistributable WITH attribution; the derived artifact
    inherits share-alike and is marked so in its own header. Never relicensed as Apache-2.0.
  · dwyl/english-words — Unlicense (public domain). No obligation, credited anyway.
Only the DERIVED mapping ships, not either corpus: 765 rows, ~20 KB.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "data" / "loanwords" / "english_loans.json"

DAKSHINA_URL = "https://storage.googleapis.com/gresearch/dakshina/dakshina_dataset_v1.0.tar"
DAKSHINA_MEMBERS = "dakshina_dataset_v1.0/ta/lexicons/"
WORDLIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"

MIN_ATTESTATIONS = 2
MIN_EN_LEN = 3          # 2-letter strings collide with Tamil romanizations far too readily
UA = "ThamizhMCP-build/0.1 (nonprofit Tamil grammar research; contact: saravanan3@duck.com)"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def _dakshina_tamil_lexicon() -> tuple[dict[str, list[tuple[str, int]]], str]:
    """Stream the 2 GB tar and keep only ta/lexicons/*.tsv — the whole archive is never stored."""
    print(f"  fetching {DAKSHINA_URL} (streaming; only ta/lexicons is retained)", file=sys.stderr)
    req = urllib.request.Request(DAKSHINA_URL, headers={"User-Agent": UA})
    lex: dict[str, list[tuple[str, int]]] = {}
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=1800) as resp:
        with tarfile.open(fileobj=resp, mode="r|") as tar:   # r| = true streaming, no seek
            for member in tar:
                if not (member.name.startswith(DAKSHINA_MEMBERS) and member.name.endswith(".tsv")):
                    continue
                data = tar.extractfile(member).read()
                digest.update(data)
                for line in data.decode("utf-8").splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3 and parts[2].strip().isdigit():
                        lex.setdefault(parts[0], []).append((parts[1].lower(), int(parts[2])))
    return lex, digest.hexdigest()


def _s2pt_headwords() -> set[str]:
    """வடசொல் headwords — excluded, so a Sanskrit word English also borrowed is not relabelled."""
    import csv
    from thamizh_mcp import config
    out: set[str] = set()
    for name in config.S2PT_SUBLISTS:
        p = config.EQUIVALENTS_DIR / name
        if not p.exists():
            continue
        for row in csv.DictReader(io.open(p, encoding="utf-8")):
            if (k := (row.get("INDIC") or "").strip()):
                out.add(k)
    return out


def build() -> dict:
    from thamizh_mcp.core.classifier import (
        forbidden_final, forbidden_initial, grantha_letters_in,
    )

    lex, dakshina_sha = _dakshina_tamil_lexicon()
    print(f"  Dakshina Tamil lexicon: {len(lex)} words", file=sys.stderr)

    wl_bytes = _fetch(WORDLIST_URL)
    english = {w.strip().lower() for w in wl_bytes.decode("utf-8", "replace").splitlines()
               if len(w.strip()) >= MIN_EN_LEN}
    print(f"  English wordlist: {len(english)} words", file=sys.stderr)

    s2pt = _s2pt_headwords()

    def orthography_proves_non_native(w: str) -> bool:
        """The gate. These rules prove NON-nativeness only — which is exactly what licenses us to
        then ask WHICH language (D-015). They never assert a source themselves."""
        return bool(grantha_letters_in(w)) or bool(forbidden_initial(w)) or bool(forbidden_final(w))

    loans: dict[str, list] = {}
    for word, romanizations in lex.items():
        if word in s2pt or not orthography_proves_non_native(word):
            continue
        hits = sorted(((r, n) for r, n in romanizations
                       if r in english and n >= MIN_ATTESTATIONS), key=lambda x: -x[1])
        if hits:
            loans[word] = [hits[0][0], hits[0][1]]

    return {
        "_meta": {
            "description": "Tamil word -> attested English romanization. Positive evidence of an "
                           "English source for origin classification.",
            "built_by": "scripts/build_english_loans.py",
            "min_attestations": MIN_ATTESTATIONS,
            "gate": "only words failing a Tholkappiyam முதல்/இறுதி எழுத்து rule or carrying a "
                    "Grantha letter are included — the rules prove NON-nativeness, which is what "
                    "licenses naming a source language (D-015). Ungated the method mislabels "
                    "native words (கார் -> car).",
            "excluded": "S2PT வடசொல் headwords, so Sanskrit words English also borrowed (ராஜா -> "
                        "raja) are not relabelled English.",
            "licence": "CC BY-SA 4.0 — inherited from Google Dakshina. NOT Apache-2.0. Attribution "
                       "travels with any claim derived from this file.",
            "sources": [
                {"name": "Google Dakshina v1.0", "ref": DAKSHINA_URL,
                 "licence": "CC BY-SA 4.0",
                 "citation": "Roark et al. 2020, Processing South Asian Languages Written in the "
                             "Latin Script: the Dakshina Dataset (LREC 2020)",
                 "lexicon_sha256": dakshina_sha},
                {"name": "dwyl/english-words", "ref": WORDLIST_URL, "licence": "Unlicense",
                 "sha256": hashlib.sha256(wl_bytes).hexdigest()},
            ],
            "entries": len(loans),
        },
        "loans": dict(sorted(loans.items())),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="rebuild and diff against the committed artifact instead of writing it")
    args = ap.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "src"))
    artifact = build()
    text = json.dumps(artifact, ensure_ascii=False, indent=1, sort_keys=False) + "\n"

    if args.verify:
        if not OUT.exists():
            print(f"MISSING: {OUT}", file=sys.stderr)
            return 1
        current = OUT.read_text(encoding="utf-8")
        cur_loans = json.loads(current)["loans"]
        new_loans = artifact["loans"]
        if cur_loans == new_loans:
            print(f"OK — {len(new_loans)} entries, mapping identical to the committed artifact")
            return 0
        added = set(new_loans) - set(cur_loans)
        removed = set(cur_loans) - set(new_loans)
        print(f"DRIFT — committed {len(cur_loans)} vs rebuilt {len(new_loans)}; "
              f"+{len(added)} -{len(removed)}", file=sys.stderr)
        for w in sorted(added)[:15]:
            print(f"  + {w} -> {new_loans[w]}", file=sys.stderr)
        for w in sorted(removed)[:15]:
            print(f"  - {w} -> {cur_loans[w]}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} — {artifact['_meta']['entries']} entries "
          f"({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
