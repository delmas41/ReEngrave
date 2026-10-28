"""ONE PRINTED HEAD, NOT TWO POSITIONS -- ROADMAP 2.212 (STAGED GATHER; flag `OMR_TWIN_HEAD_MERGE`, default OFF).

CAUSE (benchmarks/twin-heads-2026-10/FINDINGS.md): the detector often boxes one printed head twice. A head's position is read
off each box's centre, so two boxes give two positions and ADJUDICATE's keeper choice decides the written pitch.

REWORK (Sean 2026-10-27): this module INVENTS NO POSITION. The first version measured a hole/ink centre; Sean rejected the
hole centre for hollow heads (2026-10-01, 2.50: the box centre "is almost always right and better") and heads outside the staff
are placed only by the ink ledger read (`OMR_FARHEAD_LEDGER`). So here: group the twin boxes (`twin_groups`), let each keep the
position its existing reader gave it, and where they DISAGREE write the head GUESSED with both candidates
(`export.twin_head_guess_of`); where they agree nothing changes. Never one of the two picked.

CONVENTION: two boxes whose centres are within half a staff space vertically and half a head width horizontally are one head.
WHAT WOULD FALSIFY IT: a hand-labelled pair of distinct heads a half-space apart on one side of a stem (a unison written as two
heads). NOT CONFIRMED: the cut-offs (0.5 sp, 0.5 hw) are `NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS` and a gap in the pairs' dy
histogram (two plates).

PURE: boxes in, index groups out.
"""
import os
from typing import Dict, List, Sequence, Tuple

ENV = "OMR_TWIN_HEAD_MERGE"


def enabled() -> bool:
    """`OMR_TWIN_HEAD_MERGE` -- ROADMAP 2.212. **Default OFF**; `1/true/yes/on` turns it on."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


#: Two boxes are one head where their centres are strictly closer than this vertically (staff spaces) ...
TWIN_MAX_DY_SPACES = 0.5
#: ... and than this fraction of the mean box width horizontally (`NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS`, restated: the
#: adjudicator imports `gather`, so the reverse import would be a cycle).
TWIN_MAX_DX_HEAD_WIDTHS = 0.5
#: A whole group's centres span less than this vertically (staff spaces): a chain of pairs is not one head.
TWIN_MAX_SPREAD_SPACES = 0.6


def twin_groups(boxes: Sequence[Tuple[float, float, float, float]], spacing: float) -> List[List[int]]:
    """Index groups (size >= 2) of `boxes` ((x, y, w, h), one frame, `spacing` in the same unit) that are one head boxed
    more than once. Connected pairs under the two cut-offs; a group whose centres span `TWIN_MAX_SPREAD_SPACES` or more
    is dropped whole (nothing is merged that is not clearly one head)."""
    n = len(boxes)
    if n < 2 or not spacing or spacing <= 0:
        return []
    cx = [b[0] + b[2] / 2.0 for b in boxes]
    cy = [b[1] + b[3] / 2.0 for b in boxes]
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            head_w = (boxes[i][2] + boxes[j][2]) / 2.0
            if head_w <= 0:
                continue
            if abs(cy[i] - cy[j]) < TWIN_MAX_DY_SPACES * spacing \
                    and abs(cx[i] - cx[j]) < TWIN_MAX_DX_HEAD_WIDTHS * head_w:
                parent[find(i)] = find(j)
    comps: Dict[int, List[int]] = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    out = []
    for members in comps.values():
        if len(members) < 2:
            continue
        ys = [cy[i] for i in members]
        if (max(ys) - min(ys)) >= TWIN_MAX_SPREAD_SPACES * spacing:
            continue
        out.append(sorted(members))
    return sorted(out)
