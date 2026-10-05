#!/usr/bin/env python3
"""lane-ledger-template-centre diagnostic: for the 9 census heads, scan
`head_center_y` over box-middle +-0.8 sp and show the verdict at each offset,
with the probe band as shipped (+-0.15 sp) and widened (+-0.30 sp,
monkeypatched here, never in tools/). Reports whether ANY centre rescues a
head, and whether a looser band does. Measurement only. Fix 1 on throughout."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import template_centre as tc  # noqa: E402
import score_template_centre as stc  # noqa: E402
import edge_census as ec  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OFFS = [round(-0.8 + 0.1 * i, 1) for i in range(17)]
DOC = "beethoven5-litolff"


def verdict_at(h, off_sp, tol):
    old = lg.MIDDLE_ROW_TOL_SPACES
    lg.MIDDLE_ROW_TOL_SPACES = tol
    try:
        x0, y0, x1, y1 = h["box"]
        sp = (max(h["lines"]) - min(h["lines"])) / 4.0
        cy = (y0 + y1) / 2.0 + off_sp * sp
        return score.reader_absolute_position(
            h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
            page_accidental_boxes=h["acc"], four_causes_cd=True, head_center_y=cy,
            **stc.FIX1)
    finally:
        lg.MIDDLE_ROW_TOL_SPACES = old


def main():
    heads = ec.load_heads(DOC)
    ctx = tc.doc_context(DOC)
    fits = {h["subject"]: tc.fit_head(ctx, h) for h in heads}
    for tol in (0.15, 0.30):
        print(f"\n===== probe band +-{tol} sp; columns = centre offset from box middle in sp "
              f"(R right, W wrong, . abstain)")
        print("subject             ref    F0 tmplDy  " + " ".join(f"{o:+.1f}" for o in OFFS))
        for h in heads:
            if h["subject"] not in tc.CENSUS_9:
                continue
            row = []
            for o in OFFS:
                pos, _ = verdict_at(h, o, tol)
                row.append("  . " if pos is None else ("  R " if pos in h["truth"] else "  W "))
            p0, _ = verdict_at(h, 0.0, tol)
            print(f"{h['subject']:19} {h['truth']!s:6} {p0!s:>4} {fits[h['subject']]['dy_sp']:+.2f}  " + "".join(row))


if __name__ == "__main__":
    main()
