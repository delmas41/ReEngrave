#!/usr/bin/env python3
"""l283_flag_geometry: WHERE a printed eighth-note flag's ink sits, measured against its own stem's tip, on
Sean's hand-truth page (Brahms 317803 pdf 0) -- ROADMAP 2.83, measurement (a).

For every `flag*` box of his (34), the stem box it hangs from (his; the flag's left edge within
`STEM_X_SPACES` of the stem's x-span, and the flag's tip-side edge within `STEM_Y_SPACES` of a stem end), then
in LOCAL staff spaces (the cell's own five lines at the flag's x, `score.staff_bands`) and measured ALONG THE
STEM FROM ITS TIP INTO THE BODY (t = 0 at the tip, t > 0 toward the head, t < 0 past the tip):

  * the BOX (his): t_start, t_end, x0 and x1 from the stem's right edge (+ = right of it);
  * the INK: on the 600 dpi page raster (`render_page`, the gather's own), inside his box, outside the stem's
    own columns and outside the rows a staff line stands on (his staff-line checks): the first and last t
    that hold ink in the band to the right of the stem, the farthest x of that ink, and which side the ink is on.
    A flag is drawn on ONE side of its stem; the LEFT band is measured too, as the control that can fail.
  * the row profile: for each 0.1-space t-step from -1.0 to +4.0, the fraction of the 0.9-space-wide band to the
    stem's right that is ink, averaged over all flags. This is the number the old window (t in 1.0..2.5, density
    >= 0.30) is judged against.

    python3 l283_flag_geometry.py [--cache p0_rgb.npy] [--json out.json]

Reads the truth, never writes it. Nothing here is a reader and nothing is adopted: it measures where the ink is.
"""
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from l281_truth import Truth  # noqa: E402
from l281_view import PDF, page_rgb  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402

STEM_X_SPACES = 0.6
STEM_Y_SPACES = 1.6
BAND_WIDTH_SPACES = 0.9      # the old window's width, kept so the profile is comparable
LINE_HALF = 0.14
T_STEP = 0.1


def cx(r):
    return (r[0] + r[2]) / 2.0


def local_space(T, bands, x, y):
    loc = S.locate(bands, x, y, reach=3.0)
    if loc:
        b = min(loc, key=lambda p: p[1])[0]
        return b.space, b
    return T.space, None


def line_rows(bands, x, lo, hi):
    """Page rows in [lo, hi) that a staff line of a band holding x stands on."""
    rows = set()
    for b in bands:
        if b.rect[0] <= x <= b.rect[2]:
            sp = b.space
            for ly in b.lines:
                for yy in range(int(round(ly - LINE_HALF * sp)), int(round(ly + LINE_HALF * sp)) + 1):
                    if lo <= yy < hi:
                        rows.add(yy)
    return rows


def find_stem(T, f):
    sp = T.space
    best = None
    for s in T.stems:
        r = s.rect
        if not (r[0] - STEM_X_SPACES * sp <= f.rect[0] <= r[2] + STEM_X_SPACES * sp):
            continue
        # a stem end near the flag's tip-side edge
        d_bot = abs(f.rect[3] - r[3])
        d_top = abs(f.rect[1] - r[1])
        # the class names the end: a `Down` flag hangs from a DOWN stem's bottom tip, an `Up` flag from an UP stem's top tip
        # (checked by eye on the page, FINDINGS 2.83); a short stem has both ends within reach of the box, so the class decides
        want = "bottom" if f.cls.endswith("Down") else "top" if f.cls.endswith("Up") else None
        for end, d in (("bottom", d_bot), ("top", d_top)):
            if want is not None and end != want:
                continue
            if d <= STEM_Y_SPACES * sp:
                k = (abs(f.rect[0] - r[2]) + d)
                if best is None or k < best[0]:
                    best = (k, s, end)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Truth()
    bands = S.staff_bands(T.page)
    img = page_rgb(PDF, a.cache)
    gray = img.mean(axis=2)
    H, W = gray.shape
    ink = gray < 128
    rows = []
    prof_r = collections.defaultdict(list)
    prof_l = collections.defaultdict(list)
    for f in sorted(T.flags, key=lambda i: (i.rect[1], i.rect[0])):
        found = find_stem(T, f)
        if not found:
            rows.append({"flag": f.id, "cls": f.cls, "status": "no_stem_box", "rect": [round(v, 1) for v in f.rect]})
            continue
        _k, stem, end = found
        sx0, sy0, sx1, sy1 = stem.rect
        fx0, fy0, fx1, fy1 = f.rect
        sp, band = local_space(T, bands, (sx0 + sx1) / 2.0, (sy0 + sy1) / 2.0)
        sign = 1.0 if end == "top" else -1.0     # +1: walk DOWN the page from the tip into the body
        tip_y = sy0 if end == "top" else sy1
        # t along the stem, in spaces: t = (y - tip_y) * sign / sp
        t_box = sorted(((y - tip_y) * sign / sp) for y in (fy0, fy1))
        row = {"flag": f.id, "cls": f.cls, "end": end, "space": round(sp, 2),
               "stem": stem.id, "stem_w": round((sx1 - sx0) / sp, 2),
               "box_t": [round(t_box[0], 2), round(t_box[1], 2)],
               "box_x0": round((fx0 - sx1) / sp, 2), "box_x1": round((fx1 - sx1) / sp, 2),
               "status": "ok"}
        # ink, right and left of the stem, inside t in [-1.0, +4.0]
        t_lo, t_hi = -1.0, 4.0
        ya, yb = sorted((tip_y + sign * t_lo * sp, tip_y + sign * t_hi * sp))
        ya, yb = max(0, int(round(ya))), min(H, int(round(yb)))
        lr = line_rows(bands, (sx0 + sx1) / 2.0, ya, yb)
        wpx = int(round(BAND_WIDTH_SPACES * sp))
        xr0, xr1 = int(round(sx1)), int(round(sx1)) + wpx
        xl1, xl0 = int(round(sx0)), int(round(sx0)) - wpx
        side_ink = {}
        for name, (xa, xb) in (("right", (xr0, xr1)), ("left", (xl0, xl1))):
            ts, prof = [], {}
            far_x = None
            for yy in range(ya, yb):
                if yy in lr:
                    continue
                t = (yy - tip_y) * sign / sp
                seg = ink[yy, max(0, xa):min(W, xb)]
                if seg.size == 0:
                    continue
                k = int(np.floor((t - t_lo) / T_STEP + 1e-9))
                prof.setdefault(k, []).append(float(seg.mean()))
                if seg.any():
                    ts.append(t)
            for k, v in prof.items():
                (prof_r if name == "right" else prof_l)[k].append(statistics.mean(v))
            # ink extents: t range and the farthest x out from the stem, on the band to that side
            if ts:
                row[name + "_ink_t"] = [round(min(ts), 2), round(max(ts), 2)]
            else:
                row[name + "_ink_t"] = None
            # farthest x (right) / leftmost (left) of ink within his flag box (or the band) -- right only
            if name == "right":
                bx0, bx1 = int(round(max(fx0, sx1))), int(round(min(W, fx1 + 2)))
                by0, by1 = int(round(fy0)), int(round(fy1))
                sub = ink[by0:by1, bx0:bx1]
                if sub.any():
                    cols = np.where(sub.any(axis=0))[0]
                    row["ink_x_out"] = round((bx0 + cols.max() - sx1) / sp, 2)
        # right-band density where his box is: inside t window and his box rows
        rows.append(row)

    ok = [r for r in rows if r["status"] == "ok"]
    print(f"flags: {len(rows)}  with a stem box: {len(ok)}  space median {T.space:.1f}px")
    print(f"{'flag':>6} {'cls':>12} {'end':>6} {'sp':>5}  box_t          box_x0..x1   ink_right_t       ink_left_t       ink_x_out")
    for r in ok:
        print(f"{r['flag']:>6} {r['cls']:>12} {r['end']:>6} {r['space']:5.1f}  {str(r['box_t']):14s} "
              f"{r['box_x0']:5.2f}..{r['box_x1']:5.2f}  {str(r['right_ink_t']):16s}  {str(r['left_ink_t']):16s}  {r.get('ink_x_out')}")
    for r in rows:
        if r["status"] != "ok":
            print("  NO STEM BOX:", r)

    def q(vals, p):
        vals = sorted(vals)
        return vals[min(len(vals) - 1, int(round(p * (len(vals) - 1))))]

    for name, key in (("box t_start", lambda r: r["box_t"][0]), ("box t_end", lambda r: r["box_t"][1]),
                      ("box x0 (from stem right edge)", lambda r: r["box_x0"]),
                      ("box x1 (from stem right edge)", lambda r: r["box_x1"]),
                      ("ink x_out (right)", lambda r: r.get("ink_x_out"))):
        v = [key(r) for r in ok if key(r) is not None]
        print(f"{name:32s} n={len(v)} min {min(v):.2f} p10 {q(v,.1):.2f} median {statistics.median(v):.2f} p90 {q(v,.9):.2f} max {max(v):.2f}")
    rt = [r["right_ink_t"] for r in ok if r.get("right_ink_t")]
    print(f"right-band ink t_first: min {min(x[0] for x in rt):.2f} median {statistics.median(x[0] for x in rt):.2f} "
          f"max {max(x[0] for x in rt):.2f};  t_last: min {min(x[1] for x in rt):.2f} median {statistics.median(x[1] for x in rt):.2f} max {max(x[1] for x in rt):.2f}")
    print("\nrow profile: mean ink fraction of the 0.9-space band to the stem's RIGHT / LEFT, per 0.1-space step of t")
    for k in sorted(prof_r):
        t = -1.0 + k * T_STEP
        if t > 4.0:
            break
        rr = prof_r[k]
        ll = prof_l.get(k, [])
        print(f"  t {t:+.1f}..{t + T_STEP:+.1f}  right {statistics.mean(rr):.3f} (n={len(rr)})  left {statistics.mean(ll) if ll else float('nan'):.3f}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
