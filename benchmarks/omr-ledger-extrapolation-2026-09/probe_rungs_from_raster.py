"""THE PITCH OF THE PRINTED LEDGER LINES, MEASURED OFF THE RASTER.

⚠️ NO DETECTOR IN THE LOOP. Every other measurement on this thread reads the
model's `ledgerLine` boxes; this one renders the page and finds the rungs as
rows of ink, exactly as `staff_detector` finds staff lines. If the two agree,
the convention is established independently of anything the model does -- and
if they disagree, the detector-based figures are the ones to drop.

THE RULER IS THE STAFF ITSELF. A staff's five printed lines are located by
the same row-of-ink rule in the same strip, so the spacing the rungs are
compared against is measured from the same pixels in the same place. Nothing
is carried in from the record except WHERE to look: the head's x-range and
which staff it belongs to.

⚠️ SCALE VERIFIED: the record's `staff_lines` for `staff/1/0/0` are
1148/1163/1179/1195/1210 and a 600-dpi render of pdf page 1 has its dark rows
centred at 1147.5/1163/1179/1194/1210.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import fitz
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recordstream import stream_array  # noqa: E402

DPI = 600
INK = 128            # a pixel darker than this is ink
SPAN = 0.80          # a rung must cross this fraction of the head's width
MAX_OUT = 6          # staff spaces to search beyond the edge line


def rows_of_ink(strip: np.ndarray, need: float) -> list[float]:
    """Centres of the runs of consecutive rows whose ink crosses the strip."""
    dark = (strip < INK).mean(axis=1) >= need
    out, run = [], []
    for i, d in enumerate(dark):
        if d:
            run.append(i)
        elif run:
            out.append(statistics.fmean(run))
            run = []
    if run:
        out.append(statistics.fmean(run))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    lines_of: dict[str, list[float]] = {}
    pos_of: dict[str, float] = {}
    pbox: dict[str, list] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                pbox[o["subject"]] = [float(x) for x in bp]

    heads = [(s, p) for s, p in pos_of.items()
             if (p < 0 or p > 8) and s in pbox]
    print(f"{a.label}: {len(heads)} heads outside the staff with a page box")
    if not heads:
        print("DEAD: nothing outside the staff", file=sys.stderr)
        return 2

    doc = fitz.open(a.pdf)
    pages: dict[int, np.ndarray] = {}
    gaps: dict[int, list[float]] = collections.defaultdict(list)
    checked = skipped = 0
    staff_err: list[float] = []
    for s, p in heads:
        pr = s.split("/")
        pg, sy, st = int(pr[1]), int(pr[2]), int(pr[3])
        L = lines_of.get(f"staff/{pg}/{sy}/{st}")
        if not L or len(L) < 5:
            skipped += 1
            continue
        if pg not in pages:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pages[pg]
        half = statistics.fmean([L[i + 1] - L[i] for i in range(4)]) / 2.0
        above = p < 0
        edge = L[0] if above else L[4]
        x0, _, x1, _ = pbox[s]
        xa, xb = int(max(0, x0)), int(min(img.shape[1], x1))
        if xb - xa < 4:
            skipped += 1
            continue
        # ── the CONTROL, in this very strip: can the rule find the staff's
        #    own five lines here? If not, the strip is unreadable and the
        #    rungs it reports are not evidence.
        ya, yb = int(L[0] - half), int(L[4] + half)
        found = rows_of_ink(img[ya:yb, xa:xb], SPAN)
        hit = []
        for ln in L:
            near = [f + ya for f in found if abs(f + ya - ln) <= half * 0.8]
            if near:
                hit.append(min(near, key=lambda y: abs(y - ln)) - ln)
        if len(hit) < 4:
            skipped += 1
            continue
        staff_err += hit
        # ── now the rungs, outward from the edge line
        if above:
            ya, yb = int(edge - MAX_OUT * 2 * half), int(edge - half * 0.5)
        else:
            ya, yb = int(edge + half * 0.5), int(edge + MAX_OUT * 2 * half)
        if ya < 0 or yb > img.shape[0] or yb <= ya:
            skipped += 1
            continue
        found = [y + ya for y in rows_of_ink(img[ya:yb, xa:xb], SPAN)]
        d = sorted(((edge - y) if above else (y - edge)) / (2 * half)
                   for y in found)
        d = [x for x in d if x > 0.4]
        # dedupe and walk the ladder, one rung per space
        lad, prev = [], 0.0
        for x in d:
            if lad and x - lad[-1] < 0.5:
                continue
            if not (0.65 <= x - prev <= 1.35):
                break
            lad.append(x)
            prev = x
        for i, x in enumerate(lad, start=1):
            gaps[i].append(x - (lad[i - 2] if i > 1 else 0.0))
        checked += 1

    print(f"strips read: {checked}, skipped (staff lines not recoverable "
          f"there): {skipped}")
    if not gaps:
        print("DEAD: no rung found in any strip", file=sys.stderr)
        return 2
    print(f"CONTROL: the staff's OWN five lines, found in these same strips, "
          f"sit {statistics.fmean(staff_err):+.3f} px from where the record "
          f"says (sd {statistics.stdev(staff_err):.3f}, n={len(staff_err)})")

    print("\n== PRINTED ledger-rung pitch, off the raster "
          "(x the staff spacing; the grid assumes 1.000)")
    print(f"{'gap':<22} {'n':>6} {'median':>8} {'mean':>8}")
    out = {"label": a.label, "strips": checked, "gaps": {}}
    cum = 0.0
    for i in sorted(gaps):
        v = gaps[i]
        if len(v) < 5:
            continue
        med = statistics.median(v)
        cum += med
        out["gaps"][f"gap {i}"] = {"n": len(v), "median": round(med, 4),
                                   "mean": round(statistics.fmean(v), 4),
                                   "cumulative": round(cum, 4)}
        name = "edge -> rung 1" if i == 1 else f"rung {i-1} -> rung {i}"
        print(f"{name:<22} {len(v):>6} {med:>8.4f} {statistics.fmean(v):>8.4f}")
    print("\n== the grid's ERROR at each rung, in half-steps "
          "(0.5 flips the note to the wrong staff position)")
    cum = 0.0
    out["error_at_rung"] = {}
    for i in sorted(gaps):
        if f"gap {i}" not in out["gaps"]:
            continue
        cum += out["gaps"][f"gap {i}"]["median"]
        err = 2 * (cum - i)
        out["error_at_rung"][f"rung {i}"] = round(err, 4)
        print(f"  rung {i}: printed at {cum:.3f} spaces, grid says {i}.000 "
              f"-> error {err:+.3f} half-steps"
              f"{'   <-- FLIPS' if abs(err) >= 0.5 else ''}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
