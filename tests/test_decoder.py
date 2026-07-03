import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.core import decoder


def test_pos_map_tholkappiyam_frame():
    assert decoder.map_pos("noun") == "பெயர்ச்சொல்"
    assert decoder.map_pos("verb") == "வினைச்சொல்"
    assert decoder.map_pos("part") == "இடைச்சொல்"
    assert decoder.map_pos("adj") == "உரிச்சொல்"
    assert decoder.map_pos("xyz") == "unknown"
    assert decoder.word_class_of("பெயர்ச்சொல்") == "பெயர்"


def test_case_map_eight_vetrumai():
    loc = decoder.map_case(["infInc", "loc"])
    assert loc.number == 7 and "ஏழாம்" in loc.name
    assert decoder.map_case(["nom"]).number == 1
    assert decoder.map_case(["soc"]).number == 3   # sociative sits in the 3rd case
    assert decoder.map_case(["voc"]).number == 8
    assert decoder.map_case(["infInc"]) is None
