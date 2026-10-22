"""THE CONVERSE OF THE CONVENTION -- and it needs NO RASTER.

`docs/engraving-conventions.md` `[C9 + L10]` states the attachment convention
and then states a second prediction that this thread has never used:

    "Conversely, given a stem direction, the notehead is on a known side of
     the stem -- which is how to associate a stem with its head rather than a
     neighbour's."

⚠️⚠️ THAT IS A DIFFERENT CLAIM FROM THE ONE THE HANDOFF PROPOSES, AND IT LIVES
IN A DIFFERENT STAGE. The forward reading -- *is there a vertical run of ink in
one of the two legal cells* -- is a measurement of PIXELS, so it belongs to
GATHER and cannot reach an adjudicator at all (`Evidence` exposes rows and
nothing else; no adjudicator in this tree imports an image library). The
converse is a statement about two boxes that are ALREADY ON THE RECORD:
`Q.STEM` carries `(x, y, w, h)` and `Q.GLYPH_BOX` carries `(name, x, y, w, h)`,
both canonical. So the converse is testable, and shippable, with no gather
change, no re-gather and no weights.

Bravura fixes the geometry the registry quotes: `stemUpSE = [1.18, 0.168]` is
the head's RIGHT edge and `stemDownNW = [0.0, -0.168]` its LEFT. So a stem
standing to the right of its head's centre should point UP, and one to the left
should point DOWN.

TWO NUMBERS, REACH FIRST:

1. **The control** -- on heads a stem already decided, does the side agree with
   the direction? ⚠️ It is NOT an independent check: `_project` reads the
   stem's box against the head group's boxes and the side reads the same two
   boxes on the other axis. A stem associated with the WRONG head would
   usually be wrong on both, which is exactly the failure this is for --
   so read this as *how often the association is self-consistent*, never as
   accuracy against the print.
2. **The reach** -- on `stems_disagree` heads, where two stems meet one head
   and point opposite ways, how often does exactly ONE of them stand on the
   legal side? That head is currently an honest abstention (111 on Litolff, 17
   on Breitkopf) and the convention would decide it.

    python3 converse_reach.py --record R --label L --out out/L-converse.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                            # noqa: E402
# ⚠️ IMPORTED, never restated: the association test, the box readers and the
# projection are the SHIPPED ones, so this probe cannot drift from the tier it
# is measuring for.
from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402
    _project, _stems_on, _xywh, _xywh_head)


class Row:
    """The two fields `_project` / `_stems_on` read off a record row."""
    __slots__ = ("value", "id")

    def __init__(self, value, rid):
        self.value, self.id = value, rid


def cell_of(subject: str) -> str:
    """⚠️ `Subject` carries its KIND in the FIRST segment, so a `rsplit` is
    wrong -- `glyph/1/0/2/4/1` must become `cell/1/0/2/4`, not
    `glyph/1/0/2/4`. Spelled here once; the three-defect note in the
    2026-09-17 handoff is exactly this mistake.
    """
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5]) if len(p) >= 5 else subject


def side_of(stem_box, head_box) -> str:
    """Which side of the head this stem stands on. Bravura: x = 0 or x = w."""
    sx = stem_box[0] + stem_box[2] / 2.0
    hx = head_box[0] + head_box[2] / 2.0
    return "R" if sx > hx else "L"


#: The two cells that are music. Right-and-down and left-and-up do not exist.
LEGAL = {("R", "up"), ("L", "down")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    heads_by_cell: dict[str, list] = collections.defaultdict(list)
    stems_by_cell: dict[str, list] = collections.defaultdict(list)
    head_row: dict[str, Row] = {}
    klass: dict[str, str] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "glyph_box" and _xywh_head(o.get("value")) is not None:
            v = o["value"]
            name = str(v[0]) if isinstance(v, (list, tuple)) else ""
            if "notehead" in name.lower():
                r = Row(v, o["id"])
                head_row[o["subject"]] = r
                heads_by_cell[cell_of(o["subject"])].append(r)
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "stem":
            r = Row(o.get("value"), o["id"])
            if _xywh(r) is not None:
                stems_by_cell[cell_of(o["subject"])].append(r)
    if not head_row or not stems_by_cell:
        print("DEAD: no notehead boxes or no stem rows -- the record or the "
              "subject-key join is wrong.", file=sys.stderr)
        return 2

    verdict, value = {}, {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
            if v.get("outcome") == "decided":
                value[v["subject"]] = str(v.get("value"))

    ctrl = collections.Counter()
    reach = collections.Counter()
    resolved = []
    for s, reason in verdict.items():
        if "Whole" in klass.get(s, ""):
            continue
        hr = head_row.get(s)
        if hr is None:
            continue
        hb = _xywh_head(hr.value)
        cell = cell_of(s)
        heads = heads_by_cell[cell]
        mine = _stems_on(hb, stems_by_cell[cell])
        if not mine:
            continue
        cells = [(side_of(_xywh(st), hb), _project(st, heads, hb))
                 for st in mine]
        legal = [c for c in cells if c in LEGAL]

        if reason == "DECIDED":
            # self-consistency of the association we already trust
            for side, d in cells:
                ctrl["agrees" if (side, d) in LEGAL else "disagrees"] += 1
            ctrl["heads"] += 1
        elif reason == "stems_disagree":
            reach["heads"] += 1
            reach[f"stems={len(mine)}"] += 1
            if len(legal) == 1:
                reach["exactly ONE legal (the convention decides)"] += 1
                resolved.append({"subject": s, "cells": cells,
                                 "decides": legal[0][1]})
            elif not legal:
                reach["NO legal cell (both stems illegal)"] += 1
            else:
                dirs = {d for _, d in legal}
                reach["several legal, agreeing" if len(dirs) == 1
                      else "several legal, DISAGREEING"] += 1

    print(f"{a.label}\n")
    tot = ctrl["agrees"] + ctrl["disagrees"]
    print(f"== 1. CONTROL: on {ctrl['heads']} heads a stem already decided, "
          f"is each associated stem on the LEGAL side?")
    print(f"   stem/head pairs      {tot:>6}")
    for k in ("agrees", "disagrees"):
        print(f"   {k:<20} {ctrl[k]:>6}"
              + (f"   {ctrl[k]/tot:.1%}" if tot else ""))
    if not tot:
        print("\nDEAD: no stem/head pair to check", file=sys.stderr)
        return 2
    print(f"   ⚠️ self-consistency of the association, NOT accuracy -- the "
          f"side and the direction read the same two boxes.")

    print(f"\n== 2. REACH on `stems_disagree` (an honest abstention today)")
    for k, n in reach.most_common():
        print(f"   {k:<44} {n:>6}")

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"label": a.label, "control": dict(ctrl),
             "control_agreement": round(ctrl["agrees"] / tot, 4),
             "reach": dict(reach), "resolved": resolved}, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
