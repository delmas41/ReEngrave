"""ROADMAP 2.47 — a real barline discarded for a nearby note stem.

Litolff 984073 p2 system 0, x~870: the barline is 59px tall, 6px short of
the staff's own top line and flush with its bottom line; a stem 35px to its
left is 52px tall, also 6px short of top but 7px short of bottom. Both clear
`_detect_barlines_in_window`'s height/width/aspect shape gate, so they reach
`_dedup_barline_candidates` as two candidates under BARLINE_MIN_DISTANCE_PX
apart on most of the system's 11 staves — and the OLD default,
`prefer="leftmost"` (used by `_detect_barlines_per_staff`, the global pass
`Q.MEASURE_PARTITION` is built from), kept the stem (it sits first) and threw
the barline away. Only 2 of 11 staves voted for the real barline; the system
decided 16 bars where the plate prints 17 (`benchmarks/omr-measure-partition-
2026-09/FINDINGS.md` section 8).

⚠️ Both tests here were run RED against the pre-fix tree (`prefer="leftmost"`
still the default in `_detect_barlines_per_staff`) before the fix landed —
`test_sean_case_keeps_the_real_barline_not_the_stem` failed (asserted 835,
the stem, instead of 870), which is the bug this file pins shut.

The control exists because `prefer="tallest"` alone is NOT the fix: a stem
that runs long past its notehead can be taller, in raw pixels, than a short
but genuine barline without ever touching the staff's own top or bottom
line. `prefer="spanning"` requires BOTH ends to land within
`SPAN_TOUCH_TOLERANCE_PX` of the staff's own top/bottom before height
decides between spanning candidates, and falls back to `leftmost` — never to
"tallest" — when nothing in the group spans.
"""
from __future__ import annotations

import numpy as np

from tools.omr import measure_extractor as me
from tools.omr.types import Staff


def _five(top: int, spacing: int = 16) -> list[int]:
    return [top + spacing * i for i in range(5)]


def test_sean_case_keeps_the_real_barline_not_the_stem():
    """x~870 (59px, 6px short of the top line, flush with the bottom) must
    survive over a stem at x~835 (52px, 6px short of top, 7px short of
    bottom) — the exact measured Litolff p2 system-0 geometry."""
    ys = _five(100)                 # line_ys 100,116,132,148,164 -> span 64
    staff = Staff(page_index=0, staff_index=0, line_ys=ys,
                  x_start=800, x_end=950, system_index=0)
    img = np.full((400, 1000), 255, np.uint8)
    for y in ys:
        img[y:y + 2, 800:950] = 0
    # the real barline: measured top_gap=6, h=59, bottom_gap=0 (flush with
    # the band's own bottom edge) once run through the detector's own
    # morphological opening (row ranges tuned to hit those exact numbers,
    # not derived algebraically — the opening kernel trims a row off each
    # end)
    img[105:300, 870:877] = 0
    # the stem, 35px to its left: measured top_gap=6, h=52, bottom_gap=7
    # (stops short of the bottom line)
    img[105:157, 835:837] = 0
    found = me._detect_barlines_per_staff(img, staff, counts={})
    assert found == [873], (
        f"must keep the barline (x~870-873) over the stem (x~835): {found}"
    )


def test_control_a_taller_stem_must_not_beat_a_shorter_spanning_barline():
    """`prefer=\"tallest\"` alone would fail this: the stem (h=74) is taller
    than the barline (h=71), but stops 7px short of the bottom line while
    the barline is within tolerance of both ends. Spanning must win on
    REACHING the staff, not on raw height."""
    ys = [100, 120, 140, 160, 180]  # span 80, line_spacing 20
    staff = Staff(page_index=0, staff_index=0, line_ys=ys,
                  x_start=800, x_end=950, system_index=0)
    img = np.full((400, 1000), 255, np.uint8)
    for y in ys:
        img[y:y + 2, 800:950] = 0
    # genuine barline (measured): h=71, top_gap=6, bottom_gap=4 — both
    # within SPAN_TOUCH_TOLERANCE_PX
    img[105:176, 870:878] = 0
    # a long stem, 35px left (measured): h=74 — TALLER than the barline —
    # top_gap=0, bottom_gap=7, one px past tolerance: must not count as
    # spanning despite being taller
    img[100:173, 835:839] = 0
    found = me._detect_barlines_per_staff(img, staff, counts={})
    assert found == [874], (
        f"the taller stem must not beat the shorter spanning barline: {found}"
    )


def test_spanning_falls_back_to_leftmost_when_nothing_spans():
    """Neither candidate reaches both ends — `prefer=\"spanning\"` must not
    invent a winner tallest wouldn't have needed to; it falls back to
    leftmost, same as the pre-2.47 behaviour, rather than picking the
    taller of two non-spanning columns."""
    counts: dict[str, int] = {}
    # (x_centre, height, top_gap, bottom_gap) — neither spans (every gap > 6)
    found = [(100, 60, 8, 8), (130, 65, 10, 2)]
    kept = me._dedup_barline_candidates(found, prefer="spanning", counts=counts)
    assert kept == [100], f"must fall back to leftmost, not tallest: {kept}"
