"""நச்சினார்க்கினியர் உரை on எழுத்ததிகாரம் (D-024): pinned, aligned to our verses BY TEXT."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from thamizh_mcp import config
from thamizh_mcp.core import classical


@pytest.fixture(scope="module")
def urai():
    return json.loads((config.CLASSICAL_DIR / "tholkappiyam_eluthu_urai.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def eluthu():
    t = json.loads((config.CLASSICAL_DIR / "tholkappiyam.json").read_text("utf-8"))
    return t["athikaram"]["எழுத்ததிகாரம்"]


def test_header_travels_with_the_commentary(urai):
    assert urai["attribution"].startswith("© Project Madurai")
    assert "header page is kept intact" in urai["attribution"]
    assert classical.attribution("tholkappiyam_eluthu_urai") == urai["attribution"]


def test_every_one_of_our_verses_is_accounted_for(urai, eluthu):
    """Aligned, printed merged with a neighbour, or absent from the etext. Nothing silent."""
    al = urai["alignment"]
    ours = {(iy, n) for iy, vs in eluthu.items() for n in vs}
    aligned = {(u["aligned_to"]["iyal"], u["aligned_to"]["verse"]) for u in urai["units"]
               if u["aligned_to"]}
    merged = {(m["iyal"], m["verse"]) for m in al["merged_in_commentary"]}
    missing = {(m["iyal"], m["verse"]) for m in al["unaligned_ours"]}
    assert aligned | merged | missing == ours
    assert len(aligned) >= 475
    assert len(missing) == len(al["absent_from_etext"]), "each unaligned verse is an etext gap"


def test_alignment_is_by_text_and_strong(urai):
    scores = [u["match"] for u in urai["units"] if u["aligned_to"]]
    assert min(scores) >= 0.6
    assert sorted(scores)[len(scores) // 2] >= 0.95


def test_numbering_is_never_used_as_a_key(urai):
    """The commentary's n is continuous; ours restarts per இயல். A unit far into the text must be
    aligned to a small in-இயல் number, which a number-keyed lookup could never produce."""
    late = next(u for u in urai["units"] if u["n"] == 300)
    assert int(late["aligned_to"]["verse"]) < 300
    assert "NOT a key" in urai["numbering"]


def test_commentary_carries_worked_examples(urai):
    with_ex = [u for u in urai["units"] if u["examples"]]
    assert len(with_ex) >= 300
    assert all(re.search(r"எ\s*-\s*டு|உதாரணம்", e) for u in with_ex for e in u["examples"])


def test_runtime_accessor_uses_our_coordinates():
    u = classical.tholkappiyam_urai("எழுத்ததிகாரம்", "நூல் மரபு", 26)
    assert u is not None and "னஃகான்" in u["verse"]
    assert any("வரும்" in e and "எண்கு" in e for e in u["examples"])   # "… எனவும் வரும்"
    assert classical.tholkappiyam_urai("பொருளதிகாரம்", "அகத்திணையியல்", 1) is None   # not pinned yet


def test_a_verse_printed_merged_still_resolves():
    u = classical.tholkappiyam_urai("எழுத்ததிகாரம்", "பிறப்பியல்", 21)
    assert u is not None
    assert {"iyal": "பிறப்பியல்", "verse": "21"} in (u["also_covers"] or [])
