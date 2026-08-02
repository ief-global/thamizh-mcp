"""Every நூற்பா cited by a rule table must resolve in the pinned classical artifacts.

This is the enforcement mechanism for D-011 / Tholkappiyam-first. Two failure modes it catches,
both of which have already happened once:

  1. A verse number taken from a secondary source that numbers differently. The TVA course books
     quote Nannūl selectively and their numbering drifts from the pinned edition — TVA's "336"
     (இர்/ஈர்) is 337 in Project Madurai, and its "319" is 320. Cite the pinned edition.
  2. A table shipping without a `source_priority` block, which is how Tholkappiyam-first silently
     inverted in the first place.

If a citation legitimately cannot be resolved (the pinned edition does not print it), record
`verse: null` with a note — do NOT invent a number to make this test pass.
"""
import json
import re
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
GRAMMAR = DATA / "grammar"
CLASSICAL = DATA / "classical"

NANNUL_CITE = re.compile(r"நன்னூல்[,\s]*(?:நூற்பா\s*)?(\d{1,3})")
TABLES = sorted(GRAMMAR.glob("*.json"))


def _load(p: Path) -> dict:
    return json.loads(p.read_text("utf-8"))


@pytest.fixture(scope="module")
def nannul() -> dict:
    return _load(CLASSICAL / "nannul.json")


@pytest.fixture(scope="module")
def tholkappiyam() -> dict:
    return _load(CLASSICAL / "tholkappiyam.json")


def test_classical_artifacts_present():
    assert (CLASSICAL / "nannul.json").is_file()
    assert (CLASSICAL / "tholkappiyam.json").is_file()


def test_nannul_artifact_coverage(nannul):
    cov = nannul["coverage"]
    assert cov["count"] == 462, "Nannūl has exactly 462 நூற்பா"
    assert cov["missing"] == []
    # 73 and 176 are absent from the primary etext and filled from Project Madurai's older page.
    assert cov["supplemented"] == [73, 176]
    assert set(nannul["supplemented"]["verses"]) == {"73", "176"}
    assert nannul["verses"]["244"].startswith("அன் ஆன் இன் அல்")


def test_nannul_verses_are_verses_not_page_furniture(nannul):
    """Guard against the source's own markup leaking into verse text.

    Three separate leaks were found by eyeballing the committed artifact: the table of contents
    parsed as நூற்பா 1–3, mid-body section headings ('2. எழுத்ததிகாரம் 56 - 257') overwriting the
    real நூற்பா 2 and 3, and the colophon plus webpage footer glued onto நூற்பா 462. A citation
    quoting any of these would be quoting page furniture as scripture.
    """
    bad = {
        n: t for n, t in nannul["verses"].items()
        if re.search(r"[A-Za-z]{3,}", t)          # English footer text
        or re.search(r"-{3,}", t)                 # section rule
        or re.search(r"\d+\s*-\s*\d+", t)         # a TOC verse range
        or "முற்றிற்று" in t                       # colophon
    }
    assert not bad, f"page furniture leaked into verses: {sorted(bad)}"


def test_nannul_boundary_verses_exact(nannul):
    """The first and last verses — where TOC and footer contamination lands."""
    v = nannul["verses"]
    assert v["1"] == "முகவுரை பதிகம் அணிந்துரை நூன்முகம் புறவுரை தந்துரை புனைந்துரை பாயிரம்"
    assert v["462"] == "பழையன கழிதலும் புதியன புகுதலும் வழு அல கால வகையின் ஆனே"
    assert nannul["colophon"] == "நன்னூல் முற்றிற்று", "colophon kept as metadata, not as a verse"


def test_tholkappiyam_artifact_grammar_iyal_complete(tholkappiyam):
    """The two இயல் the rule tables actually depend on must have no gaps."""
    cov = tholkappiyam["coverage"]
    assert cov["எழுத்ததிகாரம்"]["புணரியல்"]["missing"] == []
    assert cov["சொல்லதிகாரம்"]["வேற்றுமையியல்"]["missing"] == []
    assert cov["சொல்லதிகாரம்"]["வேற்றுமையியல்"]["count"] == 22


def test_tholkappiyam_upstream_corruption_repaired(tholkappiyam):
    """The upstream pages bake U+FFFD in; the build repairs it to ஃ mechanically."""
    blob = json.dumps(tholkappiyam, ensure_ascii=False)
    assert "�" not in blob
    assert "அஃறிணை" in blob
    assert tholkappiyam["repairs"]["aytham_restored"] > 0


@pytest.mark.parametrize("path", TABLES, ids=lambda p: p.name)
def test_table_declares_source_priority(path):
    """A rule table without source_priority is incomplete — that is how the drift happened."""
    table = _load(path)
    sp = table.get("source_priority")
    assert sp, f"{path.name} is missing source_priority"
    assert sp.get("primary"), f"{path.name} source_priority has no primary"
    assert sp.get("why"), f"{path.name} must say WHY that authority is primary"


@pytest.mark.parametrize("path", TABLES, ids=lambda p: p.name)
def test_nannul_citations_resolve(path, nannul):
    """Every 'நன்னூல் N' anywhere in a table must exist in the pinned edition."""
    verses = nannul["verses"]
    cited = {int(n) for n in NANNUL_CITE.findall(path.read_text("utf-8"))}
    assert cited, f"{path.name} cites no Nannūl verse — unexpected"
    unresolved = sorted(n for n in cited if str(n) not in verses)
    assert not unresolved, (
        f"{path.name} cites Nannūl {unresolved}, absent from the pinned Project Madurai edition. "
        f"Check the number against data/classical/nannul.json — secondary sources renumber."
    )


@pytest.mark.parametrize("path", TABLES, ids=lambda p: p.name)
def test_tholkappiyam_citations_resolve(path, tholkappiyam):
    """Structured Tholkappiyam citations must resolve to (அதிகாரம், இயல், நூற்பா).

    Numbers restart per இயல், so a citation is only checkable with its இயல் — which is exactly why
    the citation format requires it.
    """
    table = _load(path)
    ath_map = tholkappiyam["athikaram"]

    def iyal_verses(ref: str) -> dict | None:
        for iyals in ath_map.values():
            for iyal, verses in iyals.items():
                if iyal in ref:
                    return verses
        return None

    for block in _walk(table):
        ref, verse = block.get("ref"), block.get("verse")
        if not (isinstance(ref, str) and isinstance(verse, str)):
            continue
        verses = iyal_verses(ref)
        if verses is None:  # a Nannūl ref, or an இயல் this table does not cite
            continue
        for num in re.findall(r"\d{1,3}", verse):
            assert num in verses, (
                f"{path.name}: தொல்காப்பியம் {ref} நூற்பா {num} does not exist in the pinned "
                f"edition (that இயல் has {len(verses)} நூற்பா)."
            )


def test_tholkappiyam_primary_tables_cite_it():
    """The tables whose topic Tholkappiyam governs must actually carry a Tholkappiyam citation.

    Named explicitly rather than inferred, because a table may mention Tholkappiyam only to explain
    that it does NOT cover the topic (விகுதி / இடைநிலை — the six உறுப்பு are Nannūl's).
    """
    for name in ("verrumai_urubu.json", "vikaram.json", "sariyai.json"):
        table = _load(GRAMMAR / name)
        blocks = [b for b in _walk(table) if "tholkappiyam" in {k.lower() for k in b}]
        assert blocks, (
            f"{name} is Tholkappiyam-primary but carries no `tholkappiyam` verse block"
        )


def _walk(node):
    """Yield every dict in a nested structure."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_verrumai_third_case_divergence_recorded():
    """The authorities genuinely differ here; collapsing them would be a correctness regression."""
    t = _load(GRAMMAR / "verrumai_urubu.json")
    inst = t["cases"]["inst"]
    assert inst["urubu"][0] == "ஒடு", "Tholkappiyam's ஒடு must lead the third-case உருபு list"
    assert "ஆல்" in inst["urubu"], "Nannūl's ஆல் must still be present"
    assert "DIFFER" in inst["urubu_note"]


def test_vikaram_carries_both_authority_names():
    """Tholkappiyam names the three விகாரம் first; Nannūl's names map onto them."""
    t = _load(GRAMMAR / "vikaram.json")
    assert t["vikaram"]["primary_canonical"] == ["பிறிது ஆதல்", "மிகுதல்", "குன்றல்"]
    for name, spec in t["vikaram"]["types"].items():
        assert spec.get("tholkappiyam_name"), f"{name} lacks its Tholkappiyam name"
