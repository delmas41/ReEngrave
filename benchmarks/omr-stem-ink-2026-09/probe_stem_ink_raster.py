"""IS THE STEM INK ON THE PAGE? Asked of the RASTER, not of another reading.

`docs/handoff-2026-09-17-two-brakes-and-a-ruler.md` §4 measured, for each of
the 793 heads whose stem direction abstains `no_stem`, the distance to the
nearest **stem row in the record** -- and concluded "not read". That is a
reading compared with a reading: a head with no stem row near it and a head
whose stem the CV rung never found are the same number there.

This renders the page and looks. A stem is a VERTICAL RUN OF INK AT THE SIDE
OF THE HEAD, so for each head it takes two narrow columns, one just left and
one just right, and measures the longest unbroken run of dark pixels in each.

⚠️ THE POSITIVE CONTROL IS THE WHOLE INSTRUMENT. The same test is run on the
heads that DID get a stem direction. If it cannot find ink beside those, it
is broken and its zeros mean nothing -- which is the failure this thread has
paid for three times.

⚠️ IT IS ONE-SIDED. Finding ink says a stem is probably there and the reader
missed it. Finding none does NOT prove the page is blank there: a head buried
in a chord, a beam or a neighbouring staff's ink can hide its own stem.
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
sys.path.insert(0, str(HERE.parents[1] / "benchmarks"
                      / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI = 600
INK = 128
# ⚠️ THESE THREE WERE WRONG ON THE FIRST RUN AND THE POSITIVE CONTROL SAID SO
# (it found ink beside only 30.9% of heads that DID get a stem). A stem is a
# HAIRLINE -- about an eighth of a staff space -- and it TOUCHES the head, so
# a 0.30-space column placed just outside a generous detector box is mostly
# white and mostly in the wrong place. The probe now sweeps the offset.
COL_W = 0.12        # the probe column's width, in staff spaces (a hairline)
REACH = 3.5         # how far up/down a stem is looked for, in staff spaces
MIN_STEM = 1.75     # a run this long (staff spaces) counts as a stem
SWEEP = 0.85        # how far either side of the head's edge to sweep, spaces


def longest_run(col: np.ndarray) -> int:
    best = run = 0
    for v in col:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    lines_of: dict[str, list[float]] = {}
    pbox: dict[str, list] = {}
    klass: dict[str, str] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                pbox[o["subject"]] = [float(x) for x in bp]

    verdict: dict[str, str] = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = (v.get("reason") if v.get("outcome")
                                     != "decided" else "DECIDED")

    doc = fitz.open(a.pdf)
    pages: dict[int, np.ndarray] = {}
    res: dict[str, list[float]] = collections.defaultdict(list)
    skipped = 0
    for s, reason in verdict.items():
        if s not in pbox:
            skipped += 1
            continue
        p = s.split("/")
        pg, sy, st = int(p[1]), int(p[2]), int(p[3])
        L = lines_of.get(f"staff/{pg}/{sy}/{st}")
        if not L or len(L) < 5:
            skipped += 1
            continue
        if pg not in pages:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pages[pg]
        space = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        x0, y0, x1, y1 = pbox[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * space))
        ya = max(0, int(cy - REACH * space))
        yb = min(img.shape[0], int(cy + REACH * space))
        best = 0.0
        if yb - ya >= 4:
            # sweep the column across the head's two edges: a stem touches the
            # head, and where exactly depends on the box's own generosity.
            step = max(1, w // 2)
            for edge in (x0, x1):
                lo = int(edge - SWEEP * space)
                hi = int(edge + SWEEP * space)
                for cx in range(lo, hi + 1, step):
                    xa, xb = max(0, cx), min(img.shape[1], cx + w)
                    if xb - xa < 1:
                        continue
                    col = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                    best = max(best, longest_run(col) / space)
        res[reason].append(best)

    print(f"{a.label}: {sum(len(v) for v in res.values())} heads probed, "
          f"{skipped} skipped (no page box or no staff lines)")
    print(f"\n== longest vertical ink run beside the head, in staff spaces")
    print(f"{'stem_direction says':<22} {'n':>6} {'median':>8} "
          f"{'>= %.2f sp':>10} {'share':>8}" % MIN_STEM)
    out = {"label": a.label, "min_stem_spaces": MIN_STEM, "groups": {}}
    for reason in sorted(res, key=lambda r: -len(res[r])):
        v = res[reason]
        hit = sum(1 for x in v if x >= MIN_STEM)
        out["groups"][reason] = {"n": len(v),
                                 "median": round(statistics.median(v), 3),
                                 "with_stem_ink": hit,
                                 "share": round(hit / len(v), 4)}
        print(f"{reason:<22} {len(v):>6} {statistics.median(v):>8.2f} "
              f"{hit:>10} {hit / len(v):>8.1%}")

    dec = out["groups"].get("DECIDED", {}).get("share")
    if dec is None or dec < 0.5:
        print("\nDEAD: the positive control failed -- the probe cannot find "
              "ink beside heads that DID get a stem, so its zeros mean "
              "nothing.", file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2
    print(f"\nPOSITIVE CONTROL: heads that DID get a stem show ink "
          f"{dec:.1%} of the time.")

    # ── and split the no_stem heads by what the detector called them ──────
    print("\n== `no_stem` heads by notehead class "
          "(a WHOLE note correctly has none)")
    by_cls: dict[str, list[float]] = collections.defaultdict(list)
    for s, reason in verdict.items():
        if reason != "no_stem" or s not in pbox:
            continue
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L:
            continue
    # recompute cheaply from the stored pass instead of re-rendering
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
