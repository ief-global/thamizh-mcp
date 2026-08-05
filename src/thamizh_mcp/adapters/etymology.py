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
_TEMPLATE = re.compile(r"\{\{(bor\+?|lbor\+?|inh\+?|der\+?)\|ta\|([a-z][a-z0-9\-]*)\|([^}|]*)")
_STRENGTH = {"bor": 0, "bor+": 0, "lbor": 1, "lbor+": 1, "inh": 2, "inh+": 2, "der": 3, "der+": 3}

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


def parse_etymology(wikitext: str) -> dict | None:
    """First usable etymology relation in the ==Tamil== section, or None.

    Only the Tamil section is read: the same page carries Sanskrit, Malayalam and other
    languages' entries, and their etymologies say nothing about the Tamil word.
    """
    m = re.search(r"==\s*Tamil\s*==.*?(?=\n==[^=]|\Z)", wikitext, re.S)
    if not m:
        return None
    section = m.group(0)
    hits = _TEMPLATE.findall(section)
    formations = _NATIVE_FORMATION.findall(section)
    if not hits and not formations:
        return None
    if not hits:
        # Only native word-formation stated: built from Tamil parts, so it is native.
        parts = " + ".join(p for p in formations[0][1].split("|") if p and "=" not in p)
        return {"relation": "inherited", "is_native": True, "source_lang": "ta",
                "source_lang_name": "Tamil", "source_word": parts or None,
                "template": formations[0][0], "certainty": "stated"}

    # HOMOGRAPHS. A Tamil headword often carries several Etymology sections, one per sense, and they
    # can disagree about provenance — கால் is leg (inherited, dra-pro *kāl) AND time (borrowed, Skt
    # काल); பூ is flower (dra-pro *pū) AND earth (Skt भू); சாலை is road (native சால்+ஐ) AND hall
    # (Skt शाला). Ranking by template strength picks `bor` over `inh` every time, so ANY word with
    # one Sanskrit sense came back Sanskrit — which labelled four core native words வடசொல் at 0.8.
    #
    # Which etymology applies depends on which SENSE is meant, and sense disambiguation is
    # downstream of this server (blueprint §2). So a conflict is reported as a conflict.
    native_hits = [h for h in hits if is_native_code(h[1])]
    borrowed_hits = [h for h in hits if not is_native_code(h[1])]
    if borrowed_hits and (native_hits or formations):
        nb = min(borrowed_hits, key=lambda h: _STRENGTH.get(h[0], 9))
        if native_hits:
            nn = min(native_hits, key=lambda h: _STRENGTH.get(h[0], 9))
            native_sense = {"relation": "inherited", "source_lang": nn[1],
                            "source_lang_name": language_name(nn[1]),
                            "source_word": nn[2].strip() or None}
        else:   # native sense is a Tamil derivation rather than an inheritance (சாலை = சால் + ஐ)
            parts = " + ".join(p for p in formations[0][1].split("|") if p and "=" not in p)
            native_sense = {"relation": "inherited", "source_lang": "ta",
                            "source_lang_name": "Tamil", "source_word": parts or None}
        return {
            "relation": "ambiguous",
            "is_native": None,
            "senses": [
                native_sense,
                {"relation": "borrowed", "source_lang": nb[1],
                 "source_lang_name": language_name(nb[1]), "source_word": nb[2].strip() or None},
            ],
        }

    tmpl, code, source_word = min(hits, key=lambda h: _STRENGTH.get(h[0], 9))
    native = is_native_code(code)
    return {
        "relation": "inherited" if native else "borrowed",
        "is_native": native,
        "source_lang": code,
        "source_lang_name": language_name(code),
        "source_word": source_word.strip() or None,
        "template": tmpl,
        # `der` is weaker than an outright borrowing statement — say so rather than flatten it.
        "certainty": "stated" if tmpl in ("bor", "bor+", "lbor", "inh") else "derived",
    }


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
