"""WHERE DOES THIS PLATE ACTUALLY PRINT ITS LEDGER LINES? Off the record.

⚠️ WHY THIS AND NOT THE RESIDUAL. `probe_outward_drift.py` asks the question
through `pos - round(pos)`, which is BOUNDED TO ±0.5 and therefore WRAPS: a
stretch of 0.2 half-steps per ledger line is indistinguishable from a
stretch of 0.2 minus a whole step once the accumulation passes half a step,
which at Litolff's measured pitch happens at the third ledger line. That
probe's P1 is falsified as written and this one is not a rescue of it -- it
measures a DIFFERENT quantity, the printed rung position itself, which has no
modulus in it.

⚠️ IT IS THE SAME QUESTION `ledger_grid.measure_ledger_rungs` ASKS OF THE
RASTER, asked instead of the DETECTOR, which already fires a `ledgerLine`
class the ledger-ladder arbitration reads. Two independent populations for
one convention: 117 hand-labeled notes there, 1,878 detections here.

THE ARITHMETIC. `Q.NOTEHEAD_STAFF_POSITION` keeps `pos_float` and
`Q.CELL_STAFF_SPACE` keeps `half_step`, both per cell, so the cell's grid
origin is recoverable exactly:

    top_y = y_center(head) - pos_float(head) * half_step

and then any other glyph in that cell reads on the same grid. A ledger line
is a LINE, so its true position is an EVEN integer -- 0 and 8 are the staff's
own edges, -2/-4/-6 the rungs above, 10/12/14 below. Reading the m-th rung at
`8 + 2*m*k` instead of `8 + 2*m` measures `k` directly.

⚠️ `y_canonical` IS THE TOP EDGE, NOT THE CENTRE (`template_matcher.py:109`).
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recordstream import stream_array  # noqa: E402

TOP_LINE, BOTTOM_LINE = 0.0, 8.0
MAX_RUNG = 4          # assignment by nearest is safe while 2*m*(k-1) < 1


def cell_of(subject: str) -> str | None:
    """`glyph/p/sy/st/c/i` -> `cell/p/sy/st/c`. ⚠️ NEVER string-surgery the
    tail: the KIND is the FIRST segment, so `rsplit` leaves `glyph/...` and
    matches nothing (paid for on 2026-09-17)."""
    parts = subject.split("/")
    if parts[0] != "glyph" or len(parts) != 6:
        return None
    return "cell/" + "/".join(parts[1:5])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    pos_of: dict[str, float] = {}
    box_of: dict[str, tuple[str, float, float]] = {}   # name, y_top, h
    half_of: dict[str, float] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5:
                box_of[o["subject"]] = (v[0], float(v[2]), float(v[4]))
        elif q == "cell_staff_space":
            hs = (o.get("detail") or {}).get("half_step")
            if hs:
                half_of[o["subject"]] = float(hs)

    print(f"{a.label}: {len(pos_of)} head positions, {len(box_of)} glyph "
          f"boxes, {len(half_of)} cells with a half_step")
    ledgers = [s for s, b in box_of.items() if b[0] == "ledgerLine"]
    print(f"ledgerLine detections: {len(ledgers)}")
    if not ledgers or not half_of:
        print("DEAD: nothing to measure", file=sys.stderr)
        return 2

    # ── the grid origin per cell, from the heads that already read on it ──
    origins: dict[str, float] = {}
    for s, pos in pos_of.items():
        c = cell_of(s)
        hs = half_of.get(c) if c else None
        b = box_of.get(s)
        if c is None or hs is None or b is None:
            continue
        y_center = b[1] + b[2] // 2        # ⚠️ y_canonical is the TOP edge
        origins.setdefault(c, []).append(y_center - pos * hs)
    origins = {c: statistics.median(v) for c, v in origins.items()}
    print(f"cells whose grid origin is recoverable: {len(origins)}")

    # positive control: re-derive the heads' own positions from that origin.
    # If this is not ~exact the arithmetic is wrong and nothing below counts.
    err = []
    for s, pos in pos_of.items():
        c = cell_of(s)
        if c in origins and c in half_of and s in box_of:
            b = box_of[s]
            y_center = b[1] + b[2] // 2
            err.append(abs((y_center - origins[c]) / half_of[c] - pos))
    ctrl = max(err) if err else None
    print(f"POSITIVE CONTROL: heads re-derived on the recovered grid, "
          f"max error {ctrl:.6f} over {len(err)}")
    if ctrl is None or ctrl > 1e-6:
        print("DEAD: the grid origin does not reproduce the heads",
              file=sys.stderr)
        return 2

    # ── where the rungs land ──────────────────────────────────────────────
    by_rung: dict[tuple[str, int], list[float]] = collections.defaultdict(list)
    skipped = 0
    for s in ledgers:
        c = cell_of(s)
        if c is None or c not in origins or c not in half_of:
            skipped += 1
            continue
        name, y_top, h = box_of[s]
        pos = (y_top + h // 2 - origins[c]) / half_of[c]
        if pos < TOP_LINE:
            side, d = "above", (TOP_LINE - pos)
        elif pos > BOTTOM_LINE:
            side, d = "below", (pos - BOTTOM_LINE)
        else:
            by_rung[("INSIDE the staff", 0)].append(pos)
            continue
        m = int(round(d / 2.0))
        if 1 <= m <= MAX_RUNG:
            by_rung[(side, m)].append(d / 2.0)   # measured rung index
    print(f"ledgerLine detections placed: "
          f"{sum(len(v) for k, v in by_rung.items() if k[1])}, "
          f"inside the staff: {len(by_rung.get(('INSIDE the staff', 0), []))}, "
          f"no grid: {skipped}")

    print("\n== WHERE THE RUNGS ARE, in staff spaces from the staff's edge "
          "line (a rung m should sit at exactly m)")
    print(f"{'side':<7} {'m':>2} {'n':>6} {'measured':>9} {'median':>8} "
          f"{'k = measured/m':>15}")
    out: dict = {"label": a.label, "record": a.record,
                 "ledger_detections": len(ledgers),
                 "control_max_error": ctrl, "rungs": {}}
    for side in ("above", "below"):
        for m in range(1, MAX_RUNG + 1):
            v = by_rung.get((side, m))
            if not v:
                continue
            mean, med = statistics.fmean(v), statistics.median(v)
            out["rungs"][f"{side} {m}"] = {
                "n": len(v), "mean_spaces": round(mean, 4),
                "median_spaces": round(med, 4),
                "k_mean": round(mean / m, 4), "k_median": round(med / m, 4)}
            print(f"{side:<7} {m:>2} {len(v):>6} {mean:>9.4f} {med:>8.4f} "
                  f"{mean / m:>15.4f}")

    # ── the GAP between consecutive rungs, which is what k really is ──────
    #  Pooled across sides, because the convention is about spacing and not
    #  about which way is up.
    print("\n== implied pitch of EACH successive gap (× the staff spacing)")
    out["gaps"] = {}
    prev = 0.0
    for m in range(1, MAX_RUNG + 1):
        vals = [x for side in ("above", "below") for x in by_rung.get((side, m), [])]
        if not vals:
            continue
        med = statistics.median(vals)
        gap = med - prev
        out["gaps"][f"gap {m}"] = {"n": len(vals), "pitch": round(gap, 4)}
        print(f"  edge -> rung {m}" if m == 1 else f"  rung {m-1} -> rung {m}",
              f"   n={len(vals):>5}   pitch = {gap:.4f}")
        prev = med

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
