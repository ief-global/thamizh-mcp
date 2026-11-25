#!/usr/bin/env python3
"""Build the version-locked classical-text artifacts from the pinned Project Madurai sources.

Produces `data/classical/{tholkappiyam,nannul}.json` — every நூற்பா addressable by number, so a
rule table can cite a verse and the runtime can quote it back verbatim — and
`data/classical/tholkappiyam_eluthu_urai.json`, நச்சினார்க்கினியர்'s commentary on எழுத்ததிகாரம்,
aligned to those verses BY TEXT (D-024). Re-running is idempotent;
the `source_sha256` fields in the output are what make the artifact version-locked. If upstream
changes, the checksum changes and the diff is visible in review rather than silent.

    uv run python scripts/build_classical.py            # rebuild from the network
    uv run python scripts/build_classical.py --verify   # rebuild to a temp dir and diff

Licence: Project Madurai grants free distribution provided the header is kept intact — so these
artifacts ship in the public repo WITH that header. See LICENSING.md and data/PINS.md.

Tholkappiyam comes from Project Madurai's OWN etext (pmuni0100) since 2026-11-24. It was pinned
from the tamilnation.org mirror (mp100a/b/c) before that, and the mirror was lossy: ஃ became U+FFFD
or '?', the vowel sign ொ and ~130 other characters were dropped, four verses were glued into their
neighbours, and பொருளதிகாரம் lost மரபியல் (its verses were filed under செய்யுளியல்). Every verse
of the old pin is contained in the new one. See data/PINS.md and D-024.

⚠️ Numbering differs between the two texts and this is not cosmetic:
  · Tholkappiyam — நூற்பா RESTART at 1 in every இயல், so a verse key is (அதிகாரம், இயல், number).
  · Nannūl       — numbering is CONTINUOUS 1–462, so the number alone is a key.
"""
from __future__ import annotations

import argparse
import difflib
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

THOLKAPPIYAM_URL = "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0100.html"
THOLKAPPIYAM_ATHIKARAM = ("எழுத்ததிகாரம்", "சொல்லதிகாரம்", "பொருளதிகாரம்")
# The header of THIS file, verbatim. It differs from the Nannūl pages' header (dates, URL), and the
# grant is conditional on the header of the file actually distributed travelling with it.
THOLKAPPIYAM_HEADER = (
    "© Project Madurai 1999 - 2004\n\n"
    "Project Madurai is an open, voluntary, worldwide initiative devoted to preparation of "
    "electronic texts of tamil literary works and to distribute them free on the Internet. "
    "Details of Project Madurai are available at the website http://www.tamil.net/projectmadurai\n"
    "You are welcome to freely distribute this file, provided this header page is kept intact."
)
RETIRED_THOLKAPPIYAM_MIRROR = {
    "எழுத்ததிகாரம்": "https://tamilnation.org/literature/grammar/mp100a",
    "சொல்லதிகாரம்": "https://tamilnation.org/literature/grammar/mp100b",
    "பொருளதிகாரம்": "https://tamilnation.org/literature/grammar/mp100c",
}

# நச்சினார்க்கினியர் உரை on எழுத்ததிகாரம் (Kazhagam edition with பாவாணர்'s footnotes), in two pages.
URAI_URLS = (
    "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0516_01.html",
    "https://www.projectmadurai.org/pm_etexts/utf8/pmuni0516_02.html",
)
URAI_HEADER = (
    "© Project Madurai, 1998-2015.\n\n"
    "Project Madurai is an open, voluntary, worldwide initiative devoted to preparation of "
    "electronic texts of tamil literary works and to distribute them free on the Internet. "
    "Details of Project Madurai are available at the website http://www.projectmadurai.org/\n"
    "You are welcome to freely distribute this file, provided this header page is kept intact."
)
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


# Running heads absorbed into a verse body. Project Madurai's text sometimes carries the NEXT
# section's subject word at the end of the preceding நூற்பா.
#
# This is a CURATED list, not a heuristic, and it cannot be otherwise. நூற்பா 140 ends with a
# stray 'இடைநிலை' (the subject of 141) — but 142 ends '…தரும் தொழில் இடைநிலை' where the same word
# is the verse's own predicate, and 143 likewise. A rule that trimmed one would corrupt the other.
# The discriminator is whether the verse's sentence completes without the term, which is a reading
# judgement, so every entry here is ruled individually by Saran (TVA A021 coursework).
#
# Ruled 2026-08-08: 133 and 140 are running heads; 142 is genuine and must NOT be trimmed.
# Sixteen further candidates were detected and are listed in data/PINS.md awaiting ruling — they are
# deliberately NOT trimmed until ruled, because quoting one extra word is a smaller error than
# silently deleting scripture.
NANNUL_RUNNING_HEADS: dict[str, str] = {
    "133": "பகுதி",      # subject of 134; 133's sentence completes at 'எப்பதங்களும்'
    "140": "இடைநிலை",    # subject of 141; 140's sentence completes at 'பெயரினும் சிலவே'
}


def strip_running_head(num: str, text: str) -> str:
    """Drop a ruled running head from the end of a நூற்பா. Only exact, ruled matches."""
    head = NANNUL_RUNNING_HEADS.get(str(num))
    if head and text.rstrip().endswith(head):
        return text.rstrip()[: -len(head)].strip()
    return text


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


def split_tholkappiyam(text: str) -> dict[str, str]:
    """pmuni0100 holds all three அதிகாரம் on one page. Returns each அதிகாரம்'s text.

    Layout differs from the old mirror in one way only: a verse number trails its last line after a
    space ('…ஆறே. 17'), so it is moved onto its own line for parse_tholkappiyam. The first mention
    of எழுத்ததிகாரம் is the table of contents, so the body starts at the second.
    """
    text = "\n".join(re.sub(r"^(.*[^\d\s])\s+(\d{1,3})\s*$", r"\1\n\2", ln)
                     for ln in text.split("\n"))
    pos = [[m.start() for m in re.finditer(name, text)] for name in THOLKAPPIYAM_ATHIKARAM]
    cut = [pos[0][1], pos[1][0], pos[2][0], len(text)]
    return {name: text[cut[i]:cut[i + 1]] for i, name in enumerate(THOLKAPPIYAM_ATHIKARAM)}


# --- நச்சினார்க்கினியர் உரை (D-024) -------------------------------------------------------------

_FN = "§FN "
_COMMENTARY_START = re.compile(r"^(இது|இஃது|இதுவும்|இவை|இவையும்|இ\s*-\s*ள்|இதன்\s*பொருள்)")
_CONSONANT = re.compile(r"[\u0B95-\u0BB9ஃ]")


def _urai_lines(doc: str) -> list[str]:
    # The source ends every line with "<br>" + newline; collapse the pair so a blank line means a
    # genuinely empty line (the boundary between verse and commentary).
    doc = re.sub(r"<br\s*/?>[ \t]*\r?\n?", "<br>", doc, flags=re.I)
    # Footnotes (<ul>) are numbered too ('2. கூட்டம் - …'). Tag their lines so none is ever taken
    # for a verse heading. A footnote block never spans a heading or a verse block.
    doc = re.sub(r"<ul[^>]*>((?:(?!<strong|<h\d|<center).)*?)</ul>",
                 lambda m: "<br>" + _FN + re.sub(r"<br>\s*", "<br>" + _FN, m.group(1)) + "<br>",
                 doc, flags=re.S | re.I)
    return [ln.strip() for ln in to_text(doc).split("\n")]


def parse_urai(lines: list[str]) -> tuple[list[dict], list[int]]:
    """Commentary units in order, and the continuous numbers the etext does not print.

    A heading is '<n>[.] <verse…>' where n follows the previous heading (a gap of up to two is
    tolerated and RECORDED: the etext omits 132, 219 and 391). The editor's preface numbers its own
    points 1..13, so parsing starts at verse 1 itself. A verse ends at a blank line or where the
    commentary visibly begins. A short line just before a heading is that unit's topic.
    """
    start = next(i for i, ln in enumerate(lines) if re.match(r"^1\s*\.?\s+எழுத்தெனப்", ln))
    heads: list[tuple[int, int, str]] = []
    last, absent = 0, []
    for i, ln in enumerate(lines[start:], start):
        m = re.match(r"^(\d{1,3})\s*\.?\s+(\S.*)$", ln)
        if not m or not TAMIL.search(m.group(2)) or re.search(r"\d+\s*-\s*\d+\s*$", m.group(2)):
            continue
        n = int(m.group(1))
        if last < n <= last + 3:
            absent += range(last + 1, n)
            heads.append((i, n, m.group(2)))
            last = n
    units: list[dict] = []
    for h, (i, n, first) in enumerate(heads):
        end = heads[h + 1][0] if h + 1 < len(heads) else len(lines)
        verse, j = [first], i + 1
        while j < end and lines[j] and not _COMMENTARY_START.match(lines[j]):
            verse.append(lines[j])
            j += 1
        units.append({"n": n, "verse": " ".join(verse).strip(), "_body": lines[j:end]})
    for u, nxt in zip(units, units[1:] + [None]):
        body = u.pop("_body")
        keep = [k for k, ln in enumerate(body) if ln]
        if nxt is not None and keep:
            tail = body[keep[-1]]
            if (len(tail) <= 60 and TAMIL.search(tail) and not tail.startswith(_FN)
                    and not re.search(r"\(\d{1,3}\)\s*$", tail) and not re.fullmatch(r"-{3,}", tail)):
                nxt["topic"] = tail
                body = body[:keep[-1]]
        notes = [ln[len(_FN):].strip() for ln in body if ln.startswith(_FN)]
        text = "\n".join(ln for ln in body if not ln.startswith(_FN))
        text = re.sub(r"(?m)^\s*-{3,}\s*$", "", text)
        text = re.sub(r"\n{2,}", "\n", text).strip()
        ks = re.findall(r"\((\d{1,3})\)", text[-160:])
        u["printed_number_in_iyal"] = int(ks[-1]) if ks else None
        u["urai"] = text
        u["examples"] = [re.sub(r"\s+", " ", m.group(0)).strip() for m in re.finditer(
            r"(?:எ\s*-\s*டு|உதாரணம்)\s*:?.*?(?:என\s*வரும்|$)", text, re.M)]
        u["footnotes"] = [x for x in notes if x]
    return units, absent


def _skeleton(s: str) -> str:
    """Consonants only: split and joined orthography, and vowel sandhi, reduce to the same string."""
    return "".join(_CONSONANT.findall(s))


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def align_urai(ours: list[tuple[str, str, str]], units: list[dict], band: int = 12):
    """Monotonic alignment of our verses (iyal, number, text) to commentary units, BY TEXT.

    The commentary numbers continuously and divides two இயல் differently from our text, so its
    numbers can never be used as keys. Returns (pairs, merges): pairs are (our index, unit index,
    similarity); merges are our verses the commentary prints inside a neighbour's unit.
    """
    a = [_skeleton(t) for _, _, t in ours]
    b = [_skeleton(u["verse"]) for u in units]
    n, m = len(a), len(b)
    sim = {(i, j): _ratio(a[i], b[j])
           for i in range(n) for j in range(max(0, i - band), min(m, i + band + 1))}
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt: list[list[str | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best, how = dp[i - 1][j], "skip_ours"
            if dp[i][j - 1] > best:
                best, how = dp[i][j - 1], "skip_unit"
            s = sim.get((i - 1, j - 1))
            if s is not None and s >= 0.5 and dp[i - 1][j - 1] + (s - 0.5) > best:
                best, how = dp[i - 1][j - 1] + (s - 0.5), "match"
            dp[i][j], bt[i][j] = best, how
    pairs, i, j = [], n, m
    while i > 0 and j > 0:
        if bt[i][j] == "match":
            pairs.append((i - 1, j - 1, sim[i - 1, j - 1])); i -= 1; j -= 1
        elif bt[i][j] == "skip_ours":
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    by_ours = {i: (j, s) for i, j, s in pairs}
    merges = []
    for i in range(n):
        if i in by_ours:
            continue
        for nb in (i - 1, i + 1):
            if nb in by_ours:
                j, s = by_ours[nb]
                both = ours[min(i, nb)][2] + " " + ours[max(i, nb)][2]
                r = _ratio(_skeleton(both), b[j])
                if r > s + 0.05:
                    merges.append((i, j, r))
    return pairs, merges


def build() -> tuple[dict, dict, dict]:
    doc, thol_sha = fetch(THOLKAPPIYAM_URL)
    text, rep_a, rep_c = repair(to_text(doc))
    thol_ath = {ath: parse_tholkappiyam(part) for ath, part in split_tholkappiyam(text).items()}

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
    nan_verses = {str(k): strip_running_head(str(k), nan_verses[str(k)])
                  for k in sorted(int(x) for x in nan_verses)}

    tholkappiyam = {
        "text": "Tholkappiyam",
        "text_ta": "தொல்காப்பியம்",
        "edition": "Project Madurai",
        "attribution": THOLKAPPIYAM_HEADER,
        "edition_credits": "Etext Preparation & PDF version: Dr. K. Kalyanasundaram, Lausanne, "
                           "Switzerland. Proof-reading & Web version: Mr. N. D. Logasundaram, "
                           "Chennai, Tamilnadu.",
        "numbering": "நூற்பா numbers RESTART at 1 in every இயல் and collide across இயல் and "
                     "அதிகாரம். A citation MUST be qualified: அதிகாரம் › இயல் › நூற்பா. "
                     "Verses here are keyed accordingly.",
        "citation_template": "தொல்காப்பியம், {athikaram}, {iyal}, நூற்பா {verse}",
        "sources": {"url": THOLKAPPIYAM_URL, "source_sha256": thol_sha},
        "repairs": {
            "reason": "None needed. This is Project Madurai's own etext and it is clean. The "
                      "mechanical U+FFFD→ஃ repair still runs, so a future upstream regression is "
                      "counted here rather than shipped.",
            "aytham_restored": rep_a,
            "copyright_restored": rep_c,
        },
        "retired_mirror": {
            "urls": RETIRED_THOLKAPPIYAM_MIRROR,
            "retired": "2026-11-24",
            "why": "The tamilnation.org mirror pinned 2026-08-02 was lossy. Against this etext it "
                   "had: ஃ lost as U+FFFD (repaired then) and as a literal '?' (21 verses, never "
                   "repaired); the vowel sign ொ dropped (85 verses); ~130 verses missing other "
                   "characters; four verses glued into a neighbour (சொல் வினையியல் 9, பொருளியல் 2, "
                   "மெய்ப்பாட்டியல் 17, உவமயியல் 7); and மரபியல் filed under செய்யுளியல், with "
                   "the real செய்யுளியல் absent. Every character of the old pin is present here. "
                   "The mirror also returned HTTP 503 on 2026-11-24. See D-024.",
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
    urai = build_urai(thol_ath["எழுத்ததிகாரம்"])
    return tholkappiyam, nannul, urai


def build_urai(eluthu: dict[str, dict[str, str]]) -> dict:
    """நச்சினார்க்கினியர் on எழுத்ததிகாரம், aligned to OUR verses by text (D-024)."""
    lines, sources = [], []
    for url in URAI_URLS:
        doc, sha = fetch(url)
        lines += _urai_lines(doc)
        sources.append({"url": url, "source_sha256": sha})
    units, absent = parse_urai(lines)
    ours = [(iyal, n, v) for iyal, vs in eluthu.items() for n, v in vs.items()]
    pairs, merges = align_urai(ours, units)
    for i, j, s in pairs:
        units[j]["aligned_to"] = {"iyal": ours[i][0], "verse": ours[i][1]}
        units[j]["match"] = round(s, 3)
    for i, j, s in merges:
        units[j].setdefault("also_covers", []).append({"iyal": ours[i][0], "verse": ours[i][1]})
        units[j]["match_with_merge"] = round(s, 3)
    covered = {(u["aligned_to"]["iyal"], u["aligned_to"]["verse"]) for u in units if "aligned_to" in u}
    covered |= {(c["iyal"], c["verse"]) for u in units for c in u.get("also_covers", [])}
    ordered = [{"n": u["n"], "topic": u.get("topic"), "verse": u["verse"],
                "printed_number_in_iyal": u["printed_number_in_iyal"],
                "aligned_to": u.get("aligned_to"), "also_covers": u.get("also_covers"),
                "match": u.get("match"), "urai": u["urai"], "examples": u["examples"],
                "footnotes": u["footnotes"]} for u in units]
    return {
        "text": "Tholkappiyam, எழுத்ததிகாரம், with the commentary of நச்சினார்க்கினியர்",
        "text_ta": "தொல்காப்பியம் — எழுத்ததிகாரம் — நச்சினார்க்கினியர் உரை",
        "commentator": "நச்சினார்க்கினியர்",
        "edition": "Project Madurai pmuni0516, from the edition of the South India Saiva Siddhanta "
                   "Works Publishing Society (கழகம்), Tirunelveli & Chennai, with footnotes by "
                   "புலவர் ஞா. தேவநேயப் பாவாணர்",
        "attribution": URAI_HEADER,
        "edition_credits": "Scanned image courtesy of the Digital Library of India. E-version "
                           "prepared via Project Madurai's Distributed Proof-reading by Anbu Jaya, "
                           "Karthika Mukundh, CMC Karthik, R. Navaneethakrishnan, V. Ramasami, "
                           "A. Sezhian, P. Sukumar and SC Tamizharasu. HTML and PDF versions: "
                           "Dr. K. Kalyanasundaram, Lausanne, Switzerland.",
        "sources": sources,
        "numbering": "`n` is this edition's CONTINUOUS number across எழுத்ததிகாரம். It is NOT a key "
                     "into tholkappiyam.json, whose numbers restart per இயல் and whose இயல் "
                     "division differs in two places. Use `aligned_to` (matched by verse text).",
        "alignment": {
            "method": "monotonic dynamic-programming alignment of consonant skeletons (vowels and "
                      "spacing removed, so split and joined orthography compare equal)",
            "aligned": len(pairs),
            "our_verses": len(ours),
            "absent_from_etext": absent,
            "merged_in_commentary": [{"iyal": ours[i][0], "verse": ours[i][1],
                                      "printed_with_unit": units[j]["n"]} for i, j, _ in merges],
            "only_in_commentary": [u["n"] for u in units if "aligned_to" not in u],
            "unaligned_ours": [{"iyal": iy, "verse": n} for iy, n, _ in ours
                               if (iy, n) not in covered],
            "note": "Every verse of ours is either aligned, printed merged with a neighbour, or "
                    "absent from this etext. Nothing is forced into a match.",
        },
        "units": ordered,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="rebuild and report drift instead of writing")
    a = ap.parse_args()

    thol, nan, urai = build()
    n_thol = sum(len(vs) for iyals in thol["athikaram"].values() for vs in iyals.values())
    n_nan = len(nan["verses"])
    print(f"Tholkappiyam: {len(thol['athikaram'])} அதிகாரம், {n_thol} நூற்பா")
    for ath, iyals in thol["athikaram"].items():
        print(f"  {ath}: {len(iyals)} இயல், {sum(len(v) for v in iyals.values())} நூற்பா")
    print(f"Nannūl: {n_nan} நூற்பா (expect 462)")

    al = urai["alignment"]
    accounted = al["aligned"] + len(al["merged_in_commentary"]) + len(al["unaligned_ours"])
    print(f"Urai: {len(urai['units'])} units; {al['aligned']}/{al['our_verses']} of our verses "
          f"aligned, {len(al['merged_in_commentary'])} merged, absent from etext "
          f"{al['absent_from_etext']}, only in commentary {al['only_in_commentary']}")

    if n_nan < 462 or n_thol < 1500:
        print("REFUSING TO WRITE — extraction looks truncated.", file=sys.stderr)
        return 1
    if al["aligned"] < 470 or accounted != al["our_verses"]:
        print("REFUSING TO WRITE — commentary alignment regressed.", file=sys.stderr)
        return 1

    # A per-artifact guard. On 2026-11-24 Project Madurai's Nannūl primary page had been revised
    # (sha256 bfc865ddc2e4… → b970b4ee13b4…) and the parser read it into a different text for all
    # but 14 verses. Never overwrite the verified pin with that: keep it, say so, write the rest.
    pinned_nannul = OUT_DIR / "nannul.json"
    nannul_ok = len(nan["supplemented"]["verses"]) <= 2
    if not nannul_ok:
        print(f"NOT WRITING nannul.json: {len(nan['supplemented']['verses'])} verses had to come "
              "from the supplement, so the primary page no longer parses as pinned. The verified "
              "copy is kept. See data/PINS.md.", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    drift = False
    artifacts = [("tholkappiyam", thol), ("tholkappiyam_eluthu_urai", urai)]
    if nannul_ok or not pinned_nannul.exists():
        artifacts.insert(1, ("nannul", nan))
    else:
        drift = True
    for name, data in artifacts:
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
