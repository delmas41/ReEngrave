"""`compose.py` with ONE tie-break changed, to price the lever the ceiling found.

`reference_candidates` ranks its TAIL by `(-size, -labels, -shapes[shape])` —
how many systems share the lineup is already in the ordering. Its HEAD does not
use that term:

    best = max(recurring, key=lambda v: (v.size, len(v.labels)))

so when two systems tie on size AND label count, `max` returns the one that
comes FIRST IN THE DOCUMENT. On Brahms 4 seven systems tie at 16 staves and 15
labels — movement III's page 41 and six of movement IV's — and page 41 wins by
being earlier, which makes movement III's lineup the vocabulary for the whole
document.

This arm breaks that tie by the same shape-frequency term the tail already
uses. Nothing else is touched. `--tag` distinguishes it; `compose.py`'s own
one-read-pass control is unchanged.

⚠️ It is measured, not proposed: the real change would live in `slots.py`.

    compose_shapetie.py PDF --out-dir DIR --pages 0-98 --cache DIR --tag shapetie
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "benchmarks" / "omr-spans-veto-composition-2026-09"
                       / "probe"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr import slots as slots_mod                    # noqa: E402

_real = slots_mod.reference_candidates


def _shape_tie_first(views, most_labelled=None):
    ranked = _real(views, most_labelled)
    if not ranked:
        return ranked
    head = ranked[0]
    shapes = collections.Counter(slots_mod._shape(v) for v in ranked)
    tied = [v for v in ranked
            if v.size == head.size and len(v.labels) == len(head.labels)]
    if len(tied) > 1:
        winner = max(tied, key=lambda v: shapes[slots_mod._shape(v)])
        if winner is not head:
            ranked = [winner] + [v for v in ranked if v is not winner]
    return ranked


def _reference_view(views, most_labelled=None):
    ranked = _shape_tie_first(views, most_labelled)
    return ranked[0] if ranked else None


def _build_reference(views, most_labelled=None):
    best = _reference_view(views, most_labelled)
    return slots_mod._slots_of(best) if best is not None else []


slots_mod.reference_candidates = _shape_tie_first
slots_mod.reference_view = _reference_view
slots_mod.build_reference = _build_reference

# Import the swap arm too, so the 2x2 completes: it installs the same
# `_span_views` call-site change and is inert unless OMR_LINEUP_SWAP_SPLIT is on.
import compose_swap  # noqa: E402,F401
import compose  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(compose.main())
