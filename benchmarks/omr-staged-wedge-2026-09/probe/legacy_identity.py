"""Is `export._wedge_anchors` the SAME FUNCTION after the refactor?

⚠️⚠️ THIS EXISTS BECAUSE THE OBVIOUS CONTROL WAS VACUOUS. The first attempt
at proving the refactor byte-identical exported three committed
transcriptions before and after and compared md5s. All three matched — and
`grep -c '<wedge'` on every one of them is **ZERO**. The detector fires on a
hairpin ~never on a scan (1 across eleven scanned pages against a truth of
198), so those files never call `_wedge_anchors` at all: the control could
not have failed, which is this repo's own definition of worse than no
control.

So the control is applied where the function actually runs. It drives
`_wedge_anchors` DIRECTLY over a corpus of synthetic staves built from the
same shapes `tools/omr/tests/test_export.py::TestHairpins` uses — every
branch of the rule: the between-notes case, the degenerate one-note case,
the one-anchor case, the no-candidates case, the cross-barline merge, the
stop-reach cliff on both sides, the start-rule tie, and the +1 measure
window.

Run it on the tree BEFORE the change, then on the tree after, and diff:

    python3 benchmarks/omr-staged-wedge-2026-09/probe/legacy_identity.py \\
        > benchmarks/omr-staged-wedge-2026-09/out/legacy-anchors.txt

⚠️ Its own positive control is printed FIRST: the number of cases in which
`_wedge_anchors` returned a real answer rather than None. A run reporting
`answered: 0` proves nothing and says so.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import export as E  # noqa: E402


def _head(x, y=100, w=10, m=0):
    """One notehead detection, page pixels, `bbox_page` = (x, y, w, h)."""
    return {"category": "notehead", "class": "noteheadBlackInSpace",
            "confidence": 0.9, "bbox_page": [x, y, w, 10],
            "pitch": "C4", "duration_beats": 1.0}


def _measures(rows):
    """`rows` is a list of per-measure notehead x positions."""
    return [{"measure_index": i, "detections": [_head(x) for x in xs]}
            for i, xs in enumerate(rows)]


#: `(name, measure notehead xs, segments)`. `segments` is the shape
#: `_merge_arcs_across_barlines` hands `_wedge_anchors`: a list of
#: `(measure_index, [x, y, w, h])`.
CASES = [
    ("between two notes", [[10, 70]], [(0, [30, 60, 38, 8])]),
    ("under one long note", [[10], [110]], [(0, [30, 60, 60, 8])]),
    ("one anchor is enough", [[10]], [(0, [30, 60, 60, 8])]),
    ("no candidates at all", [[]], [(0, [30, 60, 30, 8])]),
    ("cross-barline, two segments",
     [[10], [190]], [(0, [30, 60, 70, 8]), (1, [100, 60, 85, 8])]),
    ("stop reach: next note just inside",
     [[10, 70]], [(0, [30, 60, 35, 8])]),
    ("stop reach: next note far past",
     [[10, 400]], [(0, [30, 60, 35, 8])]),
    ("start rule: note astride the left edge",
     [[28, 90]], [(0, [30, 60, 50, 8])]),
    ("window reaches the NEXT measure",
     [[10], [130]], [(0, [30, 60, 60, 8])]),
    ("window does NOT reach two measures on",
     [[10], [], [], []], [(3, [330, 60, 30, 8])]),
    ("hairpin entirely before the first note",
     [[300]], [(0, [10, 60, 30, 8])]),
    ("three measures of ink", [[10], [110], [210]],
     [(0, [30, 60, 60, 8]), (1, [100, 60, 100, 8]),
      (2, [200, 60, 15, 8])]),
]


def main() -> int:
    lines, answered = [], 0
    for name, rows, segments in CASES:
        measures = _measures(rows)
        try:
            got = E._wedge_anchors(measures, segments, {})
        except Exception as exc:                              # noqa: BLE001
            lines.append(f"{name}: RAISED {type(exc).__name__}: {exc}")
            continue
        if got is None:
            lines.append(f"{name}: None")
            continue
        answered += 1
        (sm, sx), (tm, tx), first, last = got
        lines.append(
            f"{name}: start=(m{sm}, x{sx:.4f}, box{first['bbox_page']}) "
            f"stop=(m{tm}, x{tx:.4f}, box{last['bbox_page']})")

    # ⚠️ THE POSITIVE CONTROL, PRINTED FIRST. A refactor that broke the
    # function into always returning None would produce a file of `None`
    # lines that still diffs clean against itself — this is the number that
    # says the instrument was live.
    print(f"answered: {answered} of {len(CASES)} cases")
    if answered == 0:
        print("⚠️ INSTRUMENT DEAD — no case produced an anchor. "
              "A clean diff of this file means nothing.")
    for line in lines:
        print(line)
    return 0 if answered else 1


if __name__ == "__main__":
    raise SystemExit(main())
