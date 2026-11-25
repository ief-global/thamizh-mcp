#!/usr/bin/env python3
"""Build the classical commentaries on தொல்காப்பியம் சொல்லதிகாரம் from their pinned scans (D-027).

Two commentaries, each a Tamil Digital Library scan held in TVA's archive.org collection (CC BY-SA
4.0 under D-021):

  · நச்சினார்க்கினியர் உரை — சரசுவதி மகால் நூலகம், தஞ்சாவூர், 1999 (same commentator as the
    எழுத்ததிகாரம் உரை pinned in D-024, so the three அதிகாரம் read uniformly)
  · இளம்பூரணர் உரை — தமிழ்ப் பல்கலைக்கழகம், தஞ்சாவூர், 1988 (the earliest commentator)

The text is archive.org's OCR (`_djvu.xml`), NOT a proof-read etext. So every unit carries the scan
leaf and printed page it came from, and anything quoted from it must be checked against the page
image before a rule cites it. The OCR is pinned by sha256 like every other source; the scan PDFs are
pinned by sha256 too (data/PINS.md) and mirrored outside git.

Each commentary is aligned to OUR verses (data/classical/tholkappiyam.json) BY TEXT. The editions
number their நூற்பா continuously and the OCR loses about a third of the headings, so a number is
never used as a key. Alignment: every verse's consonant skeleton votes for its positions in the
OCR stream (4-gram hits), the best candidates are scored with difflib, and the highest-scoring
monotonic chain is kept. Short verses the chain misses are searched for between their aligned
neighbours. Nothing is forced: a verse with no match ≥ the threshold is listed as unaligned.

    uv run python scripts/build_sol_urai.py                      # from archive.org
    uv run python scripts/build_sol_urai.py --mirror DIR         # from a local copy of the pins
    uv run python scripts/build_sol_urai.py --verify [--mirror DIR]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "classical"
THOLKAPPIYAM = OUT_DIR / "tholkappiyam.json"
UA = "thamizh-mcp/0.1 (+https://github.com/ief-global/thamizh-mcp) classical-text pinning"

ATTRIBUTION = (
    "Scan: Tamil Digital Library (tamildigitallibrary.in), Tamil Virtual Academy, Government of "
    "Tamil Nadu, via archive.org/details/TamilVirtualAcademy. Tamil Virtual Academy material is "
    "licensed CC BY-SA 4.0. Text: archive.org OCR of that scan, aligned by thamizh-mcp; not "
    "proof-read. Derived data is share-alike (CC BY-SA 4.0), never Apache-2.0."
)

SOURCES = {
    "nacchinarkkiniyar": {
        "artifact": "tholkappiyam_sol_urai_nacchinarkkiniyar",
        "commentator": "நச்சினார்க்கினியர்",
        "title": "தொல்காப்பியம் - சொல்லதிகாரம் : நச்சினார்க்கினியர் உரையுடன்",
        "publisher": "சரசுவதி மகால் நூலகம், தஞ்சாவூர்",
        "year": 1999,
        "archive_id": "dli.jZY9lup2kZl6TuXGlZQdjZM3kZpy.TVA_BOK_0008472",
        "tdl_book_id": "jZY9lup2kZl6TuXGlZQdjZM3kZpy",
        "stem": "TVA_BOK_0008472_தொல்காப்பியம்_-_சொல்லதிகாரம்",
        "mirror_stem": "nacchinarkkiniyar",
        "end_of_text": r"எச்ச\s*வியன்\s*முற்றும்|சொல்லதிகாரம்\s*முற்றும்",
        "scan_pdf": {"sha256": "8e71d5a3f7b9695374794339c54f7153f88a6bd6e97400c2792f78371ea3670d",
                     "md5": "856dfa5e08b480b9da233d428fd25860", "bytes": 267617873},
        "sha256": {
            "djvu.xml": "a9e7819f5b9e2581f5f3726a8a6689ca47d8062b922d1ddcb98ede19e6539ec0",
            "page_numbers.json": "a6be52bceec7cf02ccbb22dc65d8d6652d9992eaa550878934161467ddc9a99e",
        },
    },
    "ilampuranar": {
        "artifact": "tholkappiyam_sol_urai_ilampuranar",
        "commentator": "இளம்பூரணர்",
        "title": "தொல்காப்பியம் : சொல்லதிகாரம் இளம்பூரணர் உரை",
        "publisher": "தமிழ்ப் பல்கலைக்கழகம், தஞ்சாவூர்",
        "year": 1988,
        "archive_id": "dli.jZY9lup2kZl6TuXGlZQdjZMdlupy",
        "tdl_book_id": "jZY9lup2kZl6TuXGlZQdjZMdlupy",
        "stem": "TVA_BOK_0006575_தொல்காப்பியம்",
        "mirror_stem": "ilampuranar",
        "end_of_text": r"சொல்லதிகாரம்\s*உண்மைப்\s*பொருளும்",
        "scan_pdf": {"sha256": "3a731b6b3f44b475a205faea2e9e120b56f100e49686ff80f3b6905fdfb1712d",
                     "md5": "5f53317cf2baf13a9aa9ca93a2630878", "bytes": 211340206},
        "sha256": {
            "djvu.xml": "92f1d32b660acecaa996c6cdb2316157cc2195195fcd3031ab2164d5214440ae",
            "page_numbers.json": "ae3c88f34e056b6d53d43fe6bcb9ba5162e80d596e49c99d06cca3ef3437eb88",
        },
    },
}

CONS = re.compile(r"[க-ஹ]")
TAMIL = re.compile(r"[஀-௿]")
K = 4                       # n-gram length for candidate voting
MATCH_MIN = 0.6             # a chain match must reach this skeleton similarity
GAPFILL_MIN = 0.75          # a short verse found between its neighbours must reach this
HEADING_BONUS = 0.15        # preference for a match that starts at the edition's own heading
_HEADING = re.compile(r"^\[?\s*(\d{1,3})\s*[\].,]\s*(.*)$")
_COMMENTARY_START = re.compile(
    r"^(\(?\s*)?(இது|இஃது|இவை|இதுவும்|இவையும்|எ\s*\.{2,}\s*ன்|என்\s*-\s*னெனின்|\(\s*இ\s*-\s*ள்)")
_FOOTNOTE_START = re.compile(r"^(சு|பா)\s*\.?\s*வே\s*[;:.,]")
_RUNNING_HEAD = re.compile(r"காப்பியம்|காபபியம்|திகாரம்|^[\[\(]?\s*\S{1,14}\s*[\]\)]?\s*$")


# --- fetching and pinning -----------------------------------------------------------------------

def _read(src: dict, kind: str, mirror: Path | None) -> tuple[bytes, str]:
    if mirror is not None:
        name = f"{src['mirror_stem']}_{kind}"
        return (mirror / name).read_bytes(), f"mirror:{name}"
    url = (f"https://archive.org/download/{src['archive_id']}/"
           + urllib.parse.quote(f"{src['stem']}_{kind}"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), url


def fetch(src: dict, kind: str, mirror: Path | None) -> tuple[bytes, dict]:
    data, _where = _read(src, kind, mirror)
    sha = hashlib.sha256(data).hexdigest()
    pinned = src["sha256"].get(kind)
    if pinned and sha != pinned:
        raise SystemExit(f"PIN MISMATCH for {src['mirror_stem']} {kind}: got {sha}, pinned {pinned}. "
                         "The upstream file changed. Diff it before adopting it (see data/PINS.md).")
    url = f"https://archive.org/download/{src['archive_id']}/{src['stem']}_{kind}"
    return data, {"file": f"{src['stem']}_{kind}", "url": url, "sha256": sha}


# --- OCR → lines --------------------------------------------------------------------------------

def ocr_lines(xml: bytes) -> list[tuple[int, str]]:
    """(leaf, line text) for every OCR line, in reading order."""
    root = ET.fromstring(xml)
    out = []
    for obj in root.iter("OBJECT"):
        m = re.search(r"_(\d{4})\.djvu$", obj.get("usemap", ""))
        leaf = int(m.group(1)) if m else -1
        for ln in obj.iter("LINE"):
            text = " ".join((w.text or "").strip() for w in ln.iter("WORD")).strip()
            if text:
                out.append((leaf, re.sub(r"\s+", " ", text)))
    return out


def clean(lines: list[tuple[int, str]]) -> tuple[list[tuple[int, str]], dict[int, list[str]]]:
    """Drop running heads and page numbers; lift each page's footnotes out of the text."""
    by_leaf: dict[int, list[str]] = defaultdict(list)
    for leaf, t in lines:
        by_leaf[leaf].append(t)
    body, notes = [], {}
    for leaf in sorted(by_leaf):
        page = by_leaf[leaf]
        # Running head: page number, book title, அதிகாரம் name, bracketed இயல் tag. All within the
        # first three lines; a long line is text, never a head.
        k = 0
        while k < min(3, len(page)) and (re.fullmatch(r"\d{1,3}", page[k])
                                         or (len(page[k]) <= 22 and _RUNNING_HEAD.search(page[k]))):
            k += 1
        page = page[k:]
        if page and re.fullmatch(r"\d{1,3}", page[-1]):
            page = page[:-1]
        f = next((i for i, t in enumerate(page) if _FOOTNOTE_START.match(t)), None)
        if f is not None:
            notes[leaf] = page[f:]
            page = page[:f]
        body += [(leaf, t) for t in page]
    return body, notes


# --- alignment ----------------------------------------------------------------------------------

def skeleton(s: str) -> str:
    return "".join(CONS.findall(s))


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _candidates(v: str, idx: dict, sk: str, top: int = 12) -> list[tuple[int, float]]:
    votes: Counter = Counter()
    for o in range(len(v) - K + 1):
        for p in idx.get(v[o:o + K], ()):
            if p >= o:
                votes[(p - o) // 8] += 1
    out: dict[int, float] = {}
    for bucket, _ in votes.most_common(top):
        best = max(((st, _ratio(v, sk[st:st + len(v)]))
                    for st in range(max(0, bucket * 8 - 8), bucket * 8 + 16)), key=lambda x: x[1])
        if best[1] >= MATCH_MIN:
            out[best[0]] = best[1]
    return sorted(out.items())


def align(verses: list[str], sk: str, headed: set[int] | None = None) -> list[tuple[int, float] | None]:
    """Position in the skeleton stream of each verse (or None), monotonic in verse order.

    The commentary QUOTES its verse again inside the உரை, so a verse can match twice. `headed` holds
    the stream positions where an edition heading ('NNN ]', 'NNN .') precedes the text; a match
    there gets a bonus, so the chain prefers the verse block to a later quotation of it."""
    headed = headed or set()
    idx: dict[str, list[int]] = defaultdict(list)
    for p in range(len(sk) - K + 1):
        idx[sk[p:p + K]].append(p)
    skels = [skeleton(v) for v in verses]
    def w(p: int, r: float) -> float:
        return r - 0.5 + (HEADING_BONUS if any(q in headed for q in range(p - 3, p + 4)) else 0.0)

    nodes = [(i, p, r) for i, v in enumerate(skels) for p, r in _candidates(v, idx, sk)]
    nodes.sort(key=lambda x: (x[0], x[1]))
    score, prev = [0.0] * len(nodes), [-1] * len(nodes)
    for k, (i, p, r) in enumerate(nodes):
        score[k] = w(p, r)
        for k2 in range(k):
            i2, p2, _ = nodes[k2]
            if i2 < i and p2 < p and score[k2] + w(p, r) > score[k]:
                score[k], prev[k] = score[k2] + w(p, r), k2
    chosen: dict[int, tuple[int, float]] = {}
    k = max(range(len(nodes)), key=lambda k: score[k]) if nodes else -1
    while k != -1:
        i, p, r = nodes[k]
        chosen[i] = (p, r)
        k = prev[k]
    # Gap-fill: a short verse has too few n-grams to vote; look for it between its neighbours.
    for i, v in enumerate(skels):
        if i in chosen or not v:
            continue
        lo = max((chosen[j][0] for j in chosen if j < i), default=0)
        hi = min((chosen[j][0] for j in chosen if j > i), default=len(sk))
        best = max(((st, _ratio(v, sk[st:st + len(v)])) for st in range(lo + 1, max(lo + 2, hi - len(v)))),
                   key=lambda x: x[1], default=None)
        if best and best[1] >= GAPFILL_MIN:
            chosen[i] = best
    return [chosen.get(i) for i in range(len(verses))]


# --- units --------------------------------------------------------------------------------------

def build_one(key: str, mirror: Path | None) -> dict:
    src = SOURCES[key]
    xml, pin_xml = fetch(src, "djvu.xml", mirror)
    pn_raw, pin_pn = fetch(src, "page_numbers.json", mirror)
    printed = {p["leafNum"]: p.get("pageNumber") or None for p in json.loads(pn_raw)["pages"]}

    body, notes = clean(ocr_lines(xml))
    sk_chars, owner, headed = [], [], set()
    for li, (_, t) in enumerate(body):
        if _HEADING.match(t):
            # இளம்பூரணர் prints 'NNN . verse…' (the verse starts here); நச்சினார்க்கினியர் prints
            # 'NNN ] topic' with the verse on the next line. Mark both places.
            headed.add(len(sk_chars))
            headed.add(len(sk_chars) + len(skeleton(t)))
        for c in CONS.findall(t):
            sk_chars.append(c)
            owner.append(li)
    sk = "".join(sk_chars)

    thol = json.loads(THOLKAPPIYAM.read_text("utf-8"))["athikaram"]["சொல்லதிகாரம்"]
    ours = [(iyal, n, text) for iyal, vs in thol.items() for n, text in vs.items()]
    our_text = {(iyal, n): text for iyal, n, text in ours}
    pos = align([t for _, _, t in ours], sk, headed)
    # The last unit ends at the edition's colophon, not at the end of the book's back matter.
    last = max(owner[h[0]] for h in pos if h)
    end_of_text = next((i for i in range(last, len(body))
                        if re.search(src["end_of_text"], body[i][1])), None)
    if end_of_text is None:
        raise SystemExit(f"{key}: end-of-text marker not found; refusing to let the last unit "
                         "swallow the back matter")
    body = body[:end_of_text]

    starts = []
    for (iyal, n, text), hit in zip(ours, pos):
        if hit is None:
            continue
        li = owner[hit[0]]
        # The edition's own heading: 'NNN ] topic' on the line before (நச்சினார்க்கினியர்), or
        # 'NNN . verse…' on the same line (இளம்பூரணர்).
        head = None
        if li > 0 and _HEADING.match(body[li - 1][1]) and not _COMMENTARY_START.search(body[li - 1][1]):
            head, li = body[li - 1][1], li - 1
        elif _HEADING.match(body[li][1]):
            head = body[li][1]
        starts.append((li, iyal, n, hit[1], head))

    units = []
    for k, (li, iyal, n, r, head) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(body)
        shared = end <= li      # the next verse starts on this same OCR line: printed together
        seg = body[li:max(end, li + 1)]
        texts = [t for _, t in seg]
        # The verse block: from the verse's first line until its consonants are all there. Our
        # verse's length is known, so the OCR block is cut by length, not by guessing where the
        # உரை begins.
        j = 1 if head and head == texts[0] and not TAMIL.search(_HEADING.match(head).group(2) or "") else 0
        need, got, verse = 0.9 * len(skeleton(our_text[(iyal, n)])), 0, []
        while j < len(texts) and got < need:
            verse.append(texts[j])
            got += len(skeleton(texts[j]))
            j += 1
        leaves = sorted({leaf for leaf, _ in seg})
        units.append({
            "aligned_to": {"iyal": iyal, "verse": n},
            "match": round(r, 3),
            "heading": head,
            "verse": " ".join(verse),
            "urai": "\n".join(texts[j:]),
            "pages": [{"leaf": lf, "printed": printed.get(lf)} for lf in leaves],
            "footnotes": [x for lf in leaves for x in notes.get(lf, [])],
            **({"shares_line_with_next": True} if shared else {}),
            **({"urai_in_next_unit": True} if not "\n".join(texts[j:]).strip() else {}),
        })

    aligned = {(u["aligned_to"]["iyal"], u["aligned_to"]["verse"]) for u in units}
    return {
        "text": f"Tholkappiyam, சொல்லதிகாரம், with the commentary of {src['commentator']}",
        "text_ta": src["title"],
        "commentator": src["commentator"],
        "edition": {"publisher": src["publisher"], "year": src["year"],
                    "archive_org": f"https://archive.org/details/{src['archive_id']}",
                    "tamil_digital_library_book_id": src["tdl_book_id"]},
        "attribution": ATTRIBUTION,
        "licence": "CC BY-SA 4.0 (Tamil Virtual Academy material, D-021); share-alike",
        "ocr": {
            "engine": "archive.org derive OCR (_djvu.xml)",
            "proof_read": False,
            "warning": "OCR text. Letters are dropped or misread (e.g. a missing pulli), and verse "
                       "lines can be split or merged. Check any quotation against the scan page "
                       "(`pages[].leaf`) before a rule cites it.",
        },
        "sources": [pin_xml, pin_pn],
        "scan": {"file": f"{src['stem']}.pdf", **src["scan_pdf"],
                 "note": "the page images; not read by the build, pinned so a quotation can be "
                         "checked against the leaf it came from"},
        "numbering": "Keyed by OUR coordinates (`aligned_to`: இயல் + நூற்பா of tholkappiyam.json). "
                     "`heading` is the edition's own heading as OCR'd, kept for reference only; "
                     "its number is never a key.",
        "alignment": {
            "method": "consonant-skeleton 4-gram voting, difflib scoring, highest-scoring monotonic "
                      "chain; short verses searched between aligned neighbours",
            "threshold": MATCH_MIN, "gapfill_threshold": GAPFILL_MIN,
            "aligned": len(units), "our_verses": len(ours),
            "unaligned_ours": [{"iyal": iy, "verse": n} for iy, n, _ in ours if (iy, n) not in aligned],
            "note": "Nothing is forced into a match. An unaligned verse has no unit here; its "
                    "commentary is still in the scan, inside a neighbouring unit's text.",
        },
        "units": units,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", type=Path, help="read the pinned files from this directory")
    ap.add_argument("--verify", action="store_true", help="rebuild and report drift, write nothing")
    ap.add_argument("--only", choices=sorted(SOURCES))
    a = ap.parse_args()
    drift = False
    for key in ([a.only] if a.only else SOURCES):
        data = build_one(key, a.mirror)
        al = data["alignment"]
        print(f"{data['commentator']}: {al['aligned']}/{al['our_verses']} verses aligned; "
              f"unaligned {[(u['iyal'], u['verse']) for u in al['unaligned_ours']]}")
        if al["aligned"] < 450:
            print("REFUSING TO WRITE — alignment regressed.", file=sys.stderr)
            return 1
        blob = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        dest = OUT_DIR / f"{SOURCES[key]['artifact']}.json"
        if a.verify:
            same = dest.exists() and dest.read_text("utf-8") == blob
            drift |= not same
            print(("ok: " if same else "DRIFT: ") + str(dest))
        else:
            dest.write_text(blob, "utf-8")
            print(f"wrote {dest} ({len(blob)} bytes)")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
