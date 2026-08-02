#!/usr/bin/env python3
"""Build the version-locked classical-text artifacts from the pinned Project Madurai sources.

Produces `data/classical/{tholkappiyam,nannul}.json` — every நூற்பா addressable by number, so a
rule table can cite a verse and the runtime can quote it back verbatim. Re-running is idempotent;
the `source_sha256` fields in the output are what make the artifact version-locked. If upstream
changes, the checksum changes and the diff is visible in review rather than silent.

    uv run python scripts/build_classical.py            # rebuild from the network
    uv run python scripts/build_classical.py --verify   # rebuild to a temp dir and diff

Licence: Project Madurai grants free distribution provided the header is kept intact — so these
artifacts ship in the public repo WITH that header, unlike the TVA course material (design repo
only). See LICENSING.md and data/PINS.md.

⚠️ Numbering differs between the two texts and this is not cosmetic:
  · Tholkappiyam — நூற்பா RESTART at 1 in every இயல், so a verse key is (அதிகாரம், இயல், number).
  · Nannūl       — numbering is CONTINUOUS 1–462, so the number alone is a key.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "classical"

UA = "thamizh-mcp/0.1 (+https://github.com/ief-global/thamizh-mcp) classical-text pinning"

THOLKAPPIYAM_URLS = {
    "எழுத்ததிகாரம்": "https://tamilnation.org/literature/grammar/mp100a",
    "சொல்லதிகாரம்": "https://tamilnation.org/literature/grammar/mp100b",
    "பொருளதிகாரம்": "https://tamilnation.org/literature/grammar/mp100c",
}
NANNUL_URL = "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0147.html"
# Project Madurai hosts a second, older Nannūl etext. It is NOT the primary source: pmuni0147 was
# revised 2021-08-31 and carries modern word-split orthography (ஆன ஒன்று ஆதி ஓர் புடை ஒப்பு இனமே),
# where pmuni0152 dates from 2002-05-15 and keeps the older joined orthography (ஆனஒன் றாதியோர்
# புடையொப் பினமே). Switching wholesale would downgrade 460 verses to the older revision to gain two.
# It is used ONLY to fill verses the primary omits, and every filled verse is marked as such.
NANNUL_SUPPLEMENT_URL = "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0152.html"

PM_HEADER = (
    "© Project Madurai 1999-2001\n\n"
    "Project Madurai is an open, voluntary, worldwide initiative devoted to preparation of "
    "electronic texts of tamil literary works and to distribute them free on the Internet. "
    "Details of Project Madurai are available at the website http://www.projectmadurai.org\n"
    "You are welcome to freely distribute this file, provided this header page is kept intact."
)

TAMIL = re.compile(r"[஀-௿]")


def fetch(url: str) -> tuple[str, str]:
    """Return (decoded html, sha256 of the raw bytes). The checksum is over BYTES, not text."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read()
    return raw.decode("utf-8", "replace"), hashlib.sha256(raw).hexdigest()


AYTHAM = "ஃ"


def repair(text: str) -> tuple[str, int, int]:
    """Repair U+FFFD baked into the upstream Tholkappiyam pages. Returns (text, n_ஃ, n_©).

    The three Tholkappiyam pages declare windows-1252 while actually serving UTF-8, and the
    resulting mis-transcode dropped exactly two characters, verifiably: **ஃ (ஆய்தம்)** wherever the
    context is Tamil, and **©** in the Project Madurai header. Every Tamil-context occurrence is ஃ —
    அ�றிணை→அஃறிணை, ன�கான்→னஃகான், அ�து→அஃது, ஒன்ப�து→ஒன்பஃது — because ஃ is the
    only character the bad transcode lost. This is a mechanical substitution, not a reconstruction:
    no judgement is applied and no other character is ever inserted. The counts are recorded in the
    artifact so the repair is auditable, and `--verify` re-derives them from upstream.
    """
    n_c = text.count("� Project")
    text = text.replace("� Project", "© Project")
    n_a = text.count("�")
    text = text.replace("�", AYTHAM)
    return text, n_a, n_c


def to_text(doc: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return s


def _flush(buf: list[str]) -> str:
    return " ".join(x.strip() for x in buf if x.strip())


# Trailing junk that the source glues onto the last verse of a section or of the whole work:
# a run of hyphens used as a section rule, the colophon, and the page footer.
_TAIL = re.compile(
    r"\s*(?:-{3,}|நன்னூல்\s*முற்றிற்று|This webpage was last revised|"
    r"Feel free to send the corrections|webmaster).*$",
    re.S,
)


def clean_verse(text: str) -> str:
    """Strip section rules and page boilerplate glued to a verse.

    Eleven verses in the Nannūl source end with a '-----' section rule, and நூற்பா 462 additionally
    carries the colophon and the webpage footer. Left in, a citation would quote page furniture as
    scripture. The colophon itself is kept — as metadata, not as a verse: Nannūl has exactly 462
    நூற்பா, so inventing 463/464 would be worse than dropping the text.
    """
    return _TAIL.sub("", text).strip()


def parse_tholkappiyam(text: str) -> dict[str, dict[str, str]]:
    """இயல் heading is a bare '<n>. <name>' line; a verse ends at a bare-number line.

    Verse numbers restart per இயல், so verses are nested under their இயல் name.
    """
    lines = text.split("\n")
    heads = [
        (i, m.group(1).strip())
        for i, ln in enumerate(lines)
        if (m := re.fullmatch(r"\s*\d+\.\s*(\S.*?)\s*", ln)) and TAMIL.search(m.group(1))
    ]
    out: dict[str, dict[str, str]] = {}
    for idx, (start, name) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        verses: dict[str, str] = {}
        buf: list[str] = []
        for ln in lines[start + 1:end]:
            s = ln.strip()
            if re.fullmatch(r"\d+", s):
                if body := _flush(buf):
                    verses[s] = body
                buf = []
            # Some verses carry their number glued to the final line ("…பெயரே.3") instead of
            # on a line of its own. Same verse boundary, different typesetting.
            elif (m := re.fullmatch(r"(.*?[^\d\s])(\d{1,3})\s*", s)) and TAMIL.search(m.group(1)):
                buf.append(m.group(1))
                if body := _flush(buf):
                    verses[m.group(2)] = body
                buf = []
            else:
                buf.append(ln)
        if verses:
            out[name] = verses
    return out


def gaps(nums: list[int]) -> list[int]:
    """Verse numbers absent from 1..max — i.e. present upstream but not extracted, or absent
    upstream. Recorded rather than hidden; never filled in."""
    have = set(nums)
    return [n for n in range(1, max(have) + 1) if n not in have] if have else []


def parse_nannul(text: str) -> tuple[dict[str, str], list[dict]]:
    """Body verses are '<n>. <text>' with CONTINUOUS numbering; also parse the TOC section map.

    The table of contents uses the SAME '<n>.' shape as a verse ('1.0 பொதுப்பாயிரம் 1 - 3'), so the
    body must be cut past it first — the TOC ends at the page's first horizontal rule. Skipping that
    cut silently turned TOC lines into நூற்பா 1, 2 and 3.
    """
    body = text
    if (rule := re.search(r"-{5,}", text)) is not None:
        body = text[rule.end():]
    elif (cut := body.find("சிறப்புப்பாயிரம்")) > 0:
        body = body[cut:]

    verses: dict[str, str] = {}
    num: str | None = None
    buf: list[str] = []
    for ln in body.split("\n"):
        # Reject heading furniture that mimics a verse opener: subsection numbers ('1.0 …') and
        # any line carrying a verse RANGE ('2. எழுத்ததிகாரம் 56 - 257'). Section headings repeat
        # mid-body, so without this they OVERWRITE the real நூற்பா 2 and 3 parsed earlier.
        # No genuine நூற்பா contains a digit range.
        if re.match(r"\s*\d+\.\d", ln) or re.search(r"\d+\s*-\s*\d+", ln):
            continue
        m = re.match(r"\s*(\d{1,3})\.\s*(.*)", ln)
        if m and 1 <= int(m.group(1)) <= 462:
            if num and (t := clean_verse(_flush(buf))):
                verses[num] = t
            num, buf = m.group(1), [m.group(2)]
        elif num is not None:
            buf.append(ln)
    if num and (t := clean_verse(_flush(buf))):
        verses[num] = t

    sections = [
        {"section": m.group(1).strip(), "first": int(m.group(2)), "last": int(m.group(3))}
        for m in re.finditer(r"([஀-௿][^\n]*?)\s*(\d{1,3})\s*-\s*(\d{1,3})\s*\n", text)
    ]
    return verses, sections


def parse_nannul_supplement(doc: str) -> dict[str, str]:
    """Parse pmuni0152 from its HTML, which is far more reliable than the flattened text.

    Each verse is one table row — `<td valign=top>` holds the verse, `<td valign=bottom>` holds the
    number — and section headings sit inside `<i>…</i>` within the verse cell. Stripping the italics
    removes headings exactly, where a text-level heuristic would guess (and did: it glued
    ‘இகர ஐகார ஈற்றுச் சிறப்புவிதி’ onto நூற்பா 176).
    """
    verses: dict[str, str] = {}
    for row in re.findall(r"<tr\b.*?</tr>", doc, flags=re.S | re.I):
        m = re.search(r"<td[^>]*valign\s*=\s*[\"']?bottom[\"']?[^>]*>(.*?)(?:</td>|</tr>|$)",
                      row, flags=re.S | re.I)
        if not m or not (num := m.group(1).strip()).isdigit():
            continue
        body = row[:m.start()]
        body = re.sub(r"<i\b.*?</i>", " ", body, flags=re.S | re.I)   # drop section headings
        if text := clean_verse(to_text(body)):
            verses[num] = " ".join(text.split())
    return verses


def build() -> tuple[dict, dict]:
    thol_ath, thol_sha = {}, {}
    rep_a = rep_c = 0
    for ath, url in THOLKAPPIYAM_URLS.items():
        doc, sha = fetch(url)
        text, n_a, n_c = repair(to_text(doc))
        rep_a, rep_c = rep_a + n_a, rep_c + n_c
        thol_ath[ath] = parse_tholkappiyam(text)
        thol_sha[ath] = {"url": url, "source_sha256": sha}

    doc, sha = fetch(NANNUL_URL)
    nan_text, n_a, n_c = repair(to_text(doc))
    nan_verses, nan_sections = parse_nannul(nan_text)

    # Fill only what the primary omits, and record which verses came from where.
    doc2, sha2 = fetch(NANNUL_SUPPLEMENT_URL)
    supp = parse_nannul_supplement(repair(doc2)[0])
    filled: dict[str, str] = {}
    for n in (str(x) for x in range(1, 463)):
        if n not in nan_verses and n in supp:
            nan_verses[n] = supp[n]
            filled[n] = NANNUL_SUPPLEMENT_URL
    nan_verses = {str(k): nan_verses[str(k)] for k in sorted(int(x) for x in nan_verses)}

    tholkappiyam = {
        "text": "Tholkappiyam",
        "text_ta": "தொல்காப்பியம்",
        "edition": "Project Madurai",
        "attribution": PM_HEADER,
        "edition_credits": "Etext Preparation & PDF version: Dr. K. Kalyanasundaram, Lausanne, "
                           "Switzerland. Proof-reading & Web version: Mr. N. D. Logasundaram, "
                           "Chennai, Tamilnadu.",
        "numbering": "நூற்பா numbers RESTART at 1 in every இயல் and collide across இயல் and "
                     "அதிகாரம். A citation MUST be qualified: அதிகாரம் › இயல் › நூற்பா. "
                     "Verses here are keyed accordingly.",
        "citation_template": "தொல்காப்பியம், {athikaram}, {iyal}, நூற்பா {verse}",
        "sources": thol_sha,
        "repairs": {
            "reason": "The upstream pages declare charset=windows-1252 while serving UTF-8; the "
                      "resulting mis-transcode baked U+FFFD into the text. Repaired mechanically: "
                      "every Tamil-context U+FFFD is ஃ (ஆய்தம்) — the only character that "
                      "transcode lost — and the header one is ©. No other substitution is made.",
            "aytham_restored": rep_a,
            "copyright_restored": rep_c,
        },
        "coverage": {
            ath: {
                iyal: {"count": len(vs), "max": max(int(n) for n in vs),
                       "missing": gaps([int(n) for n in vs])}
                for iyal, vs in iyals.items()
            } for ath, iyals in thol_ath.items()
        },
        "coverage_note": "‘missing’ = a நூற்பா number in 1..max not present in this artifact. "
                         "Recorded, never filled in. The grammar-critical இயல் "
                         "(எழுத்ததிகாரம்/புணரியல், சொல்லதிகாரம்/வேற்றுமையியல்) are complete.",
        "athikaram": thol_ath,
    }
    nannul = {
        "text": "Nannūl",
        "text_ta": "நன்னூல்",
        "author": "பவணந்தி முனிவர்",
        "edition": "Project Madurai (conforming to the edition edited by Mani "
                   "Thirunavukkarasu Mudaliar, publ. Vavilla Ramasamy Sastrulu & Sons, Madras, 1926)",
        "attribution": PM_HEADER,
        "edition_credits": "Etext preparation: Dr. Thomas Malten, Inst. of Indology and Tamil "
                           "Studies, Univ. of Koeln, Germany. Proof-reading, web & PDF versions: "
                           "Mr. N. D. Logasundaram, Chennai and Dr. K. Kalyanasundaram, Lausanne.",
        "numbering": "Numbering is CONTINUOUS 1–462 across the whole work, so a bare நூற்பா number "
                     "is unambiguous — unlike Tholkappiyam. The section map below is for "
                     "readability, not for addressing.",
        "citation_template": "நன்னூல், நூற்பா {verse}",
        "sources": {
            "primary": {"url": NANNUL_URL, "source_sha256": sha, "revised": "2021-08-31"},
            "supplement": {"url": NANNUL_SUPPLEMENT_URL, "source_sha256": sha2,
                           "revised": "2002-05-15",
                           "used_for": "gap-fill only — see `supplemented`"},
        },
        "supplemented": {
            "verses": filled,
            "note": "நூற்பா 73 and 176 are absent from the primary etext (72→74, 175→177) and were "
                    "filled from Project Madurai's older Nannūl page. The primary is NOT switched: "
                    "it is the 2021 revision with modern word-split orthography (ஆன ஒன்று ஆதி ஓர் "
                    "புடை ஒப்பு இனமே), while the supplement is 2002 with the older joined "
                    "orthography (ஆனஒன் றாதியோர் புடையொப் பினமே). Swapping wholesale would "
                    "downgrade 460 verses to gain two. These two therefore differ in orthographic "
                    "style from the rest — deliberate, and recorded here.",
        },
        "colophon": "நன்னூல் முற்றிற்று",
        "colophon_note": "Kept as metadata, not as a verse. Nannūl has exactly 462 நூற்பா; the "
                         "colophon and the page footer were being glued onto நூற்பா 462 by the "
                         "source's markup and are now stripped (see clean_verse).",
        "coverage": {
            "count": len(nan_verses),
            "expected": 462,
            "missing": gaps([int(n) for n in nan_verses]),
            "supplemented": sorted(int(n) for n in filled),
        },
        "sections": nan_sections,
        "verses": nan_verses,
    }
    return tholkappiyam, nannul


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="rebuild and report drift instead of writing")
    a = ap.parse_args()

    thol, nan = build()
    n_thol = sum(len(vs) for iyals in thol["athikaram"].values() for vs in iyals.values())
    n_nan = len(nan["verses"])
    print(f"Tholkappiyam: {len(thol['athikaram'])} அதிகாரம், {n_thol} நூற்பா")
    for ath, iyals in thol["athikaram"].items():
        print(f"  {ath}: {len(iyals)} இயல், {sum(len(v) for v in iyals.values())} நூற்பா")
    print(f"Nannūl: {n_nan} நூற்பா (expect 462)")

    if n_nan < 462 or n_thol < 1000:
        print("REFUSING TO WRITE — extraction looks truncated.", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    drift = False
    for name, data in (("tholkappiyam", thol), ("nannul", nan)):
        blob = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
        dest = OUT_DIR / f"{name}.json"
        if a.verify:
            old = dest.read_text("utf-8") if dest.exists() else ""
            if old != blob:
                drift = True
                print(f"DRIFT: {dest} differs from a fresh build")
            else:
                print(f"ok: {dest} matches upstream")
        else:
            dest.write_text(blob, "utf-8")
            print(f"wrote {dest} ({len(blob)} bytes, sha256 "
                  f"{hashlib.sha256(blob.encode()).hexdigest()[:16]}…)")
    return 1 if (a.verify and drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
