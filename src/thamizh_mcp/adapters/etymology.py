"""English Wiktionary etymology (EVOLVING) — resolves the SOURCE LANGUAGE of a Tamil word.

Why this exists. Tamil orthography can prove a word is not native — Grantha letters, a முதல் எழுத்து
violation — but it cannot say WHICH language the word came from. Reading Grantha as a Sanskrit signal
labelled பஸ், ஸ்கூல், ஹோட்டல் and ஜன்னல் as வடசொல்; refusing to read it left 51 of 108 everyday words
as `unknown`. Neither is a product. The missing ingredient is positive evidence of the source, and
en.wiktionary carries it in MACHINE-READABLE form:

    {{bor+|ta|pt|janela}}      ஜன்னல் ← Portuguese
    {{bor|ta|sa|पुस्तक}}        புத்தகம் ← Sanskrit   → வடசொல்
    {{inh|ta|dra-pro|*maran}}   மரம் inherited from Proto-Dravidian → இயற்சொல்

The last shape matters as much as the first: it is positive evidence a word IS native, which is what
the classifier's weakest branch (native-by-default) has always lacked.

TIER. This is `evolving`, not `anchor` — evidence, not authority. Wiktionary etymologies are edited
and some are contested (பசு is given as Sanskrit paśu, while a Dravidian *pacu is also argued). The
adapter therefore reports WHAT it found and WHERE, never asserting more confidence than a
crowd-edited source earns; the classifier keeps the alternative visible. An anchor source (Madras
Tamil Lexicon) is the intended upgrade path, not a replacement for citing this honestly.

Licence: CC BY-SA, cleared for use including public serving (D-012) — attribution travels with the
claim and it is never relicensed.
"""
from __future__ import annotations

import datetime as _dt
import os
import re

import httpx

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry, SourceAdapter
from thamizh_mcp.schema import SourceRef

_API = "https://en.wiktionary.org/w/api.php"
_UA = os.environ.get(
    "THAMIZH_HTTP_UA",
    "ThamizhMCP/0.1 (Tamil word-grammar MCP server; contact: saravanan3@duck.com) httpx",
)
_HEADERS = {"User-Agent": _UA, "Accept": "application/json"}

# Etymology templates, strongest relation first. `bor`/`bor+`/`lbor` state a borrowing outright;
# `inh` states inheritance; `der` only says "derived from", which may run through intermediaries —
# so it is accepted last and reported as the weaker relation it is.
# The third group is the whole template body (`*kāl||[[leg]]`, `काल|t=time`), not just the etymon:
# the gloss that names the SENSE often rides along in it.
_TEMPLATE = re.compile(r"\{\{(bor\+?|lbor\+?|inh\+?|der\+?)\|ta\|([a-z][a-z0-9\-]*)\|?([^{}]*)\}\}")
_STRENGTH = {"bor": 0, "bor+": 0, "lbor": 1, "lbor+": 1, "inh": 2, "inh+": 2, "der": 3, "der+": 3}

# A Tamil headword's senses are separated on the page by `===Etymology N===` headings, and THAT is
# the unit origin actually belongs to. Scanning the whole Tamil section at once was the original
# defect: it mixed templates from unrelated senses into one ranking.
_ETY_HEADING = re.compile(r"(?m)^===\s*Etymology(?:\s+\d+)?\s*===\s*$")

# The sense label, machine-readable, straight off the page: {{ety|ta|id=leg|…}} /
# {{etymon|ta|id=flower|…}}. Present on the well-maintained entries (கால், பூ, பசு); the gloss in
# the relation template and then the first definition line are the fallbacks.
_SENSE_ID = re.compile(r"\{\{ety(?:mon)?\|ta\|id=([^|}]+)")
_DEF_LINE = re.compile(r"(?m)^#\s+(.+)$")
_WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")
_ANY_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")

# Native WORD-FORMATION: சாலை is {{suffix|ta|சால்|ஐ}} — built from a Tamil root, not borrowed.
# These carry no language code (the parts are Tamil), so they need their own pattern; without it a
# word whose native sense is derivational looked purely Sanskrit.
_NATIVE_FORMATION = re.compile(r"\{\{(suffix|affix|prefix|compound|com)\|ta\|([^}]*)\}\}")

# Codes meaning the word is NATIVE, not borrowed: Tamil itself, Old Tamil, and anything in the
# Dravidian family. An `inh` from any of these is positive இயற்சொல் evidence.
#
# Matched by PREFIX, not by an enumerated list. Wiktionary uses a whole family of sub-branch codes —
# dra-pro, dra-sdo-pro (Proto-South-Dravidian), dra-sou-pro, dra-cen-pro … — and hardcoding them
# meant மழை (`dra-sdo-pro`) fell through and was reported as BORROWED from a language called
# "dra-sdo-pro". Any unlisted Dravidian branch would have done the same.
_NATIVE_EXACT = frozenset({"ta", "oty"})


def is_native_code(code: str) -> bool:
    return code in _NATIVE_EXACT or code == "dra" or code.startswith("dra-")

# ISO/Wiktionary codes → the name we show. Only what we actually need to render; an unlisted code
# is reported by its code rather than guessed at.
_LANG_NAMES = {
    "sa": "Sanskrit", "en": "English", "pt": "Portuguese", "ur": "Urdu", "fa": "Persian",
    "fa-cls": "Classical Persian", "ar": "Arabic", "hi": "Hindi", "nl": "Dutch", "fr": "French",
    "mr": "Marathi", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "pi": "Pali",
    "inc-hnd": "Hindustani", "grc": "Ancient Greek", "la": "Latin", "pra": "Prakrit",
    "oty": "Old Tamil", "dra-pro": "Proto-Dravidian", "dra": "Dravidian", "ta": "Tamil",
    "dra-sdo-pro": "Proto-South-Dravidian", "dra-sou-pro": "Proto-South-Dravidian",
    "dra-cen-pro": "Proto-Central-Dravidian",
}


def language_name(code: str) -> str:
    return _LANG_NAMES.get(code, code)


def _clean_gloss(text: str) -> str | None:
    """A wikitext definition fragment reduced to a plain sense label.

    Templates NEST -- {{ng|the alphasyllabic combination of {{m|ta|...}}}} -- so a single pass
    strips the inner one and leaves the outer opener behind as raw markup. Repeat to a fixed
    point, then drop any unbalanced remainder: wikitext must never reach a user-facing field.
    """
    prev = None
    while prev != text:
        prev = text
        text = _ANY_TEMPLATE.sub("", text)      # {{lb|ta|anatomy}}, {{q|of a rooster}} ...
    text = re.sub(r"\{\{.*|\}\}", "", text)     # unbalanced leftovers
    text = _WIKILINK.sub(r"\1", text)           # [[leg]] -> leg, [[a|b]] -> b
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"\(\s*[:;,]?\s*\)", "", text)   # parens emptied by template removal
    text = re.sub(r"\s+", " ", text).strip(" .,;:")
    return text or None


def _sense_label(block: str, body: str | None) -> str | None:
    """What sense this etymology block belongs to, best evidence first.

    1. the page's own machine-readable id  -- {{ety|ta|id=leg|...}}
    2. the gloss inside the relation template -- {{inh+|ta|dra-pro|*kal||[[leg]]}}, {{bor|...|t=time}}
    3. the block's first definition line -- `# [[road]], [[path]]`
    """
    m = _SENSE_ID.search(block)
    if m:
        return m.group(1).strip() or None
    if body:
        parts = [p.strip() for p in body.split("|")]
        for p in parts[1:]:
            if p.startswith(("t=", "gloss=")):
                return _clean_gloss(p.split("=", 1)[1])
        for p in parts[1:]:                     # a trailing positional gloss
            if p and "=" not in p:
                return _clean_gloss(p)
    for line in _DEF_LINE.findall(block):
        label = _clean_gloss(line)
        if label:
            return label
    return None


def _parse_block(block: str) -> dict | None:
    """One `===Etymology N===` block -> its origin, or None if it states no etymology.

    Saran's ruling (2026-08-05): a sense whose block states no relation at all is OMITTED rather
    than listed as an unknown sense. That covers real cases -- KAL 'wind' (bare cognates only) and
    KAR 'to darken' ("From the above") -- where listing them would pad the answer with non-answers.
    """
    hits = _TEMPLATE.findall(block)
    formations = _NATIVE_FORMATION.findall(block)
    if not hits and not formations:
        return None

    if hits:
        tmpl, code, body = min(hits, key=lambda h: _STRENGTH.get(h[0], 9))
        native = is_native_code(code)
        return {
            "relation": "inherited" if native else "borrowed",
            "is_native": native,
            "source_lang": code,
            "source_lang_name": language_name(code),
            "source_word": body.split("|")[0].strip() or None,
            "template": tmpl,
            # Only `der`/`der+` are weaker -- "derived from" may run through unnamed intermediaries.
            # The `+` variants of the others are NOT a weaker claim: en.wiktionary's inh+/bor+/lbor+
            # differ from the bare forms only in rendering a leading "Inherited from"/"Borrowed
            # from". Omitting inh+ and lbor+ here scored every {{inh+}} word (மழை and much of the
            # native sweep) at 0.65 while {{bor+}} borrowings got 0.8 -- a tilt against native words.
            "certainty": "derived" if tmpl.startswith("der") else "stated",
            "sense": _sense_label(block, body),
        }

    # Only native word-formation stated: built from Tamil parts, so it is native.
    parts = " + ".join(p for p in formations[0][1].split("|") if p and "=" not in p)
    return {"relation": "inherited", "is_native": True, "source_lang": "ta",
            "source_lang_name": "Tamil", "source_word": parts or None,
            "template": formations[0][0], "certainty": "stated",
            "sense": _sense_label(block, None)}


def parse_etymology(wikitext: str) -> dict | None:
    """The ==Tamil== section's etymology, ONE ENTRY PER SENSE, or None.

    Only the Tamil section is read: the same page carries Sanskrit, Malayalam and other
    languages' entries, and their etymologies say nothing about the Tamil word.

    HOMOGRAPHS -- the reason this is per-block. A Tamil headword carries one Etymology section per
    sense and they disagree: leg (inherited) / canal (inherited) / forest (derived) / time (Skt)
    for one headword; flower vs earth; road (native suffix) vs hall (Skt); blackness vs English
    car. Ranking templates across the WHOLE section picks `bor` over `inh` every time, so any word
    with a single Sanskrit sense came back Sanskrit -- that labelled four core native words
    vadasol at 0.8 and nearly shipped. Parsing per block keeps each sense's evidence attached to
    that sense; the classifier decides how the headword is reported.
    """
    m = re.search(r"==\s*Tamil\s*==.*?(?=\n==[^=]|\Z)", wikitext, re.S)
    if not m:
        return None
    section = m.group(0)

    # A page with no Etymology headings is one implicit block (the whole section). With headings,
    # drop the preamble before the first -- that holds pronunciation, not etymology.
    blocks = _ETY_HEADING.split(section)
    blocks = blocks[1:] if len(blocks) > 1 else [section]

    senses = [s for s in (_parse_block(b) for b in blocks) if s]
    if not senses:
        return None

    native = [s for s in senses if s["is_native"]]
    borrowed = [s for s in senses if not s["is_native"]]

    if native and borrowed:
        # Tamil senses first: the reader is nudged to the Tamil word and the borrowing follows in
        # full (Saran's ruling, 2026-08-05). The classifier applies the same order to the headword.
        return {"relation": "ambiguous", "is_native": None, "senses": native + borrowed}

    if len(senses) == 1:
        return senses[0]

    # Several senses agreeing in polarity (all native, or all borrowed). Report the strongest as
    # the headword relation, but keep every sense so the breakdown can still be shown.
    best = min(senses, key=lambda s: _STRENGTH.get(s["template"], 9))
    return {**best, "senses": senses}


class EnWiktionaryEtymologyAdapter(SourceAdapter):
    """Source-language evidence for one Tamil word. Never raises: a miss is an honest NoEntry."""

    name = "English Wiktionary (etymology)"
    tier = "evolving"

    def __init__(self, client: httpx.AsyncClient | None = None, timeout_s: float | None = None):
        self._client = client                       # injectable for tests
        self.timeout_s = timeout_s or config.HTTP_TIMEOUT_S

    async def lookup(self, normalized_word: str) -> AdapterResult | NoEntry:
        params = {"action": "query", "titles": normalized_word, "prop": "revisions",
                  "rvprop": "content", "rvslots": "main", "format": "json", "formatversion": "2"}
        try:
            if self._client is not None:
                resp = await self._client.get(_API, params=params, headers=_HEADERS)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_s, headers=_HEADERS) as client:
                    resp = await client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            return NoEntry(source=self.name, reason="timeout",
                           note=f"no response in {self.timeout_s}s")
        except Exception as exc:      # network/HTTP/JSON — honest gap, never a guess
            return NoEntry(source=self.name, reason="error",
                           note=f"{type(exc).__name__}: {exc}"[:200])

        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing") or "revisions" not in pages[0]:
            return NoEntry(source=self.name, reason="no_entry",
                           note=f"no en.wiktionary page for {normalized_word}")
        ety = parse_etymology(pages[0]["revisions"][0]["slots"]["main"]["content"])
        if ety is None:
            return NoEntry(source=self.name, reason="no_entry",
                           note="page exists but its Tamil section states no etymology")
        url = f"https://en.wiktionary.org/wiki/{normalized_word}#Tamil"
        ety["citation"] = url
        return AdapterResult(
            fields={"etymology": ety},
            sources=[SourceRef(name=self.name, tier="evolving", ref=url,
                               retrieved=_dt.date.today().isoformat())],
            tier="evolving")
