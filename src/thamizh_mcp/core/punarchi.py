"""Round-trip புணர்ச்சி engine (D-023): one rule set for splitting a word and joining it back.

The rule, Saran's, 2026-11-24: a split is valid only if joining its parts back, under the SAME rule
tables, rebuilds the word. So the split is found by SYNTHESIS: try the cited joins of
`data/grammar/punarchi.json` at each boundary between the parts, and keep a split only when
the join reproduces the word exactly. A split no join can rebuild declares a gap, and the gap names
the material nothing accounts for; it never drops material in silence. Before this module the
decoder built a split from FST tags alone and never compared it with the word, so the ந் of
காத்திருந்தாள் was lost without trace (KNOWN DECODER DEFECT 1).

Everything runs on PHONEMES: a மெய் ('க்') or an உயிர் ('அ'). Tholkappiyam எழுத்ததிகாரம் › புணரியல்
36 is the join (a vowel after a pulli fuses with it) and 37 is the split (strip the vowel and the
consonant takes back its own form). Rendering a phoneme list as letters applies 36; reading letters
into phonemes applies 37. That is what makes split and join one rule set, not two.

The code implements each rule's CONDITION and EFFECT by its `id`. The citation, status and wording
come from the table, so a rule cannot ship uncited by being written in code alone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from thamizh_mcp import config
from thamizh_mcp.core import classical
from thamizh_mcp.schema import JoinStep, SourceRef

# --- letters <-> phonemes (புணரியல் 36 / 37) ---

PULLI = "்"
UYIR = "அஆஇஈஉஊஎஏஐஒஓஔ"
_SIGN_TO_UYIR = {"ா": "ஆ", "ி": "இ", "ீ": "ஈ", "ு": "உ", "ூ": "ஊ",
                 "ெ": "எ", "ே": "ஏ", "ை": "ஐ", "ொ": "ஒ", "ோ": "ஓ", "ௌ": "ஔ"}
_UYIR_TO_SIGN = {v: k for k, v in _SIGN_TO_UYIR.items()}
VALLINAM = {"க்", "ச்", "ட்", "த்", "ப்", "ற்"}
# The nasal of each hard consonant's class (Nannūl 219: வன்மைக்கு இனமாத் திரிபவும்).
_INAM = {"க்": "ங்", "ச்": "ஞ்", "ட்": "ண்", "த்": "ந்", "ப்": "ம்", "ற்": "ன்"}
NEDIL = set("ஆஈஊஏஐஓஔ")


def _is_consonant(ch: str) -> bool:
    return "க" <= ch <= "ஹ"


def phonemes(text: str) -> list[str]:
    """Letters → phonemes. உயிர்மெய் splits into மெய் + உயிர் (புணரியல் 37)."""
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if _is_consonant(ch):
            if nxt == PULLI:
                out.append(ch + PULLI)
                i += 2
            elif nxt in _SIGN_TO_UYIR:
                out += [ch + PULLI, _SIGN_TO_UYIR[nxt]]
                i += 2
            else:
                out += [ch + PULLI, "அ"]
                i += 1
        else:
            out.append(ch)   # an உயிர், ஃ, or anything else passes through as itself
            i += 1
    return out


def render(ps: list[str]) -> str:
    """Phonemes → letters. A மெய் followed by an உயிர் fuses into one letter (புணரியல் 36)."""
    out: list[str] = []
    i = 0
    while i < len(ps):
        p = ps[i]
        if p.endswith(PULLI) and i + 1 < len(ps) and ps[i + 1] in UYIR:
            base, v = p[:-1], ps[i + 1]
            out.append(base + _UYIR_TO_SIGN.get(v, ""))
            i += 2
        else:
            out.append(p)
            i += 1
    return "".join(out)


def _is_mei(p: str) -> bool:
    return p.endswith(PULLI)


def _letters(ps: list[str]) -> int:
    """Letter count of a phoneme list (an உயிர்மெய் is one letter)."""
    return len(render(ps).replace(PULLI, ""))


# --- the rule table ---

@lru_cache(maxsize=1)
def table() -> dict:
    try:
        return json.loads(config.GRAMMAR_PUNARCHI_FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def rules() -> dict[str, dict]:
    return {r["id"]: r for r in table().get("join_rules", [])}


def cite_record(r: dict, label: str) -> list[SourceRef]:
    """A rule's or a stem alternant's citations as SourceRefs: its நூற்பா first, each quoted from
    the pinned edition, then the verified commentary passages, then a course book if any."""
    refs: list[SourceRef] = []
    for c in r.get("cites", []):
        if c.get("authority") == "Tholkappiyam":
            refs.append(classical.cite_tholkappiyam(
                c["athikaram"], c["iyal"], c["verse"], f"{label} — {c.get('role', '')}"))
        elif c.get("authority") == "Nannūl":
            refs.append(classical.cite_nannul(c["verse"], f"{label} — {c.get('role', '')}"))
    urai = r.get("urai", [])
    for qid in [urai] if isinstance(urai, str) else urai:
        refs.append(classical.cite_urai(qid, label))
    tb = r.get("textbook")
    if tb:
        refs.append(SourceRef(name="thamizh-mcp cited rule tables", tier="anchor",
                              ref=tb["source"] + " (Tamil Virtual Academy, CC BY-SA 4.0)",
                              verse_text=tb["quote"]))
    return refs


def cite(rule_id: str) -> list[SourceRef]:
    """The rule's citations as SourceRefs, each quoting its நூற்பா from the pinned edition."""
    r = rules().get(rule_id, {})
    return cite_record(r, r.get("name", rule_id))


@lru_cache(maxsize=1)
def _alternants() -> dict[str, list[dict]]:
    """lemma → the cited ways its பகுதி may surface, table entries first, curated paradigms after."""
    out: dict[str, list[dict]] = {}
    for e in table().get("stem_alternants", {}).get("entries", []):
        out.setdefault(e["lemma"], []).append(e)
    try:
        paradigms = json.loads(config.VERB_PARADIGMS_FILE.read_text("utf-8")).get("paradigms", {})
    except (OSError, ValueError):
        paradigms = {}
    for tense, entries in paradigms.items():
        for p in entries:
            stem, marker, lemma = p.get("stem", ""), p.get("marker", ""), p.get("lemma", "")
            if not (stem and marker and stem.endswith(marker)):
                continue
            surface = stem[: len(stem) - len(marker)]
            if surface and surface != lemma and all(a["surface"] != surface for a in out.get(lemma, [])):
                out.setdefault(lemma, []).append({
                    "lemma": lemma, "surface": surface, "change": None,
                    "source": "data/verb_paradigms.json (curated)",
                    "quote": p.get("note"),
                    "note": "curated paradigm stem; its விகாரம் label is open under ruling (a)"})
    return out


# --- parts and the search ---

@dataclass
class Part:
    form: str
    kind: str          # stem · idainilai · sariyai · vikuthi · case · plural · modern
    surface: str = ""  # filled in by the search


@dataclass
class _State:
    segs: list[list]                      # [[owner, phonemes]]: owner is a part index or a step
    steps: list[JoinStep] = field(default_factory=list)


@dataclass
class Junction:
    """Material a join contributed that is NOT one of the FST's parts (ந், a doubled ஒற்று)."""
    after: int          # it sits after part index `after`
    rule: str
    form: str
    surface: str


@dataclass
class RoundTripResult:
    holds: bool
    rebuilt: str
    parts: list[Part]
    steps: list[JoinStep]
    junctions: list[Junction]
    stem_note: Optional[dict] = None
    unaccounted: Optional[str] = None


def _step(rule_id: str, at: str, effect: str) -> JoinStep:
    r = rules().get(rule_id, {})
    return JoinStep(rule=rule_id, name=r.get("name", rule_id), at=at, effect=effect,
                    status=r.get("status", "parked"), sources=cite(rule_id))


def _tail(st: _State) -> list[str]:
    return st.segs[-1][1]


def _apply(rule_id: str, st: _State, left: Part, right: Part, rp: list[str],
           verb: bool, li: int) -> Optional[tuple[_State, list[str]]]:
    """Apply one join rule at the boundary left|right. Returns the new state and the right part's
    phonemes, or None if the rule's condition does not hold here. Never mutates `st`."""
    segs = [[o, list(p)] for o, p in st.segs]
    lp = segs[-1][1]
    at = f"{left.form} | {right.form}"
    if not lp or not rp:
        return None
    if rule_id == "ukaram_kedal":
        if len(lp) >= 2 and lp[-1] == "உ" and _is_mei(lp[-2]) and rp[0] in UYIR:
            segs[-1][1] = lp[:-1]
            return _State(segs, st.steps + [_step(rule_id, at, f"உ of {left.form} drops before {render(rp[:1])}")]), rp
        return None
    if rule_id == "udambadumei":
        if lp[-1] in UYIR and rp[0] in UYIR:
            glides = ["ய்"] if lp[-1] in "இஈஐ" else (["ய்", "வ்"] if lp[-1] == "ஏ" else ["வ்"])
            g = glides[0]
            segs.append([("j", rule_id), [g]])
            return _State(segs, st.steps + [_step(rule_id, at, f"{g} appears between the vowels")]), rp
        return None
    if rule_id == "otru_irattal":
        if verb or right.kind != "case":
            return None
        # ...ட்/ற் + உ, with a long first letter (two-letter word) or a vowel before (உயிர்த்தொடர்)
        if len(lp) >= 3 and lp[-1] == "உ" and lp[-2] in ("ட்", "ற்") and lp[-3] in UYIR:
            if _letters(lp) == 2 and lp[-3] not in NEDIL:
                return None
            segs[-1][1] = lp[:-1] + [lp[-2], "உ"]
            return _State(segs, st.steps + [_step(rule_id, at, f"{lp[-2]} doubles before the case ending")]), rp
        return None
    if rule_id == "urubu_vallinam_mikuthal":
        if verb or right.kind != "case" or rp[0] not in VALLINAM:
            return None
        segs.append([("j", rule_id), [rp[0]]])
        return _State(segs, st.steps + [_step(rule_id, at, f"{rp[0]} doubles before {right.form}")]), rp
    if rule_id == "athu_otru_kedal":
        if right.kind == "sariyai" and right.form in ("அத்து", "வற்று") and _is_mei(lp[-1]):
            segs[-1][1] = lp[:-1]
            return _State(segs, st.steps + [_step(rule_id, at, f"final {lp[-1]} drops before {right.form}")]), rp
        return None
    if rule_id == "athu_akaram_kedal":
        if right.form == "அத்து" and lp[-1] == "அ" and rp[0] == "அ":
            return _State(segs, st.steps + [_step(rule_id, at, "the அ of அத்து drops after அ")]), rp[1:]
        return None
    if rule_id == "makaram_inam":
        if lp[-1] == "ம்" and rp[0] in VALLINAM and _INAM[rp[0]] != "ம்":
            segs[-1][1] = lp[:-1] + [_INAM[rp[0]]]
            return _State(segs, st.steps + [_step(rule_id, at, f"ம் becomes {_INAM[rp[0]]} before {rp[0]}")]), rp
        return None
    if rule_id == "idainilai_na":
        if verb and right.kind == "idainilai" and right.form == "த்" and lp[-1] in UYIR:
            segs.append([("j", rule_id), ["ந்"]])
            return _State(segs, st.steps + [_step(
                rule_id, at, "இடைநிலை எழுத்து ந் comes before the tense letter த்")]), rp
        return None
    if rule_id == "irattitha_otru":
        if verb and rp[0] in VALLINAM and right.kind in ("idainilai", "vikuthi"):
            segs.append([("j", rule_id), [rp[0]]])
            return _State(segs, st.steps + [_step(
                rule_id, at, f"இடைநிலை எழுத்து {rp[0]} appears before {rp[0]}")]), rp
        return None
    return None


# Rules tried at a boundary, alone or as an ordered pair. Classical first, then the rules a
# commentary states (D-028), so an உரை is used only when no நூற்பா rebuilds the word.
_ORDER = ["athu_otru_kedal", "athu_akaram_kedal", "otru_irattal", "ukaram_kedal", "udambadumei",
          "urubu_vallinam_mikuthal", "makaram_inam", "idainilai_na", "irattitha_otru"]
_COMBOS: list[tuple[str, ...]] = [()] + [(r,) for r in _ORDER] + [
    ("athu_otru_kedal", "athu_akaram_kedal"),
    ("otru_irattal", "ukaram_kedal"),
    ("otru_irattal", "urubu_vallinam_mikuthal"),
]


def _search(parts: list[Part], stem_ps: list[str], target: list[str], verb: bool) -> list[_State]:
    """Every way the cited joins rebuild `target` from these parts (depth-first, pruned)."""
    found: list[_State] = []

    def fixed_prefix(st: _State) -> list[str]:
        return [p for _, ps in st.segs[:-1] for p in ps]

    def go(i: int, st: _State) -> None:
        pre = fixed_prefix(st)
        if target[: len(pre)] != pre:
            return
        if i == len(parts):
            flat = [p for _, ps in st.segs for p in ps]
            if flat == target:
                found.append(st)
            return
        right = parts[i]
        rp0 = phonemes(right.form)
        for combo in _COMBOS:
            cur, rp, ok = st, rp0, True
            for rid in combo:
                res = _apply(rid, cur, parts[i - 1], right, rp, verb, i - 1)
                if res is None:
                    ok = False
                    break
                cur, rp = res
            if not ok:
                continue
            go(i + 1, _State(cur.segs + [[i, list(rp)]], cur.steps))

    go(1, _State([[0, list(stem_ps)]]))
    return found


def _cost(st: _State) -> tuple[int, int, int, int]:
    """Fewest parked steps, then fewest textbook steps, then fewest commentary steps, then fewest
    steps: a நூற்பா outranks a classical உரை, which outranks a course book (D-028)."""
    return (sum(s.status == "parked" for s in st.steps),
            sum(s.status == "textbook" for s in st.steps),
            sum(s.status == "urai" for s in st.steps), len(st.steps))


def round_trip(word: str, parts: list[Part], verb: bool) -> RoundTripResult:
    """Find a split of `word` into `parts` that the cited joins rebuild, or report why none does."""
    target = phonemes(word)
    stem = parts[0].form
    candidates: list[tuple[str, Optional[dict]]] = [(stem, None)]
    candidates += [(a["surface"], a) for a in _alternants().get(stem, [])]
    for surface, alt in candidates:
        sols = _search(parts, phonemes(surface), target, verb)
        if not sols:
            continue
        best = min(sols, key=_cost)
        out = [Part(p.form, p.kind) for p in parts]
        junctions: list[Junction] = []
        last_part = 0
        for owner, ps in best.segs:
            if isinstance(owner, int):
                out[owner].surface = render(ps)
                last_part = owner
            else:
                rid = owner[1]
                r = rules().get(rid, {})
                junctions.append(Junction(after=last_part, rule=rid,
                                          form=r.get("form") or render(ps), surface=render(ps)))
        # Rebuild from the joined segments themselves, never echo the input: `holds` must be a
        # comparison the reader could repeat, not an assertion.
        rebuilt = render([p for _, ps in best.segs for p in ps])
        return RoundTripResult(rebuilt == word, rebuilt, out, best.steps, junctions, stem_note=alt)
    # No split rebuilds the word. Report the plain join so the reader sees what the parts make.
    plain = render([p for part in parts for p in phonemes(part.form)])
    return RoundTripResult(False, plain, [Part(p.form, p.kind) for p in parts], [], [],
                           unaccounted=_unaccounted(word, plain))


def _unaccounted(word: str, rebuilt: str) -> str:
    """The letters of `word` that the rebuilt string does not contain, in order."""
    import difflib
    a, b = phonemes(word), phonemes(rebuilt)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    missing = [render(a[i1:i2]) for tag, i1, i2, _, _ in sm.get_opcodes() if tag in ("delete", "replace")]
    return " · ".join(m for m in missing if m) or ""


def joins_all(*forms: str, kinds: Optional[list[str]] = None, verb: bool = False) -> set[str]:
    """Every word the cited joins can build from these forms. For tests and fixtures: the urai's
    worked examples must be among them."""
    kinds = kinds or ["stem"] + ["case"] * (len(forms) - 1)
    parts = [Part(f, k) for f, k in zip(forms, kinds)]
    words: set[str] = set()

    def go(i: int, st: _State) -> None:
        if i == len(parts):
            words.add(render([p for _, ps in st.segs for p in ps]))
            return
        rp0 = phonemes(parts[i].form)
        for combo in _COMBOS:
            cur, rp, ok = st, rp0, True
            for rid in combo:
                res = _apply(rid, cur, parts[i - 1], parts[i], rp, verb, i - 1)
                if res is None:
                    ok = False
                    break
                cur, rp = res
            if ok:
                go(i + 1, _State(cur.segs + [[i, list(rp)]], cur.steps))

    go(1, _State([[0, phonemes(parts[0].form)]]))
    return words
