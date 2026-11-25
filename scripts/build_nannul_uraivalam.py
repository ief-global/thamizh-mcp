#!/usr/bin/env python3
"""Pin the pages of the Nannūl commentaries that our rules cite (D-029).

நன்னூல் உரைவளம், தொகுதி 5 (பதவியல்), ed. முனைவர் இரா. கண்ணன், உலகத் தமிழாராய்ச்சி நிறுவனம், 2010,
prints every commentator on each பதவியல் நூற்பா side by side: மயிலைநாதர், சங்கர நமச்சிவாயர் with
சிவஞான முனிவர், விசாகப் பெருமாளையர், ஆறுமுக நாவலர் and later ones. It is a Tamil Digital Library
scan in TVA's archive.org collection (tdl.6041-5).

Unlike the சொல்லதிகாரம் commentaries (build_sol_urai.py), the volume is NOT aligned and stored whole.
Only the leaves that a verified quotation cites are excerpted, as archive.org's OCR of that leaf,
so a test can keep each quotation findable on its page. The full volume (scan, OCR, page map) is
mirrored in the design repo at sources/classical/nannul-urai/ and pinned by sha256 here.

    uv run python scripts/build_nannul_uraivalam.py                      # from archive.org
    uv run python scripts/build_nannul_uraivalam.py --mirror DIR         # from a local copy
    uv run python scripts/build_nannul_uraivalam.py --verify [--mirror DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sol_urai as sol  # noqa: E402  (shares the pinned-fetch and OCR readers)

OUT = sol.OUT_DIR / "nannul_uraivalam_padaviyal.json"

SOURCE = {
    "archive_id": "tdl.6041-5",
    "stem": "TVA_BOK_0006041_நன்னூல்_உரைவளம்",
    "mirror_stem": "uraivalam5",
    "scan_pdf": {"sha256": "299da0ea203d88263332a9b78dc0cd794e1ce6edc34173352ba1361202b07196",
                 "md5": "00ecec38b84c29eb8be52c30ce0a6f91", "bytes": 152227490},
    "sha256": {
        "djvu.xml": "3fbda381be962ca92e2b2b5ab917eb84a558e858ba5333a0159c6887c4bdddb3",
        "page_numbers.json": "53a82da4cd8bb4b56c311978f3ee9596d09e455f6a346a02ce04fe08faeffb4e",
    },
}

# The leaves a quotation in data/classical/verified_quotations.json cites. Add a leaf here before
# citing a passage on it, then rebuild.
LEAVES = {
    114: "விசாகப் பெருமாளையர் on நூற்பா 137 (கல் → கற்றான், செல் → சென்றான்)",
    125: "சே. கிருஷ்ணமாசாரியார் on நூற்பா 137 (கல் → கற்றான், கேள் → கேட்டான்)",
    144: "மயிலைநாதர் on நூற்பா 139 (வா, கொள், கொல்/செல்/வெல்)",
    145: "மயிலைநாதர் (cont.) and சங்கர நமச்சிவாயர் – சிவஞான முனிவர் on நூற்பா 139",
}


def build(mirror: Path | None) -> dict:
    xml, pin_xml = sol.fetch(SOURCE, "djvu.xml", mirror)
    pn_raw, pin_pn = sol.fetch(SOURCE, "page_numbers.json", mirror)
    printed = {p["leafNum"]: (p.get("pageNumber") or "").strip("()") or None
               for p in json.loads(pn_raw)["pages"]}
    text: dict[int, list[str]] = {}
    for leaf, t in sol.ocr_lines(xml):
        t = t.replace("‌", "")
        if leaf in LEAVES and t.strip():
            text.setdefault(leaf, []).append(t)
    missing = sorted(set(LEAVES) - set(text))
    if missing:
        raise SystemExit(f"no OCR text on leaves {missing}")
    return {
        "text": "Nannūl, பதவியல் — the classical and later commentaries, as compiled in நன்னூல் உரைவளம் 5",
        "text_ta": "நன்னூல் உரைவளம் (தொகுதி 5) : பதவியல்",
        "edition": {"editor": "முனைவர் இரா. கண்ணன்",
                    "publisher": "உலகத் தமிழாராய்ச்சி நிறுவனம், சென்னை", "year": 2010,
                    "archive_org": f"https://archive.org/details/{SOURCE['archive_id']}"},
        "attribution": ("Scan: Tamil Digital Library, Tamil Virtual Academy, Government of Tamil Nadu, "
                        "via archive.org/details/TamilVirtualAcademy (CC BY-SA 4.0). Edition: நன்னூல் "
                        "உரைவளம் 5, ed. இரா. கண்ணன், உலகத் தமிழாராய்ச்சி நிறுவனம், 2010. Text: archive.org "
                        "OCR of the cited pages only; not proof-read."),
        "licence": "CC BY-SA 4.0 (Tamil Virtual Academy collection, D-021); share-alike. Excerpts of "
                   "classical commentaries only; the edition's own matter is not reproduced.",
        "ocr": {"engine": "archive.org derive OCR (_djvu.xml)", "proof_read": False,
                "warning": "OCR text of the cited leaves only. Check any quotation against the scan "
                           "page before a rule cites it (data/classical/verified_quotations.json)."},
        "sources": [pin_xml, pin_pn],
        "scan": {"file": f"{SOURCE['stem']}.pdf", **SOURCE["scan_pdf"],
                 "note": "the page images; not read by the build"},
        "numbering": "Commentaries are filed under OUR Nannūl number (data/classical/nannul.json). This "
                     "edition numbers one lower in places: its 138 is our 139.",
        "excerpts": [{"leaf": lf, "printed": printed.get(lf), "cited_for": LEAVES[lf],
                      "text": "\n".join(text[lf])} for lf in sorted(LEAVES)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", type=Path)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    blob = json.dumps(build(a.mirror), ensure_ascii=False, indent=1) + "\n"
    if a.verify:
        same = OUT.exists() and OUT.read_text("utf-8") == blob
        print(("ok: " if same else "DRIFT: ") + str(OUT))
        return 0 if same else 1
    OUT.write_text(blob, "utf-8")
    print(f"wrote {OUT} ({len(blob)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
