#!/usr/bin/env python3
"""lane-ledger-accidental (2026-10-04) -- MEASURE ONLY.

Which far heads have a detector accidental box to their LEFT, and what did
the cause-C accidental exclusion do to the rung read of each?  Nothing in
`tools/` is edited: `edge_census`'s run-time wrappers record the walk's
candidates (`clears`), the collapse before/after, and the final ladder.

    python3 benchmarks/omr-local-staff-2026-09/accidental_census.py [--json f]

Control (printed first): the fix1_far arm reproduces Litolff 32/10/2 and
Brahms 11/0/0 with recording OFF and ON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

ARM = dict(near_edge_ledgers=True, restore_masked_near_edge=True,
           far_side_ledger=True)
LEFT_SPACES = 2.0      # accidental right edge within this of the head's left edge
VERT_SPACES = 1.5      # accidental vertically within this of the head box


def _derive(rungs_y, *a, **kw):
    real = ec._ORIG_DERIVE(rungs_y, *a, **kw)
    tr = ec.ST["trace"]
    if ec.ST["record"] and tr is not None:
        tr["final_ladder"] = [float(v) for v in rungs_y]
        tr["derive_real"] = real
    return real


def read(h, record=False, acc=True, **kw):
    ec.ST.update(record=record, undo=None, main=False, box=None)
    ec.ST["trace"] = dict(clears=[], collapse=[]) if record else None
    pos, reason = ec.score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"] if acc else [],
        four_causes_cd=True, **{**ARM, **kw})
    tr = ec.ST["trace"]
    ec.ST.update(record=False, trace=None)
    return pos, reason, tr


def left_accidentals(h):
    x0, y0, x1, y1 = h["box"]
    ys = sorted(h["lines"])
    sp = (ys[-1] - ys[0]) / 4.0
    out = []
    for sub, (ax0, ay0, ax1, ay1) in h["acc"]:
        gap = (x0 - ax1) / sp
        if not (-0.5 <= gap <= LEFT_SPACES):
            continue
        if ay1 < y0 - VERT_SPACES * sp or ay0 > y1 + VERT_SPACES * sp:
            continue
        out.append(dict(sub=sub, box=(ax0, ay0, ax1, ay1), gap_sp=round(gap, 2)))
    return out


def main():
    ec.install()
    lg.derive_far_head_step = _derive
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    print("== control (fix1_far arm; recording off / on)")
    for d, hs in heads.items():
        a = [ec.verdict(read(h)[0], h["truth"]) for h in hs]
        b = [ec.verdict(read(h, record=True)[0], h["truth"]) for h in hs]
        print(d, ec.tally(a), ec.tally(b))
    rows = []
    for d, hs in heads.items():
        for h in hs:
            la = left_accidentals(h)
            pos, reason, tr = read(h, record=True)
            pos_na, reason_na, _ = read(h, acc=False)
            rows.append(dict(doc=d, subject=h["subject"], truth=h["truth"],
                             pos=pos, v=ec.verdict(pos, h["truth"]),
                             reason=reason, acc_left=la,
                             pos_without_acc_boxes=pos_na,
                             v_without_acc_boxes=ec.verdict(pos_na, h["truth"]),
                             ladder=tr.get("final_ladder"),
                             clears=tr["clears"], collapse=tr["collapse"]))
    print("\n== census: far heads with a detector accidental box to the left "
          f"(<= {LEFT_SPACES} sp, within {VERT_SPACES} sp vertically)")
    for d in ts.DOCS:
        rs = [r for r in rows if r["doc"] == d]
        w = [r for r in rs if r["acc_left"]]
        print(f"{d}: {len(w)} of {len(rs)} heads; right/wrong/abstain =",
              ec.tally([r["v"] for r in w]),
              "| without accidental boxes in the exclusion set:",
              ec.tally([r["v_without_acc_boxes"] for r in w]))
    print("\nheads with an accidental to the left:")
    for r in rows:
        if r["acc_left"]:
            print(f"{r['doc'][:8]} {r['subject']:20} {r['v']:7} pos={r['pos']} "
                  f"truth={r['truth']} noacc={r['pos_without_acc_boxes']}"
                  f"({r['v_without_acc_boxes']}) gaps="
                  f"{[a['gap_sp'] for a in r['acc_left']]}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
