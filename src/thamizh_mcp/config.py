"""Runtime configuration — anchor locations, binaries, timeouts. Env-overridable."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ThamizhiMorph anchor (pins in data/PINS.md)
FST_DIR = Path(os.environ.get("THAMIZH_FST_DIR", REPO_ROOT / "data" / "fst"))
FLOOKUP = os.environ.get("THAMIZH_FLOOKUP") or shutil.which("flookup")
FLOOKUP_LIB = os.environ.get("THAMIZH_FLOOKUP_LIB")  # extra LD_LIBRARY_PATH if needed
THAMIZHIMORPH_PIN = "sarves/thamizhi-morph@adbacced (2026-07-02)"

# Primary FSTs (guessers excluded — they invent analyses for unknown words; that is
# exactly the unsourced-guess failure mode this project exists to remove).
PRIMARY_FSTS = ("noun.fst", "pronoun.fst", "adj.fst", "adv.fst", "part.fst",
                "verb-c3.fst", "verb-c4.fst", "verb-c11.fst", "verb-c12.fst",
                "verb-c62.fst", "verb-c-rest.fst")

FLOOKUP_TIMEOUT_S = float(os.environ.get("THAMIZH_FLOOKUP_TIMEOUT", "10"))
HTTP_TIMEOUT_S = float(os.environ.get("THAMIZH_HTTP_TIMEOUT", "10"))

DEFAULT_DB = Path(os.environ.get("THAMIZH_DB", REPO_ROOT / "data" / "knowledge.sqlite3"))


def flookup_available() -> bool:
    return bool(FLOOKUP) and Path(FLOOKUP).exists() and FST_DIR.is_dir()
