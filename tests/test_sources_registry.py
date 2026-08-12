"""D-017 — the source registry is only worth having if omission FAILS.

The defect this closes is not "we shipped a weak source". Weak sources are fine, and the project's
framing is explicit that authenticity comes from every claim carrying a graded, citable provenance
the user can check, not from every source being impeccable. The defect was that S2PT's weakness was
not declared anywhere a machine could read: it was load-bearing for weeks under a "MIT" claim with
no basis upstream, and nothing in the suite could notice.

So the load-bearing assertion here is the boring one — every SourceAdapter that ships has an entry,
and every entry states a licence. `licence_status: "unstated"` is a PASSING value: the registry
records what is true, and "we do not know" is a fact worth recording. What must never pass is
silence.
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
from pathlib import Path

import pytest

from thamizh_mcp import adapters
from thamizh_mcp.adapters.base import SourceAdapter
from thamizh_mcp.core import sources
from thamizh_mcp.schema import SourceRef

REGISTRY_FILE = Path(__file__).resolve().parents[1] / "data" / "sources.json"

VALID_MODES = {"redistribute", "serve-with-attribution", "consult-and-cite"}
REQUIRED_KEYS = {
    "name", "adapter", "tier", "grade", "licence", "licence_status",
    "redistribution", "maintenance", "pin", "supersession", "notes",
}


def _adapter_classes() -> list[type]:
    """Every concrete SourceAdapter subclass in thamizh_mcp.adapters."""
    found: list[type] = []
    for mod in pkgutil.iter_modules(adapters.__path__):
        m = importlib.import_module(f"thamizh_mcp.adapters.{mod.name}")
        for _, obj in inspect.getmembers(m, inspect.isclass):
            if (issubclass(obj, SourceAdapter) and obj is not SourceAdapter
                    and obj.__module__ == m.__name__):
                found.append(obj)
    return found


def test_registry_file_is_present_and_parses():
    assert REGISTRY_FILE.exists(), "data/sources.json is missing — D-017 registry not shipped"
    json.loads(REGISTRY_FILE.read_text("utf-8"))


def test_adapters_were_discovered():
    """Guards the guard: if discovery silently returns nothing, every test below vacuously passes."""
    classes = _adapter_classes()
    assert len(classes) >= 8, f"expected the shipped adapters, discovered only {len(classes)}"


@pytest.mark.parametrize("cls", _adapter_classes(), ids=lambda c: c.__name__)
def test_every_shipped_adapter_has_a_registry_entry(cls):
    """THE assertion of D-017. A source reaching users without a registry entry is exactly the
    S2PT situation: in use, load-bearing, and undescribed."""
    e = sources.entry(cls.name)
    assert e is not None, (
        f"{cls.__name__} ships as '{cls.name}' but has no entry in data/sources.json. "
        "Add one — including its licence, even if the honest value is 'unstated'."
    )


@pytest.mark.parametrize("cls", _adapter_classes(), ids=lambda c: c.__name__)
def test_every_adapter_entry_states_a_licence(cls):
    e = sources.entry(cls.name)
    assert e and e.get("licence"), f"{cls.name}: registry entry states no licence"
    assert e.get("licence_status") in {"stated", "unstated"}, (
        f"{cls.name}: licence_status must be 'stated' or 'unstated', got {e.get('licence_status')!r}"
    )


@pytest.mark.parametrize("cls", _adapter_classes(), ids=lambda c: c.__name__)
def test_every_adapter_entry_points_back_at_its_class(cls):
    """The registry names the adapter it describes, so a rename cannot leave a stale entry behind
    that still looks complete."""
    e = sources.entry(cls.name)
    dotted = f"{cls.__module__}.{cls.__qualname__}"
    assert e.get("adapter") == dotted, (
        f"{cls.name}: registry says adapter={e.get('adapter')!r}, class is {dotted!r}")


@pytest.mark.parametrize("key", sorted(sources.all_sources()))
def test_entry_is_complete_and_well_formed(key):
    e = sources.all_sources()[key]
    missing = REQUIRED_KEYS - set(e)
    assert not missing, f"{key}: registry entry is missing {sorted(missing)}"
    assert e["grade"] in sources.grades(), f"{key}: unknown grade {e['grade']!r}"
    assert e["tier"] in {"anchor", "evolving"}, f"{key}: unknown tier {e['tier']!r}"
    assert e["redistribution"] in VALID_MODES, (
        f"{key}: unknown redistribution mode {e['redistribution']!r}")
    if e.get("attribution_required"):
        assert e.get("attribution"), f"{key}: attribution required but none recorded"


def test_grades_are_ordered_and_capped():
    """A → D must be monotonically decreasing, or 'grade' means nothing to a reader."""
    caps = [sources.grades()[g]["confidence_cap"] for g in ("A", "B", "C", "D")]
    assert caps == sorted(caps, reverse=True), f"grade caps are not ordered A→D: {caps}"
    assert all(0.0 < c <= 1.0 for c in caps)


def test_unregistered_source_gets_the_floor_not_the_benefit_of_the_doubt():
    """An unregistered source is an unreviewed one. If omission were generous, the registry would
    reward skipping it."""
    assert sources.cap_for("a source nobody registered") == sources.UNREGISTERED_CAP
    assert sources.grade_of("a source nobody registered") is None


def test_cap_never_raises_a_confidence():
    """`cap` is a ceiling, not a score. Raising one would let the registry INVENT certainty."""
    assert sources.cap("Nannūl", 0.30) == 0.30
    assert sources.cap("Nannūl", 0.99) <= sources.cap_for("Nannūl")


def test_s2pt_stays_capped_at_the_lowest_committing_score():
    """The classifier emits 0.55 for an S2PT-backed வடசொல் claim and LICENSING.md commits to that
    number in prose. Pinned here so a grade change cannot quietly raise it."""
    s2pt = sources.entry("Sanskrit-To-Pure-Tamil (community தனித்தமிழ் lists)")
    assert s2pt["grade"] == "D"
    assert sources.cap_for(s2pt["name"]) == 0.55
    assert s2pt["licence_status"] == "unstated"
    assert s2pt["supersession"] and s2pt["supersession"]["intent"]


def test_grade_and_redistribution_are_independent_axes():
    """D-016's core finding, asserted rather than merely documented.

    The Madras Tamil Lexicon is the most authoritative lexicon we have AND the most restrictively
    licensed. If a future refactor derives one axis from the other, this fails — which is the whole
    point, because collapsing them is precisely the error D-016 was written to correct.
    """
    mtl = sources.entry("Madras Tamil Lexicon")
    assert mtl["grade"] == "A", "MTL's evidential standing is not diminished by its licence"
    assert mtl["redistribution"] == "consult-and-cite"

    by_mode: dict[str, set[str]] = {}
    for e in sources.all_sources().values():
        by_mode.setdefault(e["redistribution"], set()).add(e["grade"])
    assert any(len(g) > 1 for g in by_mode.values()), (
        "every redistribution mode maps to exactly one grade — the axes have collapsed")


def test_annotate_stamps_grade_licence_and_mode():
    ref = SourceRef(name="Sanskrit-To-Pure-Tamil (community தனித்தமிழ் lists)", tier="evolving")
    sources.annotate(ref)
    assert ref.grade == "D"
    assert ref.redistribution == "serve-with-attribution"
    assert ref.licence and "UNSTATED" in ref.licence.upper()


def test_annotate_leaves_an_unregistered_ref_alone():
    """Better an unstamped ref than a confidently wrong grade."""
    ref = SourceRef(name="not in the registry", tier="evolving")
    sources.annotate(ref)
    assert ref.grade is None and ref.licence is None


def test_describe_names_the_licence_gap_out_loud():
    """A user asking 'on whose authority?' should be told the licence is unstated, not left to
    infer it from a confidence number."""
    text = sources.describe("Sanskrit-To-Pure-Tamil (community தனித்தமிழ் lists)")
    assert "grade D" in text and "UNSTATED" in text


def test_registry_agrees_with_licensing_md_on_the_share_alike_sources():
    """LICENSING.md is authoritative for reasoning, the registry for machine-checkable facts. This
    is what keeps them from drifting — the failure mode that produced the stale MIT claim."""
    prose = (REGISTRY_FILE.parents[1] / "LICENSING.md").read_text("utf-8")
    for name in ("Tamil Wiktionary", "English Wiktionary (etymology)",
                 "Google Dakshina (attested romanizations)"):
        e = sources.entry(name)
        assert "CC BY-SA" in e["licence"], f"{name}: registry lost the share-alike licence"
        assert e["redistribution"] == "serve-with-attribution"
    assert "unstated upstream" in prose, (
        "LICENSING.md no longer records the S2PT gap the registry still declares")
