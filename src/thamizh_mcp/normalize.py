"""Input normalization — runs before every lookup (bad normalization corrupts everything).

v0: NFC + trim + Tamil-block validation. Phase 3: open-tamil get_letters for grapheme-aware
handling; reject/route non-Tamil scripts explicitly.
"""
from __future__ import annotations

import unicodedata

_TAMIL_LO, _TAMIL_HI = 0x0B80, 0x0BFF
_ALLOWED_JOINERS = {0x200C, 0x200D}  # ZWNJ / ZWJ — strip, never reject


def normalize(word: str) -> str:
    """NFC-normalize one Tamil word. Raises ValueError with an actionable message otherwise."""
    w = unicodedata.normalize("NFC", word.strip())
    w = "".join(c for c in w if ord(c) not in _ALLOWED_JOINERS)
    if not w:
        raise ValueError("Empty input: provide one Tamil word, e.g. மரம்.")
    if any(c.isspace() for c in w):
        raise ValueError("Multiple tokens received: v1 analyzes a single Tamil word at a time.")
    if not all(_TAMIL_LO <= ord(c) <= _TAMIL_HI for c in w):
        raise ValueError(
            f"Input {w!r} contains non-Tamil characters. Provide the word in Tamil script "
            "(romanized input is out of scope for v1 — see blueprint §1)."
        )
    return w
