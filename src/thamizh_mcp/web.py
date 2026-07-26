"""FastAPI head — REST API + a browser UI over the same plain-Python engine (blueprint §8).

    uv sync --extra web
    uv run thamizh-web            # → http://127.0.0.1:8080

Why a browser head exists: terminals do not shape Tamil script correctly (vowel signs detach and
reorder), which makes CLI output unreadable for demos and manual testing. Browsers shape it properly.
This is also the REST head the blueprint schedules ahead of the hosted instance — same engine, no
duplicated linguistics.

Endpoints:
    GET /                      the UI
    GET /api/analyze?word=…    full WordAnalysis JSON (&meaning=true adds the live lookup)
    GET /healthz               liveness + whether the FST is available
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from thamizh_mcp import config
from thamizh_mcp.core import engine
from thamizh_mcp.normalize import normalize

app = FastAPI(title="Thamizh MCP", description="Tamil word-grammar analysis (சொல் இலக்கணம்)")

_UI = Path(__file__).with_name("static") / "index.html"

_SECTIONS = ["origin", "root", "formation", "grammar", "native_equivalent"]


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(_UI.read_text("utf-8"))


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "fst_available": config.flookup_available()})


@app.get("/api/analyze")
async def api_analyze(
    word: str = Query(..., min_length=1, max_length=100, description="One Tamil word in Tamil script"),
    meaning: bool = Query(False, description="Also fetch meaning (live network lookup)"),
) -> JSONResponse:
    """Analyze one Tamil word. Mirrors the MCP `analyze_word` contract, over HTTP."""
    try:
        normalized = normalize(word)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    include = [*_SECTIONS, "meaning"] if meaning else list(_SECTIONS)
    analysis = await engine.analyze_word(word, normalized, include=include, allow_enrichment=meaning)
    return JSONResponse(json.loads(analysis.to_json()))


def main() -> None:
    """Entry point for `thamizh-web` (host/port via THAMIZH_WEB_HOST / THAMIZH_WEB_PORT)."""
    import os

    import uvicorn
    uvicorn.run(app, host=os.environ.get("THAMIZH_WEB_HOST", "127.0.0.1"),
                port=int(os.environ.get("THAMIZH_WEB_PORT", "8080")))


if __name__ == "__main__":
    main()
