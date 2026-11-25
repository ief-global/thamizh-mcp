#!/usr/bin/env python3
"""Pin தேவநேயப் பாவாணர்'s books from TVA's archive.org collection (D-031).

Saran, 2026-11-25: பாவாணர்'s work is authoritative, and his statements break ties where our other
sources disagree or are silent. Three books are pinned, all scans from the Tamil Digital Library in
archive.org's TamilVirtualAcademy collection (CC BY-SA 4.0, D-021):

  kalanjiyam25  பாவாணர் தமிழ்க் களஞ்சியம் 25: இயற்றமிழ் இலக்கணம் (தமிழ்மண் அறக்கட்டளை)
                — his grammar. The pages a rule cites are excerpted into
                data/classical/pavanar_iyatramil_ilakkanam.json.
  kalanjiyam19  பாவாணர் தமிழ்க் களஞ்சியம் 19: வேர்ச்சொற் கட்டுரைகள் 3 — his root-word essays.
  eluthu1972    தொல்காப்பியம் எழுத்ததிகாரம், நச்சினார்க்கினியர் உரை, with his footnotes (கழகம், 1972).

As with the Nannūl commentaries, only pages a verified quotation cites are stored in this repo; a
book with no cited page yet is pinned by checksum and mirrored in full in the design repo
(sources/classical/pavanar/), so a later rule can cite it without depending on archive.org.

    uv run python scripts/build_pavanar.py                     # from archive.org
    uv run python scripts/build_pavanar.py --mirror DIR        # from a local copy
    uv run python scripts/build_pavanar.py --verify [--mirror DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sol_urai as sol  # noqa: E402  (shares the pinned-fetch and OCR readers)

SOURCES = {
    "kalanjiyam25": {
        "archive_id": "tdl.48547-25",
        "stem": "TVA_BOK_0048547_பாவாணர்_தமிழ்க்_களஞ்சியம்_25",
        "mirror_stem": "kalanjiyam25",
        "title": "பாவாணர் தமிழ்க் களஞ்சியம் 25: இயற்றமிழ் இலக்கணம்",
        "scan_pdf": {"sha256": "210d80888e06a329e9284812ee02681a379406b4b195750c20304c7334fcda0a",
                     "md5": "a29655191c11b57aac365df39e59afcc", "bytes": 3167501},
        "sha256": {
            "djvu.xml": "75451b84f4d99bd111d7d1470cb3defea435ebd3611b0ec14ef989abf610bfb5",
            "page_numbers.json": "e9bd60aea79dea0f5acef8000b8c33faf763750e4b753060bf818cba5d71c07a",
        },
        "artifact": "pavanar_iyatramil_ilakkanam",
        # The leaves a quotation in data/classical/verified_quotations.json cites. Add a leaf here
        # before citing a passage on it, then rebuild.
        "leaves": {
            49: "§104: the past-tense இடைநிலை; இன் appears as ன் with its first letter dropped (போனான்)",
            54: "§116: the வினையெச்ச விகுதி (உ, இ, ய் past; அ present; இன் future)",
            83: "§57: சந்தி is the letter that appears where the பகுதி meets the next part (படித்தான், வந்தான்)",
            84: "§60: விகாரம் is the change in the பகுதி (வா → வ)",
        },
    },
    "kalanjiyam19": {
        "archive_id": "tdl.48510-19-3",
        "stem": "TVA_BOK_0048510_பாவாணர்_தமிழ்க்_களஞ்சியம்_19",
        "mirror_stem": "kalanjiyam19",
        "title": "பாவாணர் தமிழ்க் களஞ்சியம் 19: வேர்ச்சொற் கட்டுரைகள் 3",
        "scan_pdf": {"sha256": "f9788f679849a5043837b3ec095d4268f6a37351ed773723db7b33b4bb14ebc5",
                     "md5": "dc455ccc370c3e9317fdf4f7ff24e477", "bytes": 3982121},
        "sha256": {
            "djvu.xml": "742d102db8f9fd3aa32c5cfbf046b9c3e2ee6b8e376a2b3f4f2f4fdc06048cb5",
            "page_numbers.json": "11e4170be590507efd1c872483ab0e7deb63f3010eeff718a95ad41a580824d2",
        },
    },
    "eluthu1972": {
        "archive_id": "dli.jZY9lup2kZl6TuXGlZQdjZMdl0Uy",
        "stem": "TVA_BOK_0006701_தொல்காப்பியம்_எழுத்ததிகாரம்",
        "mirror_stem": "eluthu1972",
        "title": "தொல்காப்பியம் எழுத்ததிகாரம், நச்சினார்க்கினியர் உரை, பாவாணர் அடிக்குறிப்புகளுடன் (1972)",
        "scan_pdf": {"sha256": "0ffd2fa2e02a0e47ca506360086215db09a40b53ae249cf39c7e8f5e15e2a70b",
                     "md5": "ea6ac945c00330be137c49820a040eb5", "bytes": 395251979},
        "sha256": {
            "djvu.xml": "161eb84f2a1a81069004490d30e4f0b520e72c043acfe79ef6d4639837205c7a",
            "page_numbers.json": "5db55fa17a3bf972f9b86d64a61f7c9bc8bd17a8caa96e3b29b7a1dbb53e0d14",
        },
    },
}

ATTRIBUTION = ("Scan: Tamil Digital Library, Tamil Virtual Academy, Government of Tamil Nadu, via "
               "archive.org/details/TamilVirtualAcademy (CC BY-SA 4.0). Author: ஞா. தேவநேயப் பாவாணர். "
               "Edition: பாவாணர் தமிழ்க் களஞ்சியம், தமிழ்மண் அறக்கட்டளை. Text: archive.org OCR of the "
               "cited pages only; not proof-read.")


def build(key: str, mirror: Path | None) -> dict | None:
    """Check every pinned file of one book; return its excerpt artifact, or None if it has none."""
    src = SOURCES[key]
    xml, pin_xml = sol.fetch(src, "djvu.xml", mirror)
    pn_raw, pin_pn = sol.fetch(src, "page_numbers.json", mirror)
    leaves = src.get("leaves")
    if not leaves:
        return None
    printed = {p["leafNum"]: (p.get("pageNumber") or "").strip("()") or None
               for p in json.loads(pn_raw)["pages"]}
    text: dict[int, list[str]] = {}
    for leaf, t in sol.ocr_lines(xml):
        t = t.replace("‌", "")
        if leaf in leaves and t.strip():
            text.setdefault(leaf, []).append(t)
    missing = sorted(set(leaves) - set(text))
    if missing:
        raise SystemExit(f"{key}: no OCR text on leaves {missing}")
    return {
        "text": src["title"],
        "author": "ஞா. தேவநேயப் பாவாணர்",
        "edition": {"series": "பாவாணர் தமிழ்க் களஞ்சியம்", "publisher": "தமிழ்மண் அறக்கட்டளை, சென்னை",
                    "archive_org": f"https://archive.org/details/{src['archive_id']}"},
        "attribution": ATTRIBUTION,
        "licence": "CC BY-SA 4.0 (Tamil Virtual Academy collection, D-021); share-alike. Excerpts of the "
                   "cited pages only.",
        "role": "Saran, 2026-11-25 (D-031): பாவாணர்'s statements are authoritative and break ties where "
                "the other sources disagree or are silent.",
        "ocr": {"engine": "archive.org derive OCR (_djvu.xml)", "proof_read": False,
                "warning": "OCR text of the cited leaves only. Check any quotation against the scan "
                           "page before a rule cites it (data/classical/verified_quotations.json)."},
        "sources": [pin_xml, pin_pn],
        "scan": {"file": f"{src['stem']}.pdf", **src["scan_pdf"],
                 "note": "the page images (a typeset PDF; render pages to read them)"},
        "excerpts": [{"leaf": lf, "printed": printed.get(lf), "cited_for": leaves[lf],
                      "text": "\n".join(text[lf])} for lf in sorted(leaves)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", type=Path)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    status = 0
    for key, src in SOURCES.items():
        art = build(key, a.mirror)
        if art is None:
            print(f"ok (pinned, no page cited yet): {key}")
            continue
        out = sol.OUT_DIR / f"{src['artifact']}.json"
        blob = json.dumps(art, ensure_ascii=False, indent=1) + "\n"
        if a.verify:
            same = out.exists() and out.read_text("utf-8") == blob
            print(("ok: " if same else "DRIFT: ") + str(out))
            status |= 0 if same else 1
        else:
            out.write_text(blob, "utf-8")
            print(f"wrote {out} ({len(blob)} bytes)")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
