"""The classical commentaries on சொல்லதிகாரம் (D-027, D-028): pinned scans, OCR aligned to our
verses BY TEXT."""
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
             "இளம்பூரணர்": "tholkappiyam_sol_urai_ilampuranar",
             "சேனாவரையர்": "tholkappiyam_sol_urai_senavaraiyar"}
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
    vols = build_sol_urai.volumes(src)
    for vol in vols:
        built = {kind: s["sha256"] for s in d["sources"] for kind in vol["sha256"]
                 if s["file"] == f"{vol['stem']}_{kind}"}
        assert built == vol["sha256"], vol["stem"]
    scans = d["scan"].get("volumes") or [d["scan"]]
    assert [s["sha256"] for s in scans] == [v["scan_pdf"]["sha256"] for v in vols]


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_every_unit_names_the_scan_pages_it_came_from(name):
    for u in _load(name)["units"]:
        assert u["pages"] and all(isinstance(p["leaf"], int) for p in u["pages"])


@pytest.mark.parametrize("name", ARTIFACTS.values())
def test_back_matter_is_not_swallowed_by_the_last_unit(name):
    last = _load(name)["units"][-1]
    assert last["aligned_to"] == {"iyal": "எச்சவியல்", "verse": "67"}
    assert len(last["urai"]) < 20000


def test_runtime_accessor_serves_every_commentator():
    assert classical.commentators("சொல்லதிகாரம்") == ["நச்சினார்க்கினியர்", "இளம்பூரணர்", "சேனாவரையர்"]
    s = classical.tholkappiyam_urai("சொல்லதிகாரம்", "வினையியல்", 5, commentator="சேனாவரையர்")
    assert s and "நில்லென்பது" in s["urai"]
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
        if "excerpts" in d:
            # A page-excerpt artifact (the Nannūl commentaries, D-029; பாவாணர், D-031): the passage
            # is on its leaf, and names its commentator and நூற்பா, or its author and section.
            assert (q.get("commentator") and q.get("nannul_verse")) or (
                q.get("author") and q.get("section")), q["id"]
            [ex] = [e for e in d["excerpts"] if e["leaf"] == q["leaf"]]
            body = ex["text"]
        else:
            u = next(x for x in d["units"] if x["aligned_to"] == q["unit"])
            if "leaf" in q:
                assert (q.get("volume"), q["leaf"]) in [(p.get("volume"), p["leaf"])
                                                        for p in u.get("pages", [])], q["id"]
            else:
                # Only a proof-read etext may be quoted without a scan page (D-024).
                assert "proof-read" in q["verified_against"], q["id"]
            body = u["verse"] + u["urai"]
        a, b = _skel(q["as_printed"]), _skel(body)
        found = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False)
                    .get_matching_blocks())
        assert found / len(a) >= 0.9, q["as_printed"][:30]


def test_quotation_ids_are_unique_and_every_rule_citation_resolves():
    vq = json.loads((config.CLASSICAL_DIR / "verified_quotations.json").read_text("utf-8"))
    ids = [q["id"] for q in vq["quotations"]]
    assert len(ids) == len(set(ids))
    g = json.loads((config.GRAMMAR_PUNARCHI_FILE).read_text("utf-8"))
    pv = g["pakuthi_vikaram"]
    rules = g["join_rules"] + pv["rules"] + pv["catalogued_not_applied"] + [pv["framework"]]
    idn = json.loads(config.GRAMMAR_IDAINILAI_FILE.read_text("utf-8"))["idainilai"]
    rules += [e for t in idn.values() for e in t.get("from_fst", {}).values()]
    vk = json.loads(config.GRAMMAR_VIKUTHI_FILE.read_text("utf-8"))["echchavinai"]["vinaiyeccham"]
    rules.append(vk["tense_vikuthi"])
    cited = [i for r in rules for i in r.get("urai", [])]
    assert cited and set(cited) <= set(ids)


def test_the_editors_notes_are_not_in_senavaraiyars_units():
    """The 2018 edition prints சி. கணேசையர்'s notes after each இயல் and its running heads name him.
    A unit is சேனாவரையர்'s verse and உரை only, so neither may leak in."""
    d = _load(ARTIFACTS["சேனாவரையர்"])
    for u in d["units"]:
        assert "கணேசையர்" not in u["urai"] and "முற்றிற்று" not in u["urai"], u["aligned_to"]
        assert all(p.get("volume") in (1, 2) for p in u["pages"])
