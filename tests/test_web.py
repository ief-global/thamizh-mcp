"""FastAPI head: the REST contract + UI serve. Skipped when the web extra isn't installed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

pytest.importorskip("fastapi", reason="web extra not installed (uv sync --extra web)")
from fastapi.testclient import TestClient  # noqa: E402

from thamizh_mcp.web import app  # noqa: E402

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_ui_is_served_and_tamil_first():
    r = client.get("/")
    assert r.status_code == 200
    assert "சொல் இலக்கணம்" in r.text
    assert "Noto Sans Tamil" in r.text        # the whole point: correct Tamil shaping


def test_analyze_matches_the_mcp_contract():
    r = client.get("/api/analyze", params={"word": "மரத்தில்"})
    assert r.status_code == 200
    d = r.json()
    assert d["normalized"] == "மரத்தில்"
    assert {"origin", "formation", "grammar", "native_equivalent", "gaps", "sources"} <= set(d)


def test_non_tamil_input_is_a_400_with_reason():
    r = client.get("/api/analyze", params={"word": "computer"})
    assert r.status_code == 400 and "non-Tamil" in r.json()["error"]


def test_meaning_is_off_by_default():
    """Default must not hit the network — a demo/test must never hang on a live lookup."""
    d = client.get("/api/analyze", params={"word": "புத்தகம்"}).json()
    assert d["meaning"]["senses"] == []
