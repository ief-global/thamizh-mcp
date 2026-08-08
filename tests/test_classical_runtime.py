"""Runtime access to the pinned classical texts (D-018) — quoting the நூற்பா, not just citing it.

`test_citations.py` already proves every நூற்பா number a rule table cites exists in the pinned
edition. That is a DESIGN-time guard. These tests cover the RUNTIME half: that a claim reaching a
user can carry the verse itself, and that a missing verse degrades to None rather than a fabrication.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.core import classical
from thamizh_mcp.core.decoder import NANNOOL_PAKUPADAM, THOLKAPPIYAM_PUNARIYAL


def test_nannul_133_names_the_six_pakupada_urupu():
    """The verse the whole பகுபத decoder rests on. It sat unread in the repo for three sessions
    while the question of what a doubled consonant is called went round in circles."""
    v = classical.nannul_verse(133)
    assert v is not None
    for urupu in ("பகுதி", "விகுதி", "இடைநிலை", "சாரியை", "சந்தி", "விகாரம்"):
        assert urupu in v, f"நன்னூல் 133 must name {urupu}"


def test_nannul_140_carries_the_vikuthi_inventory():
    v = classical.nannul_verse(140)
    assert v and "ஆன்" in v and "ஆள்" in v, "the விகுதி inventory vikuthi.json cites"


def test_tholkappiyam_needs_all_three_coordinates():
    """நூற்பா numbers RESTART per இயல் and collide across இயல் and அதிகாரம், so the API has no
    bare-number form. புணரியல் 7 names the three விகாரம்."""
    v = classical.tholkappiyam_verse("எழுத்ததிகாரம்", "புணரியல்", 7)
    assert v is not None
    for vikaram in ("பிறிது ஆதல்", "மிகுதல்", "குன்றல்"):
        assert vikaram in v

    # the same bare number in a different இயல் is a different verse — proving the collision is real
    other = classical.tholkappiyam_verse("எழுத்ததிகாரம்", "மொழி மரபு", 7)
    assert other is not None and other != v


def test_a_verse_the_edition_does_not_print_is_none_not_invented():
    assert classical.nannul_verse(9999) is None
    assert classical.nannul_verse(classical.NANNUL_TOTAL + 1) is None
    assert classical.tholkappiyam_verse("எழுத்ததிகாரம்", "புணரியல்", 9999) is None
    assert classical.tholkappiyam_verse("நடத்தல்", "இல்லை", 1) is None


def test_a_missing_artifact_costs_quotation_not_a_crash(monkeypatch, tmp_path):
    """Losing the pinned texts must degrade to citation-without-quotation, never raise."""
    from thamizh_mcp import config
    monkeypatch.setattr(config, "CLASSICAL_DIR", tmp_path)
    classical._load.cache_clear()
    try:
        assert classical.nannul_verse(133) is None
        ref = classical.cite_nannul(133, "x")
        assert ref.verse == "நூற்பா 133" and ref.verse_text is None
    finally:
        classical._load.cache_clear()


# --- the decoder's own citations -----------------------------------------------------------------

def test_decoder_citations_quote_their_verse():
    for ref in (NANNOOL_PAKUPADAM, THOLKAPPIYAM_PUNARIYAL):
        assert ref.verse, f"{ref.name} citation lost its நூற்பா address"
        assert ref.verse_text, f"{ref.name} cites {ref.verse} but does not quote it"


def test_tholkappiyam_verse_label_is_qualified_never_a_bare_number():
    """A bare Tholkappiyam number is ambiguous — the label must name அதிகாரம் and இயல்."""
    assert "›" in THOLKAPPIYAM_PUNARIYAL.verse
    assert "எழுத்ததிகாரம்" in THOLKAPPIYAM_PUNARIYAL.verse
    assert "புணரியல்" in THOLKAPPIYAM_PUNARIYAL.verse


def test_the_stale_phase_4_retrieved_string_is_gone():
    """`retrieved` claimed the edition would be pinned 'in Phase 4' long after D-011 pinned it."""
    for ref in (NANNOOL_PAKUPADAM, THOLKAPPIYAM_PUNARIYAL):
        assert "Phase 4" not in (ref.retrieved or "")
    assert "Madurai" in (NANNOOL_PAKUPADAM.retrieved or "")


def test_attribution_is_available_for_any_surface_that_quotes():
    """Project Madurai grants distribution PROVIDED its header travels with the text, so a UI that
    quotes a verse must be able to fetch the credit."""
    assert classical.attribution("nannul")
    assert classical.attribution("tholkappiyam")
