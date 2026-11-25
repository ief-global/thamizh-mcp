"""The classical commentaries on சொல்லதிகாரம் (D-027): pinned scans, OCR aligned to our verses BY TEXT."""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest

from thamizh_mcp import config
from thamizh_mcp.core import classical
import build_sol_urai

ARTIFACTS = {"நச்சினார்க்கினியர்": "tholkappiyam_sol_urai_nacchinarkkiniyar",
             "இளம்பூரணர்": "tholkappiyam_sol_urai_ilampuranar"}
CONS = re.compile(r"[க-ஹ]")


def _load(name):
    return json.loads((config.CLASSICAL_DIR / f"{name}.json").read_text("utf-8"))


def _skel(s):
    return "".join(CONS.findall(s))


@pytest.fixture(scope="module")
def sol():
    t = json.loads((config.CLASSICAL_DIR / "tholkappiyam.json").read_text("utf-8"))
    return t["athikaram"]["சொல்லதிகாரம்"]


@pytest.mark.parametrize("commentator,name", ARTIFACTS.items())
def test_every_verse_is_aligned_or_listed_unaligned(commentator, name, sol):
    d = _load(name)
    assert d["commentator"] == commentator
    ours = {(iy, n) for iy, vs in sol.items() for n in vs}
    aligned = {(u["aligned_to"]["iyal"], u["aligned_to"]["verse"]) for u in d["units"]}
    unaligned = {(u["iyal"], u["verse"]) for u in d["alignment"]["unaligned_ours"]}
    assert aligned | unaligned == ours and not aligned & unaligned
    assert len(aligned) >= 460


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_alignment_is_by_text_and_strong(name):
    scores = [u["match"] for u in _load(name)["units"]]
    assert min(scores) >= 0.6
    assert sorted(scores)[len(scores) // 2] >= 0.9


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_it_says_it_is_ocr_and_carries_its_licence(name):
    d = _load(name)
    assert d["ocr"]["proof_read"] is False and "scan page" in d["ocr"]["warning"]
    assert "CC BY-SA 4.0" in d["licence"] and "Tamil Virtual Academy" in d["attribution"]
    assert classical.attribution(name) == d["attribution"]


@pytest.mark.parametrize("key", build_sol_urai.SOURCES)
def test_the_artifact_was_built_from_the_pinned_bytes(key):
    src = build_sol_urai.SOURCES[key]
    d = _load(src["artifact"])
    built = {kind: s["sha256"] for s in d["sources"] for kind in src["sha256"]
             if s["file"].endswith(kind)}
    assert built == src["sha256"]
    assert d["scan"]["sha256"] == src["scan_pdf"]["sha256"]


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_every_unit_names_the_scan_pages_it_came_from(name):
    for u in _load(name)["units"]:
        assert u["pages"] and all(isinstance(p["leaf"], int) for p in u["pages"])


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_back_matter_is_not_swallowed_by_the_last_unit(name):
    last = _load(name)["units"][-1]
    assert last["aligned_to"] == {"iyal": "எச்சவியல்", "verse": "67"}
    assert len(last["urai"]) < 20000


def test_runtime_accessor_serves_both_commentators():
    assert classical.commentators("சொல்லதிகாரம்") == ["நச்சினார்க்கினியர்", "இளம்பூரணர்"]
    n = classical.tholkappiyam_urai("சொல்லதிகாரம்", "வினையியல்", 1)
    i = classical.tholkappiyam_urai("சொல்லதிகாரம்", "வினையியல்", 1, commentator="இளம்பூரணர்")
    assert n and i and n is not i
    assert "முதனிலை" in n["urai"]            # வினை யென்றது, முதனிலையை
    assert classical.urai_artifact("சொல்லதிகாரம்", "இளம்பூரணர்") == ARTIFACTS["இளம்பூரணர்"]


def test_verified_quotations_are_still_in_their_units():
    """A passage checked against the scan stays findable, by text, in the unit it is filed under,
    and its leaf is one of that unit's pages. If a rebuild moves it, the citation must be re-checked."""
    vq = json.loads((config.CLASSICAL_DIR / "verified_quotations.json").read_text("utf-8"))
    assert vq["quotations"]
    for q in vq["quotations"]:
        d = _load(q["artifact"])
        u = next(x for x in d["units"] if x["aligned_to"] == q["unit"])
        assert q["leaf"] in [p["leaf"] for p in u["pages"]], q["as_printed"][:30]
        a, b = _skel(q["as_printed"]), _skel(u["verse"] + u["urai"])
        found = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False)
                    .get_matching_blocks())
        assert found / len(a) >= 0.9, q["as_printed"][:30]
