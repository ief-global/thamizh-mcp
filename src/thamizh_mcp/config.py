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

# Sanskrit-To-Pure-Tamil (S2PT) equivalents — வடசொல் → தனித்தமிழ் community lists.
#
# RENAMED 2026-08-08: upstream is `narVidhai/Sanskrit-To-Pure-Tamil-Dictionary`. We had it as
# "Indic-To-Pure-Tamil" — GitHub silently redirects the old path, so the stale name survived. The
# scope matters: the lists are explicitly **வடசொல்** (its README is titled "வடசொல் to தமிழ்"), not
# Indic-in-general, so membership is evidence of a SANSKRIT source, not merely "borrowed".
#
# PROVISIONAL source (D-012 said so; D-017 records why it matters): four scraped community purist
# lists, no upstream LICENCE file, last upstream commit 2020. Confidence is capped and the evidence
# string says what it is — see core/classifier.py. To be superseded by an authenticated glossary.
EQUIVALENTS_DIR = Path(os.environ.get(
    "THAMIZH_EQUIVALENTS_DIR", REPO_ROOT / "data" / "equivalents" / "sanskrit-to-pure-tamil"))
S2PT_SUBLISTS = ("viruba.csv", "tamilchol.csv", "thamizhdna-org.csv", "tamilmandram.csv")
S2PT_PIN = "narVidhai/Sanskrit-To-Pure-Tamil-Dictionary@f734646 (2026-07-02)"

# Pinned classical texts (D-011) — read at RUNTIME so a claim can quote its நூற்பா, not merely
# cite a number (D-018). Verse-addressable; rebuilt/verified by scripts/build_classical.py.
CLASSICAL_DIR = Path(os.environ.get(
    "THAMIZH_CLASSICAL_DIR", REPO_ROOT / "data" / "classical"))

# English-loanword evidence (ANCHOR, pinned artifact) — names the source of a modern borrowing
# that no etymology source covers. Built by scripts/build_english_loans.py from Google Dakshina
# (CC BY-SA 4.0) + a public-domain English wordlist; the artifact inherits CC BY-SA, NOT Apache-2.0.
# Consulted ONLY where orthography already proves non-nativeness — see adapters/loanwords.py.
ENGLISH_LOANS_FILE = Path(os.environ.get(
    "THAMIZH_ENGLISH_LOANS", REPO_ROOT / "data" / "loanwords" / "english_loans.json"))
ENGLISH_LOANS_PIN = "Dakshina v1.0 (2020-05-27) + dwyl/english-words; built 2026-08-08"

DEFAULT_DB = Path(os.environ.get("THAMIZH_DB", REPO_ROOT / "data" / "knowledge.sqlite3"))

# Transaction logging (blueprint §12): every resolved analysis is logged as gold data, on by default.
TXN_LOG = os.environ.get("THAMIZH_TXN_LOG", "1") not in ("0", "false", "no", "")
# Contamination guard (D-005): words listed here are flagged eval_fixture on every logged transaction
# so the data-curation skill can drop them from published datasets. thamizh-eval extends the file.
EVAL_FIXTURES_FILE = Path(os.environ.get("THAMIZH_EVAL_FIXTURES", REPO_ROOT / "data" / "eval_fixtures.json"))

# Curated irregular-verb paradigms (anchor) — fills FST lexicon gaps; see adapters/paradigms.py.
VERB_PARADIGMS_FILE = Path(os.environ.get(
    "THAMIZH_VERB_PARADIGMS", REPO_ROOT / "data" / "verb_paradigms.json"))

# Cited grammar rule tables (Nannūl / TVA-verified) — the canonical உறுப்பு names the FST does not give.
GRAMMAR_IDAINILAI_FILE = Path(os.environ.get(
    "THAMIZH_IDAINILAI", REPO_ROOT / "data" / "grammar" / "idainilai.json"))
GRAMMAR_VIKUTHI_FILE = Path(os.environ.get(
    "THAMIZH_VIKUTHI", REPO_ROOT / "data" / "grammar" / "vikuthi.json"))
GRAMMAR_SARIYAI_FILE = Path(os.environ.get(
    "THAMIZH_SARIYAI", REPO_ROOT / "data" / "grammar" / "sariyai.json"))
GRAMMAR_VERRUMAI_FILE = Path(os.environ.get(
    "THAMIZH_VERRUMAI", REPO_ROOT / "data" / "grammar" / "verrumai_urubu.json"))
GRAMMAR_VIKARAM_FILE = Path(os.environ.get(
    "THAMIZH_VIKARAM", REPO_ROOT / "data" / "grammar" / "vikaram.json"))


def flookup_available() -> bool:
    return bool(FLOOKUP) and Path(FLOOKUP).exists() and FST_DIR.is_dir()


def eval_fixture_words() -> frozenset[str]:
    """NFC-normalized set of eval/regression words to exclude from published data (best-effort load)."""
    import json
    import unicodedata
    try:
        data = json.loads(EVAL_FIXTURES_FILE.read_text("utf-8"))
        return frozenset(unicodedata.normalize("NFC", w) for w in data.get("words", []))
    except (OSError, ValueError):
        return frozenset()
