import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from thamizh_mcp import config
from thamizh_mcp.adapters.base import AdapterResult, NoEntry
from thamizh_mcp.adapters.thamizhimorph import ThamizhiMorphAdapter, parse_flookup


def test_parse_flookup_keeps_all_analyses():
    out = "மரத்தில்\tமரம்+noun+infInc+loc\nமரத்தில்\tமரம்+noun+infInc+soc\n"
    analyses = parse_flookup(out)
    assert [(a.lemma, a.pos, a.tags) for a in analyses] == [
        ("மரம்", "noun", ["infInc", "loc"]), ("மரம்", "noun", ["infInc", "soc"])]


def test_parse_flookup_unknown_is_empty():
    assert parse_flookup("ச克斯\t+?\n") == []
    assert parse_flookup("") == []


def test_unavailable_is_honest_noentry(tmp_path):
    ad = ThamizhiMorphAdapter(flookup=None, fst_dir=tmp_path / "nope")
    res = asyncio.run(ad.lookup("மரம்"))
    assert isinstance(res, NoEntry) and res.reason == "unavailable"


needs_fst = pytest.mark.skipif(not config.flookup_available(),
                               reason="flookup/FSTs not on this machine (see data/PINS.md)")


@needs_fst
def test_live_maram_nominal():
    res = asyncio.run(ThamizhiMorphAdapter().lookup("மரம்"))
    assert isinstance(res, AdapterResult)
    assert any(a.lemma == "மரம்" and a.pos == "noun" for a in res.fields["all_analyses"])
    assert res.sources[0].tier == "anchor"


@needs_fst
def test_live_marathil_ambiguity_preserved():
    res = asyncio.run(ThamizhiMorphAdapter().lookup("மரத்தில்"))
    tags = {tuple(a.tags) for a in res.fields["all_analyses"] if a.lemma == "மரம்"}
    assert ("infInc", "loc") in tags and ("infInc", "soc") in tags  # both kept
